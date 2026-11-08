#!/usr/bin/env python3
"""Audit the combined thermal budget of the small elastic contact qualification.

Restricted to the confirmed-geometry, implicit-Euler case with solved nodal heat,
the documented convection boundaries, and no plastic dissipation. Integrals use
reference volume, matching the current solid thermal kernels. This is not a
complete actuator/mechanical energy balance or a finite-deformation mass audit.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import numpy as np
from scipy.io import netcdf_file
from analyze_afsd_surface_flux import exterior_faces, tetra_determinants


def reference_enthalpy_density(temperature):
    # Exact primitive of rho(T)*cp(T) for the active first table segment.
    delta = temperature-293.15
    rho, cp, drho, dcp = 2661.42, 948.14, -.312, .601
    return rho*cp*delta + .5*(rho*dcp+cp*drho)*delta**2 + drho*dcp*delta**3/3


def stored_energy(reference, connectivity, temperature):
    barycentric = np.full((5,4),1/6)
    barycentric[0] = .25
    for i in range(4):
        barycentric[i+1,i] = .5
    weights = np.array([-.8,.45,.45,.45,.45])
    quadrature_T = temperature[connectivity] @ barycentric.T
    volume = abs(tetra_determinants(reference,connectivity))/6
    return float(volume @ (reference_enthalpy_density(quadrature_T) @ weights))


def assess(directory, tolerance):
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('finite positive tolerance required')
    case = json.loads((directory/'case.json').read_text())
    if case['kind'] != 'confirmed_geometry_contact_qualification':
        raise ValueError('only confirmed-geometry elastic contact qualification is supported')
    with (directory/'dwell.csv').open() as f:
        rows = [{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]
    if any(r['max_effective_plastic_strain'] > 1e-14 for r in rows):
        raise ValueError('plastic heat is active; this elastic-only budget is insufficient')
    with netcdf_file(directory/'dwell.e',mmap=False) as f:
        v = f.variables
        names = [b''.join(r).decode().strip('\x00 ') for r in v['name_nod_var'].data]
        T = np.array(v[f'vals_nod_var{names.index("T")+1}'].data)
        reference = np.column_stack([v['coord'+a].data for a in 'xyz'])
        blocks = [np.array(var.data,dtype=int)-1 for name,var in v.items() if name.startswith('connect')]
        if any(b.shape[1] != 4 for b in blocks):
            raise ValueError('linear tetrahedra required')
        connectivity = np.vstack(blocks)
        times = np.array(v['time_whole'].data)
    if (len(times) < 2 or abs(times[0]) > 1e-12 or not np.all(np.diff(times)>0)
            or len(rows) != len(times) or any(abs(r['time']-t)>1e-12 for r,t in zip(rows,times))):
        raise ValueError('matching initial and transient CSV/Exodus states required')
    if not np.isfinite(T).all() or T.min()<253.15 or T.max()>353.15:
        raise ValueError('temperature outside the supported first property segment')
    if np.max(abs(T[0]-293.15)) > 1e-10:
        raise ValueError('initial temperature must be uniform 293.15 K')
    geometry = case['process']['confirmed']
    plate_top = geometry['plate_thickness_mm']*.001
    rod_top = plate_top-case['initial_interference_mm']*.001+geometry['rod_length_mm']*.001
    convection = []
    for face,_ in exterior_faces(connectivity):
        points = reference[face]
        coefficient = (250. if np.all(abs(points[:,2])<1e-9) else
                       25. if (np.all(abs(points[:,2]-plate_top)<1e-9) or
                               np.all(abs(points[:,2]-rod_top)<1e-9)) else 0.)
        if coefficient:
            area = np.linalg.norm(np.cross(points[1]-points[0],points[2]-points[0]))/2
            convection.append((face,coefficient*area))
    energies = [stored_energy(reference,connectivity,t) for t in T]
    supplied, lost = 0.,0.
    records = []
    for i in range(1,len(times)):
        dt = times[i]-times[i-1]
        supplied += dt*rows[i]['friction_power_W']
        lost += dt*sum(weight*(T[i,face].mean()-293.15) for face,weight in convection)
        if supplied <= 0:
            raise ValueError('a positive source is required for relative-energy screening')
        error = energies[i]-energies[0]+lost-supplied
        records.append(dict(time_s=float(times[i]),stored_increment_J=energies[i]-energies[0],
                            generated_heat_J=supplied,convective_loss_J=lost,
                            thermal_balance_error_J=error,relative_to_generated_heat=error/supplied))
    worst = max(abs(r['relative_to_generated_heat']) for r in records)
    complete = abs(times[-1]-case['end_s'])<1e-12
    result = dict(passed=complete and worst<=tolerance,complete=complete,
                  scope='Reference-domain thermal budget in elastic, low-temperature contact qualification',
                  maximum_relative_thermal_error=worst,allowed_relative_error=tolerance,samples=records)
    (directory/'thermal_balance.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--tolerance',type=float,required=True)
    args = parser.parse_args()
    result = assess(args.directory,args.tolerance)
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['passed'] else 2)
