#!/usr/bin/env python3
"""Conservative geometric remap of low-temperature elastic solid fields.

Intersections transfer cell-integrated mass, thermal enthalpy and rod identity.
No nearest-node extrapolation, global temperature rescaling, or invented missing
history. This is a remap qualification, not an implemented solid-to-flow handoff.
"""
import argparse
from itertools import combinations
import json
import math
from pathlib import Path
import numpy as np
from scipy.io import netcdf_file
from scipy.spatial import ConvexHull,cKDTree
from check_contact_thermal_balance import reference_enthalpy_density
from analyze_afsd_surface_flux import tetra_determinants


def decode(rows):return [b''.join(row).decode().strip('\x00 ') for row in rows]


def read_exodus_mesh(path):
    with netcdf_file(path,mmap=False) as f:
        v=f.variables;names=decode(v['name_nod_var'].data)
        times=np.array(v['time_whole'].data)
        if not len(times) or not np.isfinite(times).all():raise ValueError('valid time history required')
        fields={name:np.array(v[f'vals_nod_var{i+1}'].data[-1]) for i,name in enumerate(names)}
        if any(name not in fields for name in ('T','Ux','Uy','Uz')):
            raise ValueError('temperature and displacement fields required; missing fields are not zero-filled')
        ref=np.column_stack([v['coord'+a].data for a in 'xyz'])
        current=ref+np.column_stack([fields[a] for a in ('Ux','Uy','Uz')])
        ids=np.array(v['eb_prop1'].data);block_names=decode(v['eb_names'].data)
        cells=[];labels=[];element_fields={}
        element_names=decode(v['name_elem_var'].data) if 'name_elem_var' in v else []
        for i,bid in enumerate(ids,1):
            var=v[f'connect{i}'];kind=var.elem_type.decode().upper()
            if kind.startswith('TRI'):continue
            if not kind.startswith('TET') or var.shape[1]!=4:raise ValueError('TET4 bulk required')
            conn=np.array(var.data,dtype=int)-1;cells.append(conn);labels.extend([block_names[i-1]]*len(conn))
            for j,name in enumerate(element_names,1):
                key=f'vals_elem_var{j}eb{i}'
                if key in v:element_fields.setdefault(name,[]).append(np.array(v[key].data[-1]))
        conn=np.vstack(cells)
        return dict(ref_coords=ref,curr_coords=current,connectivity=conn,
                    element_block_names=np.array(labels),fields=fields,times=times,
                    element_fields={k:np.concatenate(a) for k,a in element_fields.items()})


def tetra_volumes(coords,connectivity):return abs(tetra_determinants(coords,connectivity))/6


def barycentric(tet,points):
    local=(np.asarray(points)-tet[0])@np.linalg.inv((tet[1:]-tet[0]).T).T
    return np.column_stack([1-local.sum(axis=1),local])


def intersection_volume(a,b):
    ba=barycentric(b,a);ab=barycentric(a,b);eps=1e-10
    volume=lambda tet:abs(np.linalg.det((tet[1:]-tet[0]).T))/6
    if np.all(ba>=-eps):return volume(a)
    if np.all(ab>=-eps):return volume(b)
    points=[*a[np.all(ba>=-eps,axis=1)],*b[np.all(ab>=-eps,axis=1)]]
    for tet,coordinates in ((a,ba),(b,ab)):
        for i,j in combinations(range(4),2):
            for k in range(4):
                denominator=coordinates[i,k]-coordinates[j,k]
                if abs(denominator)<1e-15:continue
                s=coordinates[i,k]/denominator
                if 0<=s<=1 and np.all((1-s)*coordinates[i]+s*coordinates[j]>=-eps):
                    points.append((1-s)*tet[i]+s*tet[j])
    if len(points)<4:return 0.
    points=np.unique(np.round(points,14),axis=0)
    if len(points)<4:return 0.
    centered=points-points.mean(axis=0)
    singular=np.linalg.svd(centered,compute_uv=False)
    if singular[0]==0 or singular[-1]<1e-10*singular[0]:return 0.
    scale=np.max(abs(centered))
    return float(ConvexHull(centered/scale).volume*scale**3)


def conservative_remap(source,target,quantities,source_labels,target_labels,tolerance=1e-8):
    """P0 conservative geometric projection; reject uncovered/duplicated material."""
    source=np.asarray(source);target=np.asarray(target);quantities=np.asarray(quantities)
    volume=lambda t:abs(np.linalg.det(np.stack([t[:,j]-t[:,0] for j in (1,2,3)],axis=-1)))/6
    sv,tv=volume(source),volume(target)
    if np.any(sv<=0) or np.any(tv<=0) or not np.isfinite(quantities).all():raise ValueError('finite nondegenerate input required')
    centers=source.mean(axis=1);radii=np.linalg.norm(source-centers[:,None,:],axis=-1).max(axis=1)
    tree=cKDTree(centers);covered=np.zeros(len(source));output=np.zeros((len(target),quantities.shape[1]))
    identical={(str(label),tet.tobytes()):j for j,(tet,label) in enumerate(zip(source,source_labels))}
    for i,tet in enumerate(target):
        same=identical.get((str(target_labels[i]),tet.tobytes()))
        if same is not None:
            covered[same]+=tv[i];output[i]=quantities[same]
            continue
        center=tet.mean(axis=0);radius=np.linalg.norm(tet-center,axis=1).max()
        candidates=tree.query_ball_point(center,radius+radii.max()+1e-12)
        total=0.
        for j in candidates:
            if source_labels[j]!=target_labels[i]:continue
            if np.any(source[j].max(axis=0)<tet.min(axis=0)-1e-12) or np.any(tet.max(axis=0)<source[j].min(axis=0)-1e-12):continue
            overlap=intersection_volume(source[j],tet)
            if overlap:
                covered[j]+=overlap;total+=overlap;output[i]+=overlap*quantities[j]
        if abs(total-tv[i])>tolerance*tv[i]:raise ValueError('target has uncovered or overlapping source material')
        output[i]/=tv[i]
    if np.any(abs(covered-sv)>tolerance*sv):raise ValueError('source material lost or duplicated by target geometry')
    return output,sv,tv


def source_quantities(source):
    T=source['fields']['T'];cells=source['connectivity']
    if not np.isfinite(T).all() or T.min()<253.15 or T.max()>353.15:
        raise ValueError('this remap benchmark supports only the solid first thermal-property segment')
    plastic=source['element_fields'].get('effective_plastic_strain')
    if plastic is None or len(plastic)!=len(cells):raise ValueError('actual elemental plastic history required')
    if np.max(abs(plastic))>1e-14:raise ValueError('plastic-history remap is not implemented; refusing to discard it')
    if not set(source['element_block_names'])<= {'plate','rod'}:raise ValueError('explicit rod/plate material labels required')
    bary=np.full((5,4),1/6);bary[0]=.25
    for j in range(4):bary[j+1,j]=.5
    qT=T[cells]@bary.T;weights=np.array([-.8,.45,.45,.45,.45])
    rho=(2661.42-.312*(qT-293.15))@weights
    energy=reference_enthalpy_density(qT)@weights
    return np.column_stack([rho,energy,rho*(source['element_block_names']=='rod')])


def transfer_state(source_exodus,target_coords,target_connectivity,p=None,*,target_block_names=None,tolerance=.02):
    if not math.isfinite(tolerance) or tolerance<=0:raise ValueError('positive tolerance required')
    if target_block_names is None:raise ValueError('target material labels required; block indices are not material identity')
    src=read_exodus_mesh(source_exodus);quantities=source_quantities(src)
    mapped,sv,tv=conservative_remap(src['curr_coords'][src['connectivity']],target_coords[target_connectivity],
        quantities,src['element_block_names'],np.asarray(target_block_names))
    before=sv@quantities;after=tv@mapped
    # Invert the same solid volumetric enthalpy primitive, rather than multiply
    # temperatures by a global ratio. Density is separately carried by remap.
    lower=np.full(len(tv),253.15);upper=np.full(len(tv),353.15)
    for _ in range(60):
        middle=(lower+upper)/2;mask=reference_enthalpy_density(middle)<mapped[:,1]
        lower=np.where(mask,middle,lower);upper=np.where(mask,upper,middle)
    temperature=(lower+upper)/2;origin=mapped[:,2]/mapped[:,0]
    error=abs(after-before)/np.maximum(abs(before),1e-20)
    report=dict(passed=bool(np.all(error<tolerance)),handoff_ready=False,
        scope='Cell-integrated elastic low-temperature remap only; no velocity, stress relaxation or flow initialization',
        relative_total_mass_error=float(error[0]),relative_thermal_energy_error=float(error[1]),relative_rod_mass_error=float(error[2]),
        target_min_T_K=float(temperature.min()),target_max_T_K=float(temperature.max()),
        source_mass_kg=float(before[0]),source_rod_mass_kg=float(before[2]),
        transferred_fields=['cell mass','reference-relative thermal enthalpy','rod-origin mass'],
        missing_handoff_fields=['velocity/momentum','elastic stress/energy compatibility','hot constitutive history'])
    return temperature,origin,report


def run_state_transfer_test(source_dir,tolerance=.02):
    src=read_exodus_mesh(source_dir/'dwell.e')
    # Refine actual source tetrahedra into four children. This exercises a
    # different target mesh; use a small mesh in unit tests for generic remaps.
    coords=src['curr_coords'].tolist();target=[];labels=[]
    for i,tet in enumerate(src['connectivity']):
        if i in (0,len(src['connectivity'])//2):
            center=len(coords);coords.append(src['curr_coords'][tet].mean(axis=0).tolist())
            for face in combinations(tet,3):target.append([*face,center]);labels.append(src['element_block_names'][i])
        else:target.append(tet.tolist());labels.append(src['element_block_names'][i])
    _,_,report=transfer_state(source_dir/'dwell.e',np.array(coords),np.array(target),
                             target_block_names=labels,tolerance=tolerance)
    report['source_cells']=len(src['connectivity']);report['target_cells']=len(target)
    (source_dir/'state_transfer_qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_dir',type=Path);parser.add_argument('--tolerance',type=float,default=.02)
    args=parser.parse_args();result=run_state_transfer_test(args.source_dir,args.tolerance)
    print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 2)
