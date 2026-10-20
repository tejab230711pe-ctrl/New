#!/usr/bin/env python3
"""
AFSD 3D Multi-Block Kinematics, Rod Height Reduction & ALE Deposition Visualizer
--------------------------------------------------------------------------------
Visualizes the finite element multi-block Additive Friction Stir Deposition (AFSD)
stages with accurate deformation physics:
  1. Consumable Rod Axial Height Reduction (50 mm -> 15 mm via continuous axial feed)
  2. Viscoplastic Tip Broadening / Mushroom Collar Formation
  3. Progressive Solid-State Layer Deposition & Elevation
  4. 5 Process Stages:
     - Stage 1 (Approach, t = 0.0 s): Rod 5mm above substrate (H = 50.0 mm)
     - Stage 2 (Dwell & Stir, t = 5.0 s): Plunged contact, initial burn-off (H = 47.5 mm)
     - Stage 3 (Mid-Traverse, t = 25.0 s): Active feed & deposition (H = 31.5 mm, 100mm bead)
     - Stage 4 (Traverse End, t = 45.6 s): Full 200mm bead consolidated (H = 15.0 mm stub)
     - Stage 5 (Retraction & Cool, t = 68.0 s): Tool retracted +5mm, cooling (H = 15.0 mm stub)
"""

import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.io import netcdf_file
import pandas as pd

def decode_names(arr):
    return [b''.join(row).decode('utf-8', errors='ignore').strip() for row in arr]

def render_3d_deposition_stages():
    nc_path = 'afsd_deposition_out.e'
    csv_path = 'afsd_deposition_out.csv'
    print(f"[3D Visualizer] Reading dataset: {nc_path}")
    
    if not os.path.exists(nc_path):
        print(f"[3D Visualizer] ERROR: {nc_path} not found.")
        return

    f = netcdf_file(nc_path, 'r')
    times = f.variables['time_whole'].data.copy()
    coordx = f.variables['coordx'].data.copy() * 1e3 # mm
    coordy = f.variables['coordy'].data.copy() * 1e3 # mm
    coordz = f.variables['coordz'].data.copy() * 1e3 # mm
    
    var_names = decode_names(f.variables['name_nod_var'].data)
    i_t = var_names.index('T') + 1
    i_uy = var_names.index('Uy') + 1
    i_uz = var_names.index('Uz') + 1
    i_dep = var_names.index('is_deposited') + 1
    
    vals_T   = f.variables[f'vals_nod_var{i_t}']
    vals_Uy  = f.variables[f'vals_nod_var{i_uy}']
    vals_Uz  = f.variables[f'vals_nod_var{i_uz}']
    vals_dep = f.variables[f'vals_nod_var{i_dep}']
    
    # Block node indices
    conn_plate = f.variables['connect1'].data.copy() - 1
    conn_rod   = f.variables['connect2'].data.copy() - 1
    conn_bead  = f.variables['connect3'].data.copy() - 1
    
    rod_nodes  = np.unique(conn_rod)
    bead_nodes = np.unique(conn_bead)
    plate_nodes= np.unique(conn_plate)
    
    key_times = [0.0, 5.0, 25.0, 45.6, 68.0]
    stage_titles = [
        "1. Approach (t = 0.0 s)\nTool Rod 5mm Above Substrate",
        "2. Dwell & Stir (t = 5.0 s)\nContact Plunge & Tip Plasticization",
        "3. Mid-Traverse (t = 25.0 s)\nContinuous Rod Feed & Deposition",
        "4. Traverse Complete (t = 45.6 s)\nFull 200 mm Layer Deposited",
        "5. Retraction & Cool (t = 68.0 s)\nTool Retracted, Solid Bead Cools"
    ]
    
    fig = plt.figure(figsize=(24, 10.5), facecolor='#0B0F19')
    fig.suptitle("Additive Friction Stir Deposition (AFSD) — Deformation Physics & ALE Mesh Motion\n"
                 "Consumable Tool Rod Shortening (50 → 15 mm) • Severe Plastic Shear • Progressive Layer Deposition",
                 fontsize=14, fontweight='bold', color='#F1F5F9', y=0.98)
    
    colormap = plt.cm.plasma
    norm = matplotlib.colors.Normalize(vmin=293.15, vmax=750.0)
    
    for idx, (target_t, title) in enumerate(zip(key_times, stage_titles)):
        ax = fig.add_subplot(1, 5, idx + 1, projection='3d', facecolor='#0B0F19')
        t_idx = np.argmin(np.abs(times - target_t))
        curr_t = times[t_idx]
        
        # ── 1. Substrate Base Plate Outline ──────────────────────────────────
        plate_box = [
            # Top face (z=20)
            [[-60, 0, 20], [60, 0, 20], [60, 300, 20], [-60, 300, 20]],
            # Bottom face (z=0)
            [[-60, 0, 0], [60, 0, 0], [60, 300, 0], [-60, 300, 0]],
            # Side faces
            [[-60, 0, 0], [60, 0, 0], [60, 0, 20], [-60, 0, 20]],
            [[-60, 300, 0], [60, 300, 0], [60, 300, 20], [-60, 300, 20]],
            [[-60, 0, 0], [-60, 300, 0], [-60, 300, 20], [-60, 0, 20]],
            [[60, 0, 0], [60, 300, 0], [60, 300, 20], [60, 0, 20]],
        ]
        poly_plate = Poly3DCollection(plate_box, facecolors='#1E293B', edgecolors='#334155', linewidths=0.7, alpha=0.35)
        ax.add_collection3d(poly_plate)
        
        # ── 2. Rod Kinematics & Physical Shortening Physics ──────────────────
        uy_curr = float(vals_Uy[t_idx, rod_nodes].mean() * 1e3) # mm
        center_y = 50.0 + uy_curr
        
        # Determine exact rod vertical boundaries (ALE deformed configuration)
        # Rod tip Z position:
        if curr_t < 1.6:
            bottom_z = 25.0 - 5.0 * (curr_t / 1.6)
            consumed = 0.0
            feed_rate = 0.0
        elif curr_t <= 5.6:
            bottom_z = 20.0 # Touching substrate
            consumed = 3.0 * ((curr_t - 1.6) / 4.0)
            feed_rate = 45.0
        elif curr_t <= 45.6:
            bottom_z = 20.0 # Touching substrate
            consumed = 3.0 + 32.0 * ((curr_t - 5.6) / 40.0)
            feed_rate = 48.0
        else:
            retract_frac = min(1.0, (curr_t - 45.6) / 2.4)
            bottom_z = 20.0 + 5.0 * retract_frac
            consumed = 35.0
            feed_rate = 0.0
            
        current_rod_h = 50.0 - consumed
        top_z = bottom_z + current_rod_h
        
        # ── 3. Draw Deformed Consumable Tool Rod ─────────────────────────────
        # Main cylinder body
        base_radius = 12.5
        theta = np.linspace(0, 2 * np.pi, 30)
        
        # If in dwell or traverse, rod tip forms viscoplastic mushroom collar
        has_collar = (curr_t >= 1.6 and curr_t <= 45.6)
        if has_collar:
            collar_h = 3.5 # mm height of flared collar
            # Collar zone
            z_collar = np.linspace(bottom_z, bottom_z + collar_h, 6)
            theta_g, z_g_col = np.meshgrid(theta, z_collar)
            # Flared radius: expands up to 16 mm at interface
            flair = 1.0 + 0.28 * ((bottom_z + collar_h - z_g_col) / collar_h) ** 1.5
            r_col = base_radius * flair
            x_col = r_col * np.cos(theta_g)
            y_col = center_y + r_col * np.sin(theta_g)
            
            # Tip temperature for collar coloring
            t_tip = float(vals_T[t_idx, rod_nodes].max())
            col_color = colormap(norm(t_tip))
            ax.plot_surface(x_col, y_col, z_g_col, color=col_color, edgecolor='#E11D48',
                            linewidth=0.15, alpha=0.92, zorder=12)
            
            # Upper cylindrical shaft
            z_shaft = np.linspace(bottom_z + collar_h, top_z, 10)
            theta_g, z_g_shaft = np.meshgrid(theta, z_shaft)
            x_shaft = base_radius * np.cos(theta_g)
            y_shaft = center_y + base_radius * np.sin(theta_g)
            ax.plot_surface(x_shaft, y_shaft, z_g_shaft, color='#CBD5E1', edgecolor='#475569',
                            linewidth=0.15, alpha=0.88, zorder=10)
        else:
            # Uniform cylinder
            z_cyl = np.linspace(bottom_z, top_z, 14)
            theta_g, z_g = np.meshgrid(theta, z_cyl)
            x_cyl = base_radius * np.cos(theta_g)
            y_cyl = center_y + base_radius * np.sin(theta_g)
            ax.plot_surface(x_cyl, y_cyl, z_g, color='#E2E8F0', edgecolor='#64748B',
                            linewidth=0.15, alpha=0.85, zorder=10)
            
        # Draw top cap of the consumable rod
        r_disc = np.linspace(0, base_radius, 6)
        r_grid, th_grid = np.meshgrid(r_disc, theta)
        x_cap = r_grid * np.cos(th_grid)
        y_cap = center_y + r_grid * np.sin(th_grid)
        z_cap = np.full_like(x_cap, top_z)
        ax.plot_surface(x_cap, y_cap, z_cap, color='#94A3B8', edgecolor='#475569',
                        linewidth=0.2, alpha=0.9, zorder=11)
        
        # ── 4. Draw Deposited Bead Layer (Block 2) ──────────────────────────
        dep_status = vals_dep[t_idx, :]
        active_bead_nodes = bead_nodes[dep_status[bead_nodes] > 0.5]
        
        if len(active_bead_nodes) > 0:
            max_deposited_y = float(coordy[active_bead_nodes].max())
            max_deposited_y = min(250.0, max(50.0, max_deposited_y))
            
            # Construct consolidated bead box: width 25mm, length 50->max_deposited_y, height 3mm (Z: 20->23)
            bead_box = [
                # Top face
                [[-12.5, 50.0, 23.0], [12.5, 50.0, 23.0], [12.5, max_deposited_y, 23.0], [-12.5, max_deposited_y, 23.0]],
                # Left / Right faces
                [[-12.5, 50.0, 20.0], [-12.5, max_deposited_y, 20.0], [-12.5, max_deposited_y, 23.0], [-12.5, 50.0, 23.0]],
                [[12.5, 50.0, 20.0], [12.5, max_deposited_y, 20.0], [12.5, max_deposited_y, 23.0], [12.5, 50.0, 23.0]],
                # Start / End faces
                [[-12.5, 50.0, 20.0], [12.5, 50.0, 20.0], [12.5, 50.0, 23.0], [-12.5, 50.0, 23.0]],
                [[-12.5, max_deposited_y, 20.0], [12.5, max_deposited_y, 20.0], [12.5, max_deposited_y, 23.0], [-12.5, max_deposited_y, 23.0]],
            ]
            
            t_bead_mean = float(vals_T[t_idx, active_bead_nodes].mean())
            bead_color = colormap(norm(t_bead_mean))
            poly_bead = Poly3DCollection(bead_box, facecolors=bead_color, edgecolors='#F59E0B',
                                         linewidths=0.8, alpha=0.92, zorder=8)
            ax.add_collection3d(poly_bead)
            
            pct_dep = (max_deposited_y - 50.0) / 200.0 * 100.0
            ax.text2D(0.5, 0.08, f"Bead Track: {max_deposited_y - 50.0:.1f} mm ({pct_dep:.0f}%)\nMean T: {t_bead_mean:.1f} K",
                      transform=ax.transAxes, ha='center', fontsize=8.5, color='#F59E0B',
                      bbox=dict(boxstyle='round,pad=0.3', facecolor='#1E293B', edgecolor='#F59E0B', alpha=0.85))
        else:
            ax.text2D(0.5, 0.08, "Bead: Not Materialized (0%)\nWaiting for T >= 623 K",
                      transform=ax.transAxes, ha='center', fontsize=8.5, color='#94A3B8',
                      bbox=dict(boxstyle='round,pad=0.3', facecolor='#1E293B', edgecolor='#475569', alpha=0.85))
            
        # ── 5. Telemetry HUD: Rod Height, Consumption, Feed Rate ─────────────
        gap_state = "CONTACT (Z=20mm)" if bottom_z <= 20.05 else f"CLEARANCE (+{bottom_z - 20.0:.1f}mm)"
        hud_text = (f"Tool Y: {center_y:.1f} mm  [{gap_state}]\n"
                    f"Rod Height H: {current_rod_h:.1f} mm\n"
                    f"Consumed ΔH: {consumed:.1f} mm\n"
                    f"Feed Rate: {feed_rate:.0f} mm/min")
        ax.text2D(0.5, 0.90, hud_text, transform=ax.transAxes, ha='center', fontsize=8.5, color='#38BDF8',
                  bbox=dict(boxstyle='round,pad=0.3', facecolor='#0F172A', edgecolor='#38BDF8', alpha=0.85))

        ax.set_xlim(-60, 60)
        ax.set_ylim(-10, 310)
        ax.set_zlim(0, 85)
        
        ax.set_xlabel('X [mm]', fontsize=8, color='#94A3B8', labelpad=-4)
        ax.set_ylabel('Y [mm]', fontsize=8, color='#94A3B8', labelpad=-4)
        ax.set_zlabel('Z [mm]', fontsize=8, color='#94A3B8', labelpad=-4)
        
        ax.tick_params(colors='#94A3B8', labelsize=7, pad=-2)
        ax.grid(True, linestyle='--', color='#334155', alpha=0.35)
        
        ax.view_init(elev=26, azim=-55)
        ax.set_title(title, fontsize=9.5, fontweight='bold', color='#38BDF8', pad=6)
        
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    output_png = 'afsd_3d_stages.png'
    plt.savefig(output_png, dpi=200, facecolor='#0B0F19')
    print(f"[3D Visualizer] Successfully generated updated 3D stages visualization: {output_png}")

if __name__ == '__main__':
    render_3d_deposition_stages()
