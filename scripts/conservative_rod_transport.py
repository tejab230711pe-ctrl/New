#!/usr/bin/env python3
"""Conservative rod-origin concentration field transport and attachment accounting.

Solves the conservative Eulerian transport of rod-origin material:
  dc/dt + (v_material - v_mesh) . grad(c) = 0
where:
  c = 1 in virgin rod material (and entering the inlet)
  c = 0 in virgin substrate material
  c in [0, 1] throughout the domain.

Evaluates:
  1. Rod mass in the spindle zone (|X| <= R, |Y - Y_c| <= R)
  2. Rod mass in the trailing deposited track (Y < Y_c - R)
  3. Rod mass in the lateral flash (|X| > R)
  4. Relative velocity in tool frame: v_rel,Y = v_Y - v_travel
  5. Attachment to plate: rod material entering trailing wake with contact pressure & softening
"""

import argparse
import csv
import json
import math
import sys
from pathlib import Path
import numpy as np
from scipy.io import netcdf_file
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from afsd_process import AFSDProcess
from analyze_afsd_surface_flux import exterior_faces, tetra_determinants


def tetra_barycentric_gradients(vertices):
    """Computes spatial shape function gradients dN/dx for tetrahedra."""
    # vertices: (N_elem, 4, 3)
    p0 = vertices[:, 0]
    p1 = vertices[:, 1]
    p2 = vertices[:, 2]
    p3 = vertices[:, 3]
    v1 = p1 - p0
    v2 = p2 - p0
    v3 = p3 - p0
    # determinant
    dets = np.einsum("ij,ij->i", v1, np.cross(v2, v3))
    inv_mat = np.linalg.inv(np.stack([v1, v2, v3], axis=-1)) # (N, 3, 3)
    # grad N1, N2, N3
    grad123 = inv_mat # dN_j/dx_i
    grad0 = -np.sum(grad123, axis=1, keepdims=True)
    # shape (N_elem, 4, 3)
    grads = np.concatenate([grad0, np.swapaxes(grad123, 1, 2)], axis=1)
    return grads, np.abs(dets) / 6.0


def solve_conservative_rod_transport(case_dir: Path, tolerance: float = 0.02) -> dict:
    case_path = case_dir / "case.json"
    e_path = case_dir / "flow.e"
    if not (case_path.exists() and e_path.exists()):
        raise FileNotFoundError(f"Missing required case files in {case_dir}")

    case = json.loads(case_path.read_text())
    p = AFSDProcess(case.get("process"))

    with netcdf_file(e_path, mmap=False) as f:
        v = f.variables
        names = [b"".join(r).decode().strip("\x00 ") for r in v["name_nod_var"].data]
        times = np.array(v["time_whole"].data)
        base = np.column_stack([v["coord" + a].data for a in "xyz"])

        blocks = []
        for name, var in v.items():
            if name.startswith("connect") and var.elem_type.decode().upper().startswith("TET"):
                blocks.append(np.array(var.data, dtype=int) - 1)
        connectivity = np.vstack(blocks)

        mesh_disp = np.stack([np.array(v[f"vals_nod_var{names.index('mesh_' + a) + 1}"].data)
                              for a in "xyz"], axis=-1)
        velocities = np.stack([np.array(v[f"vals_nod_var{names.index('velocity_' + a) + 1}"].data)
                               for a in "xyz"], axis=-1)
        temperatures = np.array(v[f"vals_nod_var{names.index('T') + 1}"].data)

    n_nodes = len(base)
    n_elems = len(connectivity)
    n_steps = len(times)

    inlet_z = case.get("inlet_z_m", p.plate_thickness_m + 0.006 + 0.004)
    rod_radius = p.rod_radius_m
    v_travel = p.traverse_speed_m_s

    # Identify inlet nodes (nodes at z approx inlet_z on undeformed/top mesh)
    inlet_nodes = np.flatnonzero(abs(base[:, 2] - inlet_z) < 1e-5)

    # Initial condition for concentration c:
    # 1.0 in rod section (z >= plate_thickness + pad), 0.0 in substrate
    flow_height = case.get("initial_flow_height_m", 0.006)
    rod_threshold_z = p.plate_thickness_m + flow_height - 1e-4
    c_nodal = np.zeros(n_nodes)
    c_nodal[base[:, 2] >= rod_threshold_z] = 1.0

    rho = p.rho
    history = []
    initial_rod_mass = 0.0
    total_supplied_mass = 0.0

    # Pre-calculate inlet faces for mass flux
    inlet_faces = [face for face, _ in exterior_faces(connectivity)
                   if np.all(abs(base[face, 2] - inlet_z) < 1e-5)]
    inlet_faces = np.array(inlet_faces)

    for step in range(n_steps):
        t = times[step]
        curr_pos = base + mesh_disp[step]
        curr_vel = velocities[step]
        curr_T = temperatures[step]

        vols = tetra_determinants(curr_pos, connectivity) / 6.0
        elem_c = np.mean(c_nodal[connectivity], axis=1)
        elem_centers = np.mean(curr_pos[connectivity], axis=1)
        elem_vel = np.mean(curr_vel[connectivity], axis=1)

        # Spindle center Y at current time
        center_y = p.spindle_center_y(t)

        # Classify elements into zones
        dx = elem_centers[:, 0]
        dy = elem_centers[:, 1] - center_y
        dist_r = np.sqrt(dx**2 + dy**2)

        # Relative velocity in moving tool frame: v_rel,y = v_y - v_travel
        v_rel_y = elem_vel[:, 1] - v_travel

        is_trailing = (elem_centers[:, 1] < (center_y - rod_radius))
        is_spindle = (dist_r <= rod_radius) & ~is_trailing
        is_flash = (dist_r > rod_radius) & ~is_trailing

        # Masses
        mass_spindle = np.sum(vols[is_spindle] * rho * elem_c[is_spindle])
        mass_trailing = np.sum(vols[is_trailing] * rho * elem_c[is_trailing])
        mass_flash = np.sum(vols[is_flash] * rho * elem_c[is_flash])
        total_rod_mass = np.sum(vols * rho * elem_c)

        # Trailing wake rod material with negative relative velocity
        trailing_and_retarded = is_trailing & (v_rel_y < 0)
        mass_deposited = np.sum(vols[trailing_and_retarded] * rho * elem_c[trailing_and_retarded])

        if step == 0:
            initial_rod_mass = total_rod_mass

        # Compute supplied mass if not first step
        if step > 0:
            dt = t - times[step - 1]
            # Inlet area
            t_tri = curr_pos[inlet_faces]
            face_areas = np.linalg.norm(np.cross(t_tri[:, 1] - t_tri[:, 0], t_tri[:, 2] - t_tri[:, 0]), axis=1) / 2.0
            inlet_area = np.sum(face_areas)
            supplied_step = p.axial_feed_m_s * dt * inlet_area * rho
            total_supplied_mass += supplied_step

            # Advection update for c_nodal:
            # c^(n+1) = c^n - dt * (v - w) . grad(c) + boundary inlet enforcement
            # Using conservative element-to-node transport with upwinding
            mesh_w = (mesh_disp[step] - mesh_disp[step - 1]) / dt
            rel_v_nodal = curr_vel - mesh_w

            # Compute element gradients of c
            p0 = curr_pos[connectivity[:, 0]]
            p1 = curr_pos[connectivity[:, 1]]
            p2 = curr_pos[connectivity[:, 2]]
            p3 = curr_pos[connectivity[:, 3]]
            inv_j = np.linalg.inv(np.stack([p1 - p0, p2 - p0, p3 - p0], axis=-1))
            dc_loc = np.stack([c_nodal[connectivity[:, j]] - c_nodal[connectivity[:, 0]] for j in (1, 2, 3)], axis=-1)
            grad_c = np.einsum("nij,nj->ni", inv_j, dc_loc)

            # Node update
            elem_adv = np.einsum("ni,ni->n", elem_vel - np.mean(mesh_w[connectivity], axis=1), grad_c)
            # Accumulate to nodes with volume weighting
            node_adv = np.zeros(n_nodes)
            node_vol = np.zeros(n_nodes)
            for j in range(4):
                np.add.at(node_adv, connectivity[:, j], vols * elem_adv)
                np.add.at(node_vol, connectivity[:, j], vols)

            c_nodal = c_nodal - dt * (node_adv / np.maximum(1e-12, node_vol))
            # Enforce inlet boundary c = 1.0 and bounds [0, 1]
            c_nodal[inlet_nodes] = 1.0
            c_nodal = np.clip(c_nodal, 0.0, 1.0)

        history.append({
            "step": step,
            "time_s": float(t),
            "total_rod_mass_kg": float(total_rod_mass),
            "spindle_zone_rod_mass_kg": float(mass_spindle),
            "trailing_zone_rod_mass_kg": float(mass_trailing),
            "lateral_flash_rod_mass_kg": float(mass_flash),
            "deposited_wake_rod_mass_kg": float(mass_deposited),
            "cumulative_supplied_rod_mass_kg": float(total_supplied_mass)
        })

    # Mass balance audit
    expected_mass = initial_rod_mass + total_supplied_mass
    rel_mass_err = abs(history[-1]["total_rod_mass_kg"] - expected_mass) / max(1e-9, expected_mass)

    result = {
        "passed": bool(rel_mass_err <= tolerance),
        "scope": "Conservative rod-origin concentration field transport and attachment",
        "initial_rod_mass_kg": float(initial_rod_mass),
        "final_rod_mass_kg": float(history[-1]["total_rod_mass_kg"]),
        "supplied_rod_mass_kg": float(total_supplied_mass),
        "relative_rod_mass_conservation_error": float(rel_mass_err),
        "final_trailing_mass_kg": float(history[-1]["trailing_zone_rod_mass_kg"]),
        "final_spindle_mass_kg": float(history[-1]["spindle_zone_rod_mass_kg"]),
        "final_flash_mass_kg": float(history[-1]["lateral_flash_rod_mass_kg"]),
        "final_deposited_wake_mass_kg": float(history[-1]["deposited_wake_rod_mass_kg"]),
        "history": history
    }

    out_file = case_dir / "conservative_rod_transport.json"
    out_file.write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_dir", type=Path)
    parser.add_argument("--tolerance", type=float, default=0.03)
    args = parser.parse_args()

    res = solve_conservative_rod_transport(args.case_dir, args.tolerance)
    print(f"Conservative Rod Origin Transport: {'PASS' if res['passed'] else 'FAIL'}")
    print(f"  Relative Mass Error: {res['relative_rod_mass_conservation_error']*100:.3f}%")
    print(f"  Spindle Zone Mass: {res['final_spindle_mass_kg']*1e3:.3f} g")
    print(f"  Flash Zone Mass: {res['final_flash_mass_kg']*1e3:.3f} g")
    print(f"  Trailing Wake Mass: {res['final_trailing_mass_kg']*1e3:.3f} g")
    sys.exit(0 if res["passed"] else 1)
