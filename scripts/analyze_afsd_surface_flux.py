#!/usr/bin/env python3
"""Separate fluid continuity from ALE surface leakage in circular qualification cases.

Requires NumPy/SciPy and serial, reference-coordinate Exodus with linear TET4
elements and the fields exported by create_afsd_circular_flow_case.py.
Outward flux is positive. This diagnostic does not correct the computed shape.
"""
import argparse
from collections import defaultdict
from itertools import combinations
import json
from pathlib import Path

import numpy as np
from scipy.io import netcdf_file


def exterior_faces(connectivity):
    faces = defaultdict(list)
    for tet in connectivity:
        for face in combinations(tet, 3):
            faces[tuple(sorted(face))].append(next(n for n in tet if n not in face))
    if any(len(adjacent) > 2 for adjacent in faces.values()):
        raise ValueError('nonmanifold tetrahedral mesh')
    return [(np.array(face), opposite[0]) for face, opposite in faces.items()
            if len(opposite) == 1]


def surface_fluxes(positions, faces, velocity, mesh_velocity, labels):
    result = {label: dict(area_m2=0., fluid_m3_s=0., mesh_m3_s=0.,
                          relative_m3_s=0., absolute_normal_leak_m3_s=0.)
              for label in set(labels)}
    for (face, opposite), label in zip(faces, labels):
        p = positions[face]
        area = np.cross(p[1]-p[0], p[2]-p[0])/2
        if np.dot(area, positions[opposite]-p.mean(axis=0)) > 0:
            area = -area
        fluid = float(velocity[face].mean(axis=0) @ area)
        mesh = float(mesh_velocity[face].mean(axis=0) @ area)
        entry = result[label]
        entry['area_m2'] += float(np.linalg.norm(area))
        entry['fluid_m3_s'] += fluid
        entry['mesh_m3_s'] += mesh
        entry['relative_m3_s'] += fluid-mesh
        # Exact integral of the signed linear flux; this sum of absolute face
        # integrals is a lower bound on the integral of absolute pointwise leak.
        entry['absolute_normal_leak_m3_s'] += abs(fluid-mesh)
    return result


def analyze(directory):
    case = json.loads((directory/'case.json').read_text())
    if case['kind'] != 'standalone_flow_qualification':
        raise ValueError('only circular qualification cases are supported')
    with netcdf_file(directory/'flow.e', mmap=False) as exodus:
        variables = exodus.variables
        names = [b''.join(row).decode().strip('\x00 ') for row in variables['name_nod_var'].data]
        fields = {name: np.array(variables[f'vals_nod_var{i+1}'].data)
                  for i, name in enumerate(names)}
        reference = np.column_stack([variables[f'coord{a}'].data for a in 'xyz'])
        blocks = [np.array(var.data, dtype=int)-1 for name, var in variables.items()
                  if name.startswith('connect')]
        if not blocks or any(block.shape[1] != 4 for block in blocks):
            raise ValueError('only linear TET4 blocks are supported')
        connectivity = np.vstack(blocks)
        times = np.array(variables['time_whole'].data)
    displacement = np.stack([fields[f'mesh_{a}'] for a in 'xyz'], axis=-1)
    velocity = np.stack([fields[f'velocity_{a}'] for a in 'xyz'], axis=-1)
    if len(times) < 2 or not np.all(np.diff(times) > 0):
        raise ValueError('at least two strictly increasing accepted times are required')
    if not all(np.isfinite(a).all() for a in (reference, times, displacement, velocity)):
        raise ValueError('nonfinite Exodus data')
    if abs(times[0]-case['start_s']) > 1e-10 or np.max(abs(displacement[0])) > 1e-12:
        raise ValueError('requires initial reference geometry with zero mesh displacement')
    faces = exterior_faces(connectivity)
    labels = []
    for face, _ in faces:
        p = reference[face]
        radius = np.hypot(p[:, 0], p[:, 1]-.0125)
        if np.all(abs(p[:, 2]-.010) < 1e-9):
            labels.append('plate')
        elif (np.all(abs(p[:, 2]-case.get('inlet_z_m', .010+case['initial_flow_height_m'])) < 1e-9)
              and np.all(radius <= case['rod_radius_m']+1e-9)):
            labels.append('inlet')
        else:
            labels.append('free_surface')
    if set(labels) != {'plate', 'inlet', 'free_surface'}:
        raise ValueError('geometry does not match the circular qualification case')
    records = []
    for i in range(1, len(times)):
        dt = times[i]-times[i-1]
        flux = surface_fluxes(reference+displacement[i], faces, velocity[i],
                              (displacement[i]-displacement[i-1])/dt, labels)
        incoming = -flux['inlet']['relative_m3_s']
        if incoming <= 0:
            raise ValueError('expected positive supplied material flux')
        records.append(dict(time_s=float(times[i]), boundaries=flux,
            fluid_net_relative_to_feed=sum(x['fluid_m3_s'] for x in flux.values())/incoming,
            free_surface_leak_relative_to_feed=flux['free_surface']['relative_m3_s']/incoming))
    return dict(scope='End-step surface flux diagnostic; not a time-integrated volume balance',
                sign='outward positive; negative free-surface relative flux means artificial influx',
                samples=records)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    result = analyze(args.directory)
    (args.directory/'surface_flux.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
