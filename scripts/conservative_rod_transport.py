#!/usr/bin/env python3
"""Offline conservative cell-average rod tracer on accepted ALE tetrahedral fields.

Shared-face donor-cell fluxes, geometric swept volumes, CFL substeps and no
concentration clipping. A reported flux projection enforces cellwise continuity
of the weakly divergence-free FE velocity. This is not a MOOSE-coupled tracer or
an attachment/bonding model. The assumed hot pad's origin remains unspecified.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from scipy.io import netcdf_file
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import factorized
from analyze_afsd_surface_flux import tetra_determinants
from afsd_process import AFSDProcess


def tetra_barycentric_gradients(vertices):
    jac=np.stack([vertices[:,j]-vertices[:,0] for j in (1,2,3)],axis=-1)
    rows=np.linalg.inv(jac)
    return np.concatenate([-rows.sum(axis=1,keepdims=True),rows],axis=1),abs(np.linalg.det(jac))/6


def face_topology(points,cells):
    pending={}; faces=[]; owner=[]; neighbor=[]
    for i,tet in enumerate(cells):
        for opposite in range(4):
            face=[tet[j] for j in range(4) if j!=opposite]
            key=tuple(sorted(face))
            if key in pending:
                index=pending[key]
                if neighbor[index]>=0: raise ValueError('nonmanifold mesh')
                neighbor[index]=i
            else:
                p=points[face]
                if np.dot(np.cross(p[1]-p[0],p[2]-p[0]),points[tet[opposite]]-p[0])>0:
                    face[1],face[2]=face[2],face[1]
                pending[key]=len(faces);faces.append(face);owner.append(i);neighbor.append(-1)
    return np.array(faces),np.array(owner),np.array(neighbor)


def integrated_flux(x0,x1,v0,v1,faces,dt):
    fluid=np.zeros(len(faces)); mesh=np.zeros(len(faces))
    w=(x1-x0)/dt
    # Two Gauss points exactly integrate degree-three flux on linearly moving faces.
    for s in [.5-.5/math.sqrt(3),.5+.5/math.sqrt(3)]:
        points=((1-s)*x0+s*x1)[faces]
        area=np.cross(points[:,1]-points[:,0],points[:,2]-points[:,0])/2
        fluid+=dt*.5*np.einsum('ij,ij->i',area,((1-s)*v0+s*v1)[faces].mean(axis=1))
        mesh+=dt*.5*np.einsum('ij,ij->i',area,w[faces].mean(axis=1))
    return fluid,mesh


class FluxTransport:
    def __init__(self,points,cells,inlet_faces):
        self.cells=cells
        self.faces,self.owner,self.neighbor=face_topology(points,cells)
        self.internal=self.neighbor>=0
        self.boundary=~self.internal
        self.inlet=np.asarray(inlet_faces(self.faces),dtype=bool)&self.boundary
        if not self.inlet.any(): raise ValueError('no inlet faces found')
        ids=np.arange(len(self.faces)); inside=ids[self.internal]
        self.B=coo_matrix((np.r_[np.ones(len(ids)),-np.ones(len(inside))],
            (np.r_[self.owner,self.neighbor[self.internal]],np.r_[ids,inside])),
            shape=(len(cells),len(ids))).tocsr()
        self.A=self.B[:,self.internal]
        lap=(self.A@self.A.T).tocsc()
        # Connected mesh, one pressure gauge. Singular disconnected domains fail.
        self.solve=factorized(lap[1:,1:]) if len(cells)>1 else None
        self.sign=np.sign(tetra_determinants(points,cells))

    def volumes(self,x):
        determinant=tetra_determinants(x,self.cells)
        if np.any(determinant*self.sign<=0): raise ValueError('inverted or degenerate tetrahedron')
        return abs(determinant)/6

    def step(self,x0,x1,v0,v1,c,dt):
        V0,V1=self.volumes(x0),self.volumes(x1)
        fluid,mesh=integrated_flux(x0,x1,v0,v1,self.faces,dt)
        original=fluid.copy()
        # Preserve all boundary fluxes except distribute roundoff/global imbalance
        # over inlet. Report this correction; never conceal it in a mass rescale.
        mismatch=float(fluid[self.boundary].sum())
        fluid[self.inlet]-=mismatch/self.inlet.sum()
        divergence=self.B@fluid
        potential=np.zeros(len(c))
        if self.solve is not None: potential[1:]=self.solve(divergence[1:])
        fluid[self.internal]-=self.A.T@potential
        if np.max(abs(self.B@fluid))>1e-10*max(1e-30,abs(fluid).sum()):
            raise ValueError('flux projection failed')
        relative=fluid-mesh
        gcl=np.max(abs((self.B@mesh)-(V1-V0)))
        if gcl>1e-10*max(V0.max(),V1.max()): raise ValueError('geometric conservation failed')
        donor=c[self.owner].copy()
        incoming=relative<0
        internal_in=incoming&self.internal
        donor[internal_in]=c[self.neighbor[internal_in]]
        external_in=incoming&self.boundary
        donor[external_in]=self.inlet[external_in].astype(float)
        outgoing=np.maximum(relative,0.)
        out_per_cell=np.bincount(self.owner,weights=outgoing,minlength=len(c))
        out_per_cell+=np.bincount(self.neighbor[self.internal],
            weights=np.maximum(-relative[self.internal],0.),minlength=len(c))
        if np.max(out_per_cell/V0)>.8: raise ValueError('CFL exceeded; use more substeps')
        transported=relative*donor
        mass=c*V0-self.B@transported
        next_c=mass/V1
        if next_c.min() < -1e-10 or next_c.max()>1+1e-10:
            raise ValueError('unbounded concentration; no clipping applied')
        supplied=-transported[self.boundary&incoming].sum()
        escaped=transported[self.boundary&~incoming].sum()
        return next_c,dict(supplied=float(supplied),escaped=float(escaped),
            boundary_correction=abs(mismatch),projection_l1=float(abs(fluid-original).sum()),
            fluid_l1=float(abs(original).sum()),gcl_error=float(gcl))


def solve_conservative_rod_transport(case_dir,tolerance=.02):
    if not math.isfinite(tolerance) or tolerance<=0: raise ValueError('positive tolerance required')
    case=json.loads((case_dir/'case.json').read_text())
    certificate=json.loads((case_dir/'qualification.json').read_text())
    if certificate.get('passed') is not True: raise ValueError('passing flow qualification required')
    for name,digest in certificate['artifact_sha256'].items():
        if hashlib.sha256((case_dir/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('stale qualification: '+name)
    p=AFSDProcess(case.get('process'))
    with netcdf_file(case_dir/'flow.e',mmap=False) as f:
        v=f.variables
        names=[b''.join(r).decode().strip('\x00 ') for r in v['name_nod_var'].data]
        field=lambda name:np.array(v[f'vals_nod_var{names.index(name)+1}'].data)
        base=np.column_stack([v['coord'+a].data for a in 'xyz'])
        cells=np.vstack([np.array(var.data,dtype=int)-1 for name,var in v.items() if name.startswith('connect')])
        if cells.shape[1]!=4: raise ValueError('TET4 required')
        positions=base+np.stack([field('mesh_'+a) for a in 'xyz'],axis=-1)
        velocity=np.stack([field('velocity_'+a) for a in 'xyz'],axis=-1)
        times=np.array(v['time_whole'].data)
    if len(times)<2 or not np.all(np.diff(times)>0): raise ValueError('increasing accepted times required')
    inlet_z=case['inlet_z_m']
    transport=FluxTransport(base,cells,lambda faces:np.all(abs(base[faces,2]-inlet_z)<1e-9,axis=1))
    pad_top=inlet_z-case['inlet_extension_m']
    c=np.all(base[cells,2]>=pad_top-1e-10,axis=1).astype(float)
    rho=p.rho; initial=float(c@transport.volumes(positions[0]))
    supplied=escaped=projection=fluid_total=boundary_correction=0.
    history=[]
    for i,t in enumerate(times):
        if i:
            dt=times[i]-times[i-1]
            qf,qm=integrated_flux(positions[i-1],positions[i],velocity[i-1],velocity[i],transport.faces,dt)
            scale=np.bincount(transport.owner,weights=abs(qf-qm),minlength=len(c))
            scale+=np.bincount(transport.neighbor[transport.internal],weights=abs((qf-qm)[transport.internal]),minlength=len(c))
            count=max(1,math.ceil(4*np.max(scale/transport.volumes(positions[i-1]))))
            if count>10000: raise ValueError('excessive CFL substeps')
            for step in range(count):
                a,b=step/count,(step+1)/count
                mix=lambda field,s:(1-s)*field[i-1]+s*field[i]
                c,info=transport.step(mix(positions,a),mix(positions,b),mix(velocity,a),mix(velocity,b),c,dt/count)
                supplied+=info['supplied'];escaped+=info['escaped']
                projection+=info['projection_l1'];fluid_total+=info['fluid_l1'];boundary_correction+=info['boundary_correction']
        mass=rho*c*transport.volumes(positions[i])
        centers=positions[i,cells].mean(axis=1)
        center_y=p.spindle_center_y(float(t));radius=case['rod_radius_m']
        trailing=centers[:,1]<center_y-radius
        spindle=(np.hypot(centers[:,0],centers[:,1]-center_y)<=radius)&~trailing
        outside=~(trailing|spindle)
        error=float(mass.sum()/rho+escaped-initial-supplied)
        history.append(dict(time_s=float(t),total_rod_mass_kg=float(mass.sum()),
            trailing_zone_rod_mass_kg=float(mass[trailing].sum()),spindle_zone_rod_mass_kg=float(mass[spindle].sum()),
            outside_footprint_rod_mass_kg=float(mass[outside].sum()),c_min=float(c.min()),c_max=float(c.max()),
            cumulative_supplied_rod_mass_kg=rho*supplied,cumulative_escaped_rod_mass_kg=rho*escaped,
            mass_error_kg=rho*error))
    error=abs(history[-1]['mass_error_kg'])
    relative=error/max(rho*supplied,1e-30)
    projection_error=projection/max(fluid_total,1e-30)
    boundary_error=boundary_correction/max(supplied,1e-30)
    result=dict(passed=bool(relative<=tolerance and projection_error<=tolerance and boundary_error<=tolerance),
        mass_accounting_passed=bool(relative<=tolerance),allowed_relative_error=tolerance,scope='Offline conservative FV tracer with explicitly projected FE flux; no attachment model',
        coupled_to_moose=False,attachment_verified=False,relative_rod_mass_conservation_error=relative,
        initial_rod_mass_kg=rho*initial,final_rod_mass_kg=history[-1]['total_rod_mass_kg'],supplied_rod_mass_kg=rho*supplied,
        escaped_rod_mass_kg=rho*escaped,flux_projection_relative_l1=projection/max(fluid_total,1e-30),
        boundary_flux_correction_relative_to_feed=boundary_correction/max(supplied,1e-30),
        final_trailing_mass_kg=history[-1]['trailing_zone_rod_mass_kg'],history=history,
        source_artifact_sha256=certificate['artifact_sha256'])
    np.savez_compressed(case_dir/'rod_concentration.npz',concentration=c,connectivity=cells,positions=positions[-1])
    (case_dir/'conservative_rod_transport.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case_dir',type=Path);parser.add_argument('--tolerance',type=float,default=.02)
    args=parser.parse_args();result=solve_conservative_rod_transport(args.case_dir,args.tolerance)
    print(json.dumps({k:v for k,v in result.items() if k!='history'},indent=2))
    raise SystemExit(0 if result['passed'] else 2)
