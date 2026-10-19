#!/usr/bin/env python3
"""
AFSD 3D Multi-Block Kinematics & Progressive Deposition Visualizer
-----------------------------------------------------------------
Extracts nodal coordinates, displacement vectors (Ux, Uy, Uz), and 
deposition state (is_deposited, T) from afsd_deposition_out.e to render
3D physical stages of the Additive Friction Stir Deposition process:
  1. Initial Position (Approach): Rod hovering 5 mm above plate (t = 0.0 s)
  2. Dwell & Plunge: Rod lowered into contact, rotating & heating (t = 5.0 s)
  3. Mid-Traverse: Rod actively depositing bead along centerline (t = 25.0 s)
  4. End of Traverse: Tool reaching final deposition boundary (t = 45.6 s)
  5. Retraction & Cool: Tool retracted upwards, full bead consolidated (t = 68.0 s)
"""

import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.io import netcdf_file

def decode_names(arr):
    return [b''.join(row).decode('utf-8', errors='ignore').strip() for row in arr]

def render_3d_deposition_stages():
    nc_path = 'afsd_deposition_out.e'
    print(f"[3D Visualizer] Reading Exodus dataset: {nc_path}")
    
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
        "2. Dwell & Stir (t = 5.0 s)\nContact Preload & Frictional Heat",
        "3. Traverse Deposition (t = 25.0 s)\nBead Forms at T >= T_plast",
        "4. Traverse Complete (t = 45.6 s)\nFull 200 mm Layer Deposited",
        "5. Retraction & Cool (t = 68.0 s)\nTool Retracted, Solid Bead Cools"
    ]
    
    fig = plt.figure(figsize=(22, 10), facecolor='#0D1117')
    fig.suptitle("AFSD 3D Multi-Block Finite Element Model — Tool Motion & Layer Deposition\nRotating Consumable Tool Rod (Block 1) • Substrate Base Plate (Block 0) • Materialized Bead (Block 2)",
                 fontsize=14, fontweight='bold', color='#E6EDF3', y=0.98)
    
    colormap = plt.cm.plasma
    norm = matplotlib.colors.Normalize(vmin=293.15, vmax=750.0)
    
    for idx, (target_t, title) in enumerate(zip(key_times, stage_titles)):
        ax = fig.add_subplot(1, 5, idx + 1, projection='3d', facecolor='#0D1117')
        t_idx = np.argmin(np.abs(times - target_t))
        curr_t = times[t_idx]
        
        # Substrate plate outline / box
        # Plate dimensions: X [-60, 60], Y [0, 300], Z [0, 20] mm
        plate_box = [
            # Top face
            [[-60, 0, 20], [60, 0, 20], [60, 300, 20], [-60, 300, 20]],
            # Bottom face
            [[-60, 0, 0], [60, 0, 0], [60, 300, 0], [-60, 300, 0]],
            # Side faces
            [[-60, 0, 0], [60, 0, 0], [60, 0, 20], [-60, 0, 20]],
            [[-60, 300, 0], [60, 300, 0], [60, 300, 20], [-60, 300, 20]],
            [[-60, 0, 0], [-60, 300, 0], [-60, 300, 20], [-60, 0, 20]],
            [[60, 0, 0], [60, 300, 0], [60, 300, 20], [60, 0, 20]],
        ]
        poly_plate = Poly3DCollection(plate_box, facecolors='#1E293B', edgecolors='#334155', linewidths=0.8, alpha=0.35)
        ax.add_collection3d(poly_plate)
        
        # Current tool displacement
        uy_curr = vals_Uy[t_idx, rod_nodes].mean() * 1e3 # mm
        uz_curr = vals_Uz[t_idx, rod_nodes].mean() * 1e3 # mm
        
        # Tool rod geometry displaced
        rod_x = coordx[rod_nodes]
        rod_y = coordy[rod_nodes] + uy_curr
        rod_z = coordz[rod_nodes] + uz_curr
        
        # Draw tool rod as a 3D cylinder
        # Center at (0, 50 + uy_curr), z from (25 + uz_curr) to (75 + uz_curr)
        center_y = 50.0 + uy_curr
        bottom_z = 25.0 + uz_curr
        top_z    = 75.0 + uz_curr
        radius   = 12.5
        
        theta = np.linspace(0, 2*np.pi, 24)
        z_cyl = np.linspace(bottom_z, top_z, 6)
        theta_grid, z_grid = np.meshgrid(theta, z_cyl)
        x_cyl = radius * np.cos(theta_grid)
        y_cyl = center_y + radius * np.sin(theta_grid)
        
        rod_surf = ax.plot_surface(x_cyl, y_cyl, z_grid, color='#E2E8F0', edgecolor='#64748B',
                                   linewidth=0.2, alpha=0.85, zorder=10)
        
        # Deposited bead elements
        dep_status = vals_dep[t_idx, :]
        active_bead_nodes = bead_nodes[dep_status[bead_nodes] > 0.5]
        
        if len(active_bead_nodes) > 0:
            # Active bead section extends from Y = 50 mm to current deposition front
            max_deposited_y = coordy[active_bead_nodes].max()
            
            bead_box = [
                # Bead top
                [[-12.5, 50.0, 23.0], [12.5, 50.0, 23.0], [12.5, max_deposited_y, 23.0], [-12.5, max_deposited_y, 23.0]],
                # Bead sides
                [[-12.5, 50.0, 20.0], [-12.5, max_deposited_y, 20.0], [-12.5, max_deposited_y, 23.0], [-12.5, 50.0, 23.0]],
                [[12.5, 50.0, 20.0], [12.5, max_deposited_y, 20.0], [12.5, max_deposited_y, 23.0], [12.5, 50.0, 23.0]],
                [[-12.5, 50.0, 20.0], [12.5, 50.0, 20.0], [12.5, 50.0, 23.0], [-12.5, 50.0, 23.0]],
                [[-12.5, max_deposited_y, 20.0], [12.5, max_deposited_y, 20.0], [12.5, max_deposited_y, 23.0], [-12.5, max_deposited_y, 23.0]],
            ]
            
            # Mean temperature of the active bead
            t_bead_mean = vals_T[t_idx, active_bead_nodes].mean()
            bead_color = colormap(norm(t_bead_mean))
            
            poly_bead = Poly3DCollection(bead_box, facecolors=bead_color, edgecolors='#F59E0B',
                                         linewidths=1.0, alpha=0.9, zorder=8)
            ax.add_collection3d(poly_bead)
            
            pct_dep = (max_deposited_y - 50.0) / 200.0 * 100
            ax.text2D(0.5, 0.08, f"Bead Length: {max_deposited_y - 50.0:.1f} mm ({pct_dep:.0f}%)\nMean T: {t_bead_mean:.1f} K",
                      transform=ax.transAxes, ha='center', fontsize=9, color='#F59E0B',
                      bbox=dict(boxstyle='round,pad=0.3', facecolor='#1E293B', edgecolor='#F59E0B', alpha=0.8))
        else:
            ax.text2D(0.5, 0.08, "Bead: Not Materialized (0%)\nWaiting for T >= T_plast",
                      transform=ax.transAxes, ha='center', fontsize=9, color='#94A3B8',
                      bbox=dict(boxstyle='round,pad=0.3', facecolor='#1E293B', edgecolor='#475569', alpha=0.8))
            
        # Tool position label
        gap_contact = "IN CONTACT (Z=20mm)" if uz_curr < -4.0 else f"HOVERING (+{5.0 + uz_curr:.1f}mm)"
        ax.text2D(0.5, 0.92, f"Tool Y: {50.0 + uy_curr:.1f} mm\nState: {gap_contact}",
                  transform=ax.transAxes, ha='center', fontsize=9, color='#38BDF8',
                  bbox=dict(boxstyle='round,pad=0.3', facecolor='#0F172A', edgecolor='#38BDF8', alpha=0.8))

        ax.set_xlim(-60, 60)
        ax.set_ylim(-10, 310)
        ax.set_zlim(0, 85)
        
        ax.set_xlabel('X [mm]', fontsize=8, color='#94A3B8', labelpad=-4)
        ax.set_ylabel('Y [mm]', fontsize=8, color='#94A3B8', labelpad=-4)
        ax.set_zlabel('Z [mm]', fontsize=8, color='#94A3B8', labelpad=-4)
        
        ax.tick_params(colors='#94A3B8', labelsize=7, pad=-2)
        ax.grid(True, linestyle='--', color='#334155', alpha=0.4)
        
        ax.view_init(elev=26, azim=-55)
        ax.set_title(title, fontsize=10, fontweight='bold', color='#38BDF8', pad=6)
        
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    output_png = 'afsd_3d_stages.png'
    plt.savefig(output_png, dpi=200, facecolor='#0D1117')
    print(f"[3D Visualizer] Successfully generated 3D stages visualization: {output_png}")

if __name__ == '__main__':
    render_3d_deposition_stages()
