#!/usr/bin/env python3
"""Track volume-weighted rod particles through accepted circular ALE fields.

This is a passive Lagrangian diagnostic, not a conservative FE tracer equation.
It identifies initial upstream rod material and material entering the inlet.
The initially assumed hot pad has unknown origin and is not labeled as rod.
Escaped particles are recorded, never projected back onto the computed domain.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.io import netcdf_file
from scipy.spatial import cKDTree

from analyze_afsd_surface_flux import exterior_faces, tetra_determinants


class TetraInterpolator:
    def __init__(self, positions, connectivity, values):
        self.connectivity = connectivity
        self.vertices = positions[connectivity]
        self.origin = self.vertices[:, 0]
        self.inverse = np.linalg.inv(np.stack([self.vertices[:, j]-self.origin
                                               for j in (1, 2, 3)], axis=-1))
        self.values = values
        self.tree = cKDTree(self.vertices.mean(axis=1))
        self.lower = self.vertices.min(axis=1)-1e-11
        self.upper = self.vertices.max(axis=1)+1e-11

    def interpolate(self, points):
        output = np.full((len(points), self.values.shape[1]), np.nan)
        found = np.zeros(len(points), dtype=bool)
        if not len(points):
            return output, found
        finite_ids = np.flatnonzero(np.isfinite(points).all(axis=1))
        if not len(finite_ids):
            return output, found
        _, candidates = self.tree.query(points[finite_ids], k=min(24, len(self.connectivity)))
        if candidates.ndim == 1:
            candidates = candidates[:, None]
        for i, nearest in zip(finite_ids, candidates):
            point = points[i]
            # Nearest-centroid search is only an accelerator. The fallback is
            # exhaustive over bounding boxes, so thin tetrahedra are not lost.
            for selection in (nearest, np.flatnonzero(
                    np.all(point >= self.lower, axis=1) & np.all(point <= self.upper, axis=1))):
                coordinates = np.einsum('nij,nj->ni', self.inverse[selection],
                                         point-self.origin[selection])
                barycentric = np.column_stack((1-coordinates.sum(axis=1), coordinates))
                valid = np.flatnonzero(np.all(barycentric >= -1e-9, axis=1)
                                      & np.all(barycentric <= 1+1e-9, axis=1))
                if len(valid):
                    j = valid[0]
                    output[i] = barycentric[j] @ self.values[self.connectivity[selection[j]]]
                    found[i] = True
                    break
        return output, found


def trace(directory):
    case = json.loads((directory/'case.json').read_text())
    qualification = json.loads((directory/'qualification.json').read_text())
    if not qualification['passed']:
        raise ValueError('qualify the flow fields before interpreting rod trajectories')
    # Reject stale approval after a different solve overwrites the fields.
    import hashlib
    if hashlib.sha256((directory/'flow.e').read_bytes()).hexdigest() != qualification['artifact_sha256']['flow.e']:
        raise ValueError('Exodus differs from the qualified artifact')
    with netcdf_file(directory/'flow.e', mmap=False) as f:
        v = f.variables
        names = [b''.join(row).decode().strip('\x00 ') for row in v['name_nod_var'].data]
        fields = {name:np.array(v[f'vals_nod_var{i+1}'].data) for i,name in enumerate(names)}
        base = np.column_stack([v['coord'+a].data for a in 'xyz'])
        connectivity = np.vstack([np.array(var.data,dtype=int)-1
                                  for name,var in v.items() if name.startswith('connect')])
        times = np.array(v['time_whole'].data)
    positions = base + np.stack([fields['mesh_'+a] for a in 'xyz'], axis=-1)
    velocities = np.stack([fields['velocity_'+a] for a in 'xyz'], axis=-1)
    inlet_z = case['inlet_z_m']
    faces = [face for face,_ in exterior_faces(connectivity)
             if np.all(abs(base[face,2]-inlet_z) < 1e-9)]
    if not faces:
        raise ValueError('no inlet faces')
    faces = np.array(faces)
    centroid = base[connectivity].mean(axis=1)
    # Upstream mesh is conforming at the pad/rod interface.
    initial = np.all(base[connectivity,2] >= .010+case['initial_flow_height_m']-1e-10, axis=1)
    points = centroid[initial].copy()
    weights = abs(tetra_determinants(base, connectivity)[initial])/6
    initial_volume = float(weights.sum())
    birth = np.full(len(points), times[0])
    active = np.ones(len(points), dtype=bool)
    selected = np.unique(np.linspace(0, len(points)-1, min(64,len(points))).astype(int))
    trajectories = [[float(times[0]), int(j), *points[j], 1] for j in selected]
    supplied = 0.
    history = []
    for i in range(1, len(times)):
        dt = times[i]-times[i-1]
        middle_positions = .5*(positions[i]+positions[i-1])
        middle_velocity = .5*(velocities[i]+velocities[i-1])
        old = TetraInterpolator(positions[i-1], connectivity, velocities[i-1])
        middle = TetraInterpolator(middle_positions, connectivity, middle_velocity)
        current = TetraInterpolator(positions[i], connectivity, velocities[i])
        ids = np.flatnonzero(active)
        v0, ok0 = old.interpolate(points[ids])
        midpoint = points[ids]+.5*dt*v0
        vm, okm = middle.interpolate(midpoint)
        ok = ok0 & okm
        active[ids[~ok]] = False
        points[ids[ok]] += dt*vm[ok]
        # One inlet quadrature particle per triangle per interval. Its weight
        # is supplied volume, using the same trapezoidal area rule as the gate.
        triangles = middle_positions[faces]
        new_points = triangles.mean(axis=1)
        def areas(p):
            t = p[faces]
            return np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)/2
        new_weights = case['feed_m_per_s']*dt*.5*(areas(positions[i-1])+areas(positions[i]))
        inlet_v = middle_velocity[faces].mean(axis=1)
        new_points += .5*dt*inlet_v
        points = np.vstack((points, new_points))
        weights = np.r_[weights, new_weights]
        birth = np.r_[birth, np.full(len(faces), .5*(times[i]+times[i-1]))]
        active = np.r_[active, np.ones(len(faces), dtype=bool)]
        supplied += float(new_weights.sum())
        ids = np.flatnonzero(active)
        material_v, inside = current.interpolate(points[ids])
        active[ids[~inside]] = False
        trajectories.extend([[float(times[i]), int(j), *points[j], int(active[j])]
                             for j in selected])
        ids = ids[inside]
        relative_y = material_v[inside,1]-case['traverse_m_per_s']
        center_y = .0125+case['traverse_m_per_s']*(times[i]-case['start_s'])
        trailing = points[ids,1] < center_y-case['rod_radius_m']
        history.append(dict(time_s=float(times[i]), supplied_rod_volume_m3=supplied,
            tracked_active_rod_volume_m3=float(weights[active].sum()),
            escaped_or_unlocated_rod_volume_m3=float(weights[~active].sum()),
            rod_volume_with_negative_relative_y_velocity_m3=float(weights[ids[relative_y < 0]].sum()),
            rod_volume_in_trailing_region_m3=float(weights[ids[trailing]].sum())))
    with (directory/'rod_particles.csv').open('w') as stream:
        writer = csv.writer(stream)
        writer.writerow(['particle_id','birth_time_s','x_m','y_m','z_m','volume_weight_m3','located_in_domain'])
        for j in range(len(points)):
            writer.writerow([j,birth[j],*points[j],weights[j],int(active[j])])
    with (directory/'rod_trajectories.csv').open('w') as stream:
        writer = csv.writer(stream)
        writer.writerow(['time_s','particle_id','x_m','y_m','z_m','located_in_domain'])
        writer.writerows(trajectories)
    report = dict(scope='Passive rod-origin particles, not a validated marker concentration or deposited mass',
                  integrator='midpoint RK2 on linearly interpolated accepted fields',
                  initial_rod_volume_m3=initial_volume, supplied_volume_m3=supplied,
                  accounting_error_m3=float(weights.sum())-initial_volume-supplied,
                  particle_count=len(points), history=history,
                  warning='Negative tool-relative Y velocity alone does not prove deposition; inspect trailing rod-origin volume and trajectories. Particle/time/mesh refinement is required.')
    (directory/'rod_transport.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    args = parser.parse_args()
    result = trace(args.directory)
    print(json.dumps({k:v for k,v in result.items() if k != 'history'},indent=2))
    print(json.dumps(result['history'][-1],indent=2))
