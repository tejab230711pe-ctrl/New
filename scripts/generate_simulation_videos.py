#!/usr/bin/env python3
"""
AFSD Simulation Video Suite Generator
=====================================
Builds three publication-quality simulation videos for the Additive Friction
Stir Deposition (AFSD) process, using `process_schematic.py` as the visual and
geometric reference:

1. Isometric Full-Domain Simulation Video:
   - File: `afsd_simulation_isometric.mp4` & `afsd_simulation_isometric.gif`
   - Complete 3D view of the 120 x 300 x 20 mm plate, dimension annotations,
     rotating consumable tool rod, dynamic curled flash collar, progressive
     rippled deposit bead, and telemetry HUD.

2. Close-up Tool-Workpiece Dynamics Video:
   - File: `afsd_simulation_closeup.mp4` & `afsd_simulation_closeup.gif`
   - Macro follow-camera tracking tool plunge, viscoplastic collar curl,
     shear ripple formation, and tool retraction.

3. Scientific Multi-Viewport Video:
   - File: `afsd_simulation_multiview.mp4` & `afsd_simulation_multiview.gif`
   - 3-panel synchronized engineering dashboard (3D Physics, Thermal Field,
     Live Time-Series Graphs: Temperature, Axial Force, Motor Power).
"""

import os
import sys
import shutil
import time
import numpy as np
import pandas as pd
import multiprocessing as mp
import subprocess
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(WORKSPACE_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
CSV_PATH = os.path.join(WORKSPACE_DIR, "afsd_deposition_out.csv")

# Import the high-performance renderer components
from simulation_renderer import (
    BatchRenderer, draw_contact_shadow, draw_solid_plate,
    draw_refined_annulus_collar_layer, draw_solid_rod,
    draw_refined_fs_layer, draw_plate_dimensions,
    compute_material_deformation_ability
)

# ═══════════════════════════════════════════════════════════════════════════ #
#                     SIMULATION STATE INTERPOLATION                          #
# ═══════════════════════════════════════════════════════════════════════════ #

def load_simulation_data():
    """Loads and prepares interpolation functions from afsd_deposition_out.csv."""
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Simulation data CSV not found: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    t_data = df['time'].values
    t_max = df['T_max'].values
    rpm_data = df['current_rpm'].values
    force_data = df['force_kN'].values
    power_data = df['power_kW'].values
    dep_data = df['deposited_bead_pct'].values
    torque_data = df['spindle_torque_Nm'].values if 'spindle_torque_Nm' in df.columns else np.zeros_like(t_data)
    fy_data = df['traverse_force_N'].values if 'traverse_force_N' in df.columns else np.zeros_like(t_data)
    fx_data = df['transverse_force_N'].values if 'transverse_force_N' in df.columns else np.zeros_like(t_data)
    flow_stress_data = df['flow_stress_Pa'].values if 'flow_stress_Pa' in df.columns else np.full_like(t_data, 255.21e6)
    lnZ_data = df['ln_Zener_Hollomon'].values if 'ln_Zener_Hollomon' in df.columns else np.full_like(t_data, 60.0)
    return t_data, t_max, rpm_data, force_data, power_data, dep_data, torque_data, fy_data, fx_data, flow_stress_data, lnZ_data


def compute_frame_states(num_frames=160):
    """Computes exact physical states for all video frames."""
    (t_data, t_max_arr, rpm_arr, force_arr, power_arr, dep_arr,
     torque_arr, fy_arr, fx_arr, flow_stress_arr, lnZ_arr) = load_simulation_data()
    t_eval = np.linspace(0.0, 68.0, num_frames)
    
    t_max_interp = np.interp(t_eval, t_data, t_max_arr)
    rpm_interp   = np.interp(t_eval, t_data, rpm_arr)
    force_interp = np.interp(t_eval, t_data, force_arr)
    power_interp = np.interp(t_eval, t_data, power_arr)
    dep_interp   = np.interp(t_eval, t_data, dep_arr)
    torque_interp = np.interp(t_eval, t_data, torque_arr)
    fy_interp     = np.interp(t_eval, t_data, fy_arr)
    fx_interp     = np.interp(t_eval, t_data, fx_arr)
    flow_stress_interp = np.interp(t_eval, t_data, flow_stress_arr)
    lnZ_interp    = np.interp(t_eval, t_data, lnZ_arr)

    states = []
    plate_w, plate_l, plate_t = 120.0, 300.0, 20.0
    rod_r, rod_h = 12.5, 50.0

    cumulative_mushroom = 0.0
    for i, t in enumerate(t_eval):
        # Determine Process Stage & Kinematics
        if t <= 1.6:
            stage_name = "Approach (Plunging & Spin-Up)"
            stage_badge = "1. APPROACH (PLUNGING)"
            stage_color = "#2563EB" # Blue
            frac = t / 1.6
            tool_z = 25.0 - 5.0 * frac
            tool_y = 50.0
            collar_scale = 0.0
            dep_len = 0.0
            is_contact = (tool_z <= 20.1)
        elif t <= 5.6:
            stage_name = "Dwell & Frictional Stir Pre-Heating"
            stage_badge = "2. DWELL & FRICTIONAL STIR"
            stage_color = "#D97706" # Amber
            tool_z = 20.0
            tool_y = 50.0
            frac = (t - 1.6) / 4.0
            collar_scale = frac ** 1.2
            dep_len = 0.0
            is_contact = True
        elif t <= 45.6:
            stage_name = "Traverse & Progressive Layer Deposition"
            stage_badge = "3. TRAVERSE & LAYER DEPOSITION"
            stage_color = "#059669" # Emerald green
            tool_z = 20.0
            tool_y = 50.0 + (t - 5.6) * 5.0
            collar_scale = 1.0
            # Material does NOT deposit immediately: governed by physical simulation gate (T in 350-525 C & pressure)
            dep_len = float(dep_interp[i]) * 200.0
            is_contact = True
        else:
            stage_name = "Tool Retraction & Solidification Cooling"
            stage_badge = "4. RETRACTION & COOLING"
            stage_color = "#7C3AED" # Purple
            tool_y = 250.0
            frac = min(1.0, (t - 45.6) / 2.4)
            tool_z = 20.0 + 5.0 * frac
            collar_scale = 1.0
            dep_len = float(dep_interp[i]) * 200.0
            is_contact = False

        rot_angle = np.radians((t * 1200.0 * 360.0 / 60.0) % 360.0)

        rpm_val = max(0.0, float(rpm_interp[i]))
        force_val = max(0.0, float(force_interp[i]))
        power_val = max(0.0, float(power_interp[i]))
        temp_val = max(293.15, float(t_max_interp[i]))

        # Rotational drag resistance (frictional torque)
        omega = (2.0 * np.pi * rpm_val / 60.0) if rpm_val > 10.0 else 1.0
        torque_nm = (power_val * 1000.0 / omega) if (rpm_val > 10.0 and is_contact) else 0.0

        # Physical Deformation Ability Criterion (T >= 450 K onset, full at 540 K):
        def_ability = compute_material_deformation_ability(temp_val)

        f_drive = min(1.0, force_val / 5.0)
        t_drive = min(1.0, torque_nm / 45.0)
        flow_drive = f_drive * (0.35 + 0.65 * t_drive) if is_contact else 0.0

        instant_mushroom = def_ability * flow_drive
        cumulative_mushroom = max(cumulative_mushroom, instant_mushroom)

        # Status text for HUD telemetry
        if t <= 1.6:
            mat_state = "ELASTIC (Rigid Tool)"
            torque_state = "FREE SPIN (No Drag)"
        elif def_ability < 0.05:
            mat_state = "RIGID (T < 450 K, Below Def. Threshold)"
            torque_state = f"{torque_nm:4.1f} N·m [ROTATION RESISTED]"
        elif def_ability < 0.85:
            mat_state = f"DEF. ONSET ({def_ability*100:2.0f}% Softened - Outward Flow)"
            torque_state = f"{torque_nm:4.1f} N·m [HIGH TORSIONAL SHEAR]"
        elif is_contact:
            mat_state = f"VISCOPLASTIC FLOW ({cumulative_mushroom*100:2.0f}% Mushroom)"
            torque_state = f"{torque_nm:4.1f} N·m [STICKING TORSION]"
        else:
            mat_state = f"PERMANENT MUSHROOM TIP ({cumulative_mushroom*100:2.0f}% Retained)"
            torque_state = "UNLOADED (Spindle Retracted)"

        # Consumable Rod Shortening Dynamics (Continuous Axial Consumption into Bead Layer)
        # Initial rod length = 50.0 mm
        # Dwell: initial plastic burn-off creates mushroom base (-3.0 mm)
        # Traverse: continuous mass-conserving consumption (-32.0 mm across 200 mm bead)
        # Retraction: leaves remaining 15.0 mm shortened stub
        if t <= 1.6:
            current_rod_h = 50.0
            feed_rate = 0.0
        elif t <= 5.6:
            current_rod_h = 50.0 - 3.0 * ((t - 1.6) / 4.0)
            feed_rate = 45.0
        elif t <= 45.6:
            current_rod_h = 47.0 - 32.0 * ((t - 5.6) / 40.0)
            feed_rate = 48.0
        else:
            current_rod_h = 15.0
            feed_rate = 0.0
        
        consumed_len = 50.0 - current_rod_h

        # Solid-State Layer Formation Criterion: 0.6 to 0.9 T_solidus (350 °C to 525 °C / 623 K to 798 K)
        # Material will NOT deposit immediately! Requires T in [350, 525] °C AND forging contact pressure!
        t_sol_low = 623.15   # 350 °C (0.6 T_solidus)
        t_sol_high = 798.15  # 525 °C (0.9 T_solidus)
        is_layer_forming = (is_contact and (temp_val >= t_sol_low) and (temp_val <= t_sol_high) and (force_val >= 1.5))

        if t <= 1.6:
            layer_state = "STANDBY (Tool Approaching)"
        elif not is_contact:
            layer_state = "SOLIDIFIED & COOLED (Layer Consolidated)"
        elif temp_val < t_sol_low:
            layer_state = f"PRE-HEATING (T = {temp_val-273.15:3.0f} °C < 350 °C - NO DEPOSITION)"
        elif temp_val <= t_sol_high:
            layer_state = f"ACTIVE CONSOLIDATION ({temp_val-273.15:3.0f} °C in 350-525 °C Gate)"
        else:
            layer_state = f"INHIBITED (T = {temp_val-273.15:3.0f} °C > 525 °C - Exceeds Gate)"

        states.append({
            'idx': i,
            'time': t,
            'stage_name': stage_name,
            'stage_badge': stage_badge,
            'stage_color': stage_color,
            'tool_y': tool_y,
            'tool_z': tool_z,
            'collar_scale': collar_scale,
            'dep_len': dep_len,
            'dep_pct': float(dep_interp[i]) * 100.0,
            'rot_angle': rot_angle,
            'rpm': rpm_val,
            'force_kn': force_val,
            'power_kw': power_val,
            'torque_nm': torque_nm,
            't_max': temp_val,
            'def_ability': def_ability,
            'mushroom_scale': cumulative_mushroom,
            'mat_state': mat_state,
            'torque_state': torque_state,
            'is_contact': is_contact,
            'plate_w': plate_w,
            'plate_l': plate_l,
            'plate_t': plate_t,
            'rod_r': rod_r,
            'rod_h': current_rod_h,
            'consumed_len': consumed_len,
            'is_layer_forming': is_layer_forming,
            'layer_state': layer_state,
            'fy_kn': float(fy_interp[i]) / 1000.0,
            'fx_kn': float(fx_interp[i]) / 1000.0,
            'flow_stress_mpa': float(flow_stress_interp[i]) / 1e6,
            'lnZ': float(lnZ_interp[i])
        })

    return states, (t_data, t_max_arr, force_arr, power_arr, torque_arr, fy_arr)


# ═══════════════════════════════════════════════════════════════════════════ #
#                     VIDEO 1: ISOMETRIC FULL DOMAIN                          #
# ═══════════════════════════════════════════════════════════════════════════ #

def render_isometric_frame(args):
    """Renders a single frame for the Full Isometric Simulation Video."""
    state, out_file = args
    fig = plt.figure(figsize=(16, 9), dpi=100)
    fig.patch.set_facecolor('white')
    ax = fig.add_axes([-0.05, -0.05, 1.1, 1.1], projection='3d', computed_zorder=False)
    ax.set_facecolor('white')
    ax.view_init(elev=27, azim=-50)
    ax.set_box_aspect([1.2, 2.7, 0.9])

    px0 = -state['plate_w'] / 2.0
    py0 = 0.0

    renderer = BatchRenderer()

    # 1. Soft Ground Contact Shadow
    draw_contact_shadow(renderer, px0, py0, state['plate_w'], state['plate_l'], z_plane=-2.0)

    # 2. Solid Base Plate with FE Mesh & Thermal Glow
    draw_solid_plate(renderer, ax, px0, py0, 0, state['plate_w'], state['plate_l'], state['plate_t'],
                     nx=36, ny=54, nz=5, rcx=0, rcy=state['tool_y'], rod_r=state['rod_r'],
                     heat_temp=state['t_max'], is_contact=state['is_contact'])

    # 3. Progressive Deposited Bead with 3D Shear Ripples
    draw_refined_fs_layer(renderer, 0.0, state['tool_y'], state['rod_r'], state['plate_t'],
                          y_start=50.0, dep_length=state['dep_len'], ny=60, nx=40,
                          peak_temp=state['t_max'])

    # 4. Curled Flash Annulus Collar (Back Half)
    collar_z = state['plate_t'] if state['is_contact'] else state['tool_z']
    draw_refined_annulus_collar_layer(renderer, 0.0, state['tool_y'], collar_z, state['rod_r'],
                                      collar_scale=state['collar_scale'], pass_type='back',
                                      nth=76, ns=26)

    # 5. Rotating Consumable Tool Rod with Viscoplastic Mushrooming & Rotational Resistance
    draw_solid_rod(renderer, 0.0, state['tool_y'], state['tool_z'], state['tool_z'] + state['rod_h'],
                   state['rod_r'], rot_angle=state['rot_angle'], nth=72, nz=28,
                   mushroom_scale=state['mushroom_scale'])

    # 6. Curled Flash Annulus Collar (Front Half)
    draw_refined_annulus_collar_layer(renderer, 0.0, state['tool_y'], collar_z, state['rod_r'],
                                      collar_scale=state['collar_scale'], pass_type='front',
                                      nth=76, ns=26)

    # Commit batched 3D polygons
    renderer.commit(ax)

    # 7. Precision Dimensions
    draw_plate_dimensions(ax, px0, py0, 0, state['plate_w'], state['plate_l'], state['plate_t'])

    ax.set_xlim(-90, 90)
    ax.set_ylim(-30, 330)
    ax.set_zlim(-6, 95)

    for a in [ax.xaxis, ax.yaxis, ax.zaxis]:
        a.set_ticks([])
        a.pane.fill = False
        a.pane.set_edgecolor('white')
        a.line.set_color('white')
    ax.grid(False)

    # Telemetry HUD Card
    hud_bg = dict(boxstyle='round,pad=0.55', facecolor='#0B132B', edgecolor='#1C2D4A', linewidth=1.4, alpha=0.92)
    contact_str = "IN CONTACT" if state['is_contact'] else "RETRACTED"
    text_content = (
        'AFSD MULTI-BLOCK 3D PROCESS SIMULATION\n'
        f"Stage:     {state['stage_name'].upper()}\n"
        f"Time:      t = {state['time']:5.1f} s / 68.0 s\n"
        f"Rod Feed:  L = {state['rod_h']:4.1f} mm (-{state['consumed_len']:4.1f} mm consumed)\n"
        f"Forces:    Fz={state['force_kn']:4.2f} kN | Fy={state['fy_kn']:4.2f} kN | Fx={state['fx_kn']:4.2f} kN\n"
        f"Torque:    Mz = {state['torque_nm']:4.1f} N·m ({state['power_kw']:4.1f} kW @ {state['rpm']:4.0f} RPM)\n"
        f"Flow:      sigma_y = {state['flow_stress_mpa']:4.1f} MPa | ln(Z) = {state['lnZ']:4.1f}\n"
        f"Bond Gate: 0.6-0.9 T_sol (350-525 °C) [{ 'ACTIVE' if state['is_layer_forming'] else 'OFF' }]\n"
        f"T_max:     {state['t_max']:5.1f} K ({state['t_max'] - 273.15:5.1f} °C)\n"
        f"Tool:      Y = {state['tool_y']:5.1f} mm  |  Z = {state['tool_z']:4.1f} mm [{contact_str}]\n"
        f"Deposit:   {state['dep_len']:5.1f} mm / 200.0 mm ({state['dep_pct']:4.1f}%)"
    )
    fig.text(0.04, 0.94, text_content, color='#E2E8F0', fontsize=10.5,
             family='monospace', fontweight='bold', va='top', bbox=hud_bg)

    # Stage Badge Banner
    fig.text(0.50, 0.95, f"  {state['stage_badge']}  ", color='white', fontsize=13,
             fontweight='bold', ha='center', va='top',
             bbox=dict(boxstyle='round,pad=0.4', facecolor=state['stage_color'], edgecolor='none', alpha=0.95))

    fig.savefig(out_file, dpi=100, facecolor='white')
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════════════════ #
#                     VIDEO 2: CLOSE-UP MACRO VIEW                            #
# ═══════════════════════════════════════════════════════════════════════════ #

def render_closeup_frame(args):
    """Renders a single frame for the Close-Up Macro Follow-Camera Video."""
    state, out_file = args
    fig = plt.figure(figsize=(16, 9), dpi=100)
    fig.patch.set_facecolor('white')
    ax = fig.add_axes([-0.05, -0.05, 1.1, 1.1], projection='3d', computed_zorder=False)
    ax.set_facecolor('white')
    ax.view_init(elev=24, azim=-48)
    ax.set_box_aspect([1.1, 1.3, 0.9])

    px0 = -state['plate_w'] / 2.0
    py0 = 0.0

    renderer = BatchRenderer()

    # Plate & thermal glow
    draw_solid_plate(renderer, ax, px0, py0, 0, state['plate_w'], state['plate_l'], state['plate_t'],
                     nx=36, ny=54, nz=5, rcx=0, rcy=state['tool_y'], rod_r=state['rod_r'],
                     heat_temp=state['t_max'], is_contact=state['is_contact'])

    # Deposited bead
    draw_refined_fs_layer(renderer, 0.0, state['tool_y'], state['rod_r'], state['plate_t'],
                          y_start=50.0, dep_length=state['dep_len'], ny=60, nx=40,
                          peak_temp=state['t_max'])

    # Annulus Collar (Back Half)
    collar_z = state['plate_t'] if state['is_contact'] else state['tool_z']
    draw_refined_annulus_collar_layer(renderer, 0.0, state['tool_y'], collar_z, state['rod_r'],
                                      collar_scale=state['collar_scale'], pass_type='back',
                                      nth=80, ns=26)

    # Rotating Tool Rod with Viscoplastic Mushrooming & Rotational Resistance
    draw_solid_rod(renderer, 0.0, state['tool_y'], state['tool_z'], state['tool_z'] + state['rod_h'],
                   state['rod_r'], rot_angle=state['rot_angle'], nth=72, nz=28,
                   mushroom_scale=state['mushroom_scale'])

    # Annulus Collar (Front Half)
    draw_refined_annulus_collar_layer(renderer, 0.0, state['tool_y'], collar_z, state['rod_r'],
                                      collar_scale=state['collar_scale'], pass_type='front',
                                      nth=80, ns=26)

    renderer.commit(ax)

    # Follow-Camera Limits centered on tool
    ax.set_xlim(-40, 40)
    ax.set_ylim(state['tool_y'] - 45, state['tool_y'] + 40)
    ax.set_zlim(14, 65)

    for a in [ax.xaxis, ax.yaxis, ax.zaxis]:
        a.set_ticks([])
        a.pane.fill = False
        a.pane.set_edgecolor('white')
        a.line.set_color('white')
    ax.grid(False)

    # Macro Telemetry
    hud_bg = dict(boxstyle='round,pad=0.5', facecolor='#0B132B', edgecolor='#1C2D4A', linewidth=1.4, alpha=0.92)
    mushroom_pct = state['mushroom_scale'] * 26.0
    text_content = (
        'TOOL-WORKPIECE INTERACTION (MACRO DYNAMICS)\n'
        f"Time:       t = {state['time']:4.1f} s  |  Stage: {state['stage_name'].split()[0].upper()}\n"
        f"Rod Feed:   L = {state['rod_h']:4.1f} mm  |  Consumed: -{state['consumed_len']:4.1f} mm\n"
        f"Forces:     Fz = {state['force_kn']:4.2f} kN  |  Fy = {state['fy_kn']:4.2f} kN  |  Fx = {state['fx_kn']:4.2f} kN\n"
        f"Torque Mz:  {state['torque_nm']:4.1f} N·m  |  Power: {state['power_kw']:4.2f} kW\n"
        f"Flow:       sigma_y = {state['flow_stress_mpa']:4.1f} MPa  |  ln(Z) = {state['lnZ']:4.1f}\n"
        f"Layer Gate: {state['layer_state']}\n"
        f"Interface:  {state['t_max']:5.1f} K ({state['t_max'] - 273.15:5.1f} °C) | 0.6-0.9 T_sol\n"
        f"Flash:      {state['collar_scale']*100:4.0f}% Viscoplastic Collar"
    )
    fig.text(0.04, 0.94, text_content, color='#E2E8F0', fontsize=10.5,
             family='monospace', fontweight='bold', va='top', bbox=hud_bg)

    fig.text(0.50, 0.95, '  TOOL & FLASH COLLAR DYNAMICS (MACRO VIEW)  ', color='white', fontsize=13,
             fontweight='bold', ha='center', va='top',
             bbox=dict(boxstyle='round,pad=0.4', facecolor='#2563EB', edgecolor='none', alpha=0.95))

    fig.savefig(out_file, dpi=100, facecolor='white')
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════════════════ #
#                     VIDEO 3: SCIENTIFIC MULTI-VIEWPORT                      #
# ═══════════════════════════════════════════════════════════════════════════ #

def render_multiview_frame(args):
    """Renders a single frame for the 3-Panel Scientific Telemetry & Thermal Video."""
    state, curves, out_file = args
    t_data, t_max_arr, force_arr, power_arr, torque_arr, fy_arr = curves
    curr_t = state['time']

    fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
    fig.patch.set_facecolor('#0B0F19') # Sleek dark scientific dashboard

    # ── PANEL 1: Left 3D Isometric Physics View ──────────────────────────── #
    ax_3d = fig.add_axes([0.01, 0.04, 0.57, 0.91], projection='3d', computed_zorder=False)
    ax_3d.set_facecolor('#0B0F19')
    ax_3d.view_init(elev=27, azim=-50)
    ax_3d.set_box_aspect([1.2, 2.7, 0.9])

    px0 = -state['plate_w'] / 2.0
    py0 = 0.0

    renderer = BatchRenderer()
    draw_contact_shadow(renderer, px0, py0, state['plate_w'], state['plate_l'], z_plane=-2.0, is_dark_bg=True)
    draw_solid_plate(renderer, ax_3d, px0, py0, 0, state['plate_w'], state['plate_l'], state['plate_t'],
                     nx=36, ny=54, nz=5, rcx=0, rcy=state['tool_y'], rod_r=state['rod_r'],
                     heat_temp=state['t_max'], is_contact=state['is_contact'])
    draw_refined_fs_layer(renderer, 0.0, state['tool_y'], state['rod_r'], state['plate_t'],
                          y_start=50.0, dep_length=state['dep_len'], ny=60, nx=40,
                          peak_temp=state['t_max'])

    collar_z = state['plate_t'] if state['is_contact'] else state['tool_z']
    draw_refined_annulus_collar_layer(renderer, 0.0, state['tool_y'], collar_z, state['rod_r'],
                                      collar_scale=state['collar_scale'], pass_type='back',
                                      nth=72, ns=22)
    draw_solid_rod(renderer, 0.0, state['tool_y'], state['tool_z'], state['tool_z'] + state['rod_h'],
                   state['rod_r'], rot_angle=state['rot_angle'], nth=64, nz=24,
                   mushroom_scale=state['mushroom_scale'])
    draw_refined_annulus_collar_layer(renderer, 0.0, state['tool_y'], collar_z, state['rod_r'],
                                      collar_scale=state['collar_scale'], pass_type='front',
                                      nth=72, ns=22)
    renderer.commit(ax_3d)

    ax_3d.set_xlim(-90, 90)
    ax_3d.set_ylim(-30, 330)
    ax_3d.set_zlim(-6, 95)
    for a in [ax_3d.xaxis, ax_3d.yaxis, ax_3d.zaxis]:
        a.set_ticks([])
        a.pane.fill = False
        a.pane.set_edgecolor('#0B0F19')
        a.line.set_color('#0B0F19')
    ax_3d.grid(False)

    # 3D View Title
    ax_3d.text2D(0.5, 0.98, "3D Finite Element Kinematics & Layer Deposition",
                 transform=ax_3d.transAxes, ha='center', va='top', color='#38BDF8',
                 fontsize=13, fontweight='bold',
                 bbox=dict(boxstyle='round,pad=0.3', facecolor='#1E293B', edgecolor='#38BDF8', alpha=0.9))

    # ── PANEL 2: Top-Right Substrate Surface Temperature Field ──────────── #
    ax_therm = fig.add_axes([0.60, 0.56, 0.37, 0.36])
    ax_therm.set_facecolor('#0F172A')

    # Construct 2D temperature contour on plate top surface
    grid_x = np.linspace(-60, 60, 60)
    grid_y = np.linspace(0, 300, 120)
    GX, GY = np.meshgrid(grid_x, grid_y)

    # Ambient base temp
    GT = np.ones_like(GX) * 293.15

    # Hot stir zone at active tool location
    d_tool = np.sqrt(GX**2 + (GY - state['tool_y'])**2)
    t_rise = max(0.0, state['t_max'] - 293.15)
    GT += t_rise * np.exp(-0.5 * (d_tool / 14.0)**2)

    # Deposited bead thermal footprint
    if state['dep_len'] > 0:
        in_bead = (abs(GX) <= 12.5) & (GY >= 50.0) & (GY <= state['tool_y'])
        age = (state['tool_y'] - GY) / 5.0 # seconds since deposition
        bead_temp = 293.15 + t_rise * np.exp(-age / 18.0)
        GT = np.maximum(GT, np.where(in_bead, bead_temp, 293.15))

    cplot = ax_therm.contourf(GY, GX, GT, levels=np.linspace(293.15, 750.0, 35),
                              cmap='plasma', extend='both')
    ax_therm.set_title("Substrate & Bead Thermal Field T(x, y) [K]", color='#F59E0B',
                       fontsize=12, fontweight='bold', pad=8)
    ax_therm.set_xlabel("Y Position [mm]", color='#94A3B8', fontsize=9)
    ax_therm.set_ylabel("X Position [mm]", color='#94A3B8', fontsize=9)
    ax_therm.tick_params(colors='#94A3B8', labelsize=8)
    for spine in ax_therm.spines.values():
        spine.set_color('#334155')

    # Tool location marker
    ax_therm.plot([state['tool_y']], [0], marker='o', markersize=9, color='#38BDF8',
                  markeredgecolor='white', markeredgewidth=1.5)
    ax_therm.axvline(state['tool_y'], color='#38BDF8', linestyle='--', alpha=0.6, lw=1.0)

    # Colorbar
    cbar = fig.colorbar(cplot, ax=ax_therm, fraction=0.046, pad=0.03)
    cbar.ax.tick_params(colors='#94A3B8', labelsize=8)
    cbar.set_label('Temperature [K]', color='#94A3B8', fontsize=9)

    # ── PANEL 3: Bottom-Right Live Process Telemetry Curves ──────────────── #
    ax_plot = fig.add_axes([0.60, 0.09, 0.37, 0.38])
    ax_plot.set_facecolor('#0F172A')

    # Plot full background curves
    ax_plot.plot(t_data, t_max_arr, color='#EF4444', lw=1.5, alpha=0.35, label='_nolegend_')
    ax_plot.plot(t_data, force_arr * 100.0, color='#10B981', lw=1.5, alpha=0.35, label='_nolegend_')
    ax_plot.plot(t_data, power_arr * 80.0, color='#38BDF8', lw=1.5, alpha=0.35, label='_nolegend_')
    ax_plot.plot(t_data, torque_arr * 10.0, color='#C084FC', lw=1.5, alpha=0.35, label='_nolegend_')

    # Plot active history up to current time
    mask = (t_data <= curr_t)
    if np.any(mask):
        ax_plot.plot(t_data[mask], t_max_arr[mask], color='#EF4444', lw=2.4, label='Peak Temp T_max [K]')
        ax_plot.plot(t_data[mask], force_arr[mask] * 100.0, color='#10B981', lw=2.2, label='Normal Load F_z [x100 N]')
        ax_plot.plot(t_data[mask], power_arr[mask] * 80.0, color='#38BDF8', lw=2.0, label='Spindle Power [x80 W]')
        ax_plot.plot(t_data[mask], torque_arr[mask] * 10.0, color='#C084FC', lw=2.0, label='Spindle Torque M_z [x10 N·m]')

    # Moving Time Scrubber line
    ax_plot.axvline(curr_t, color='#F8FAFC', lw=1.8, linestyle='-', alpha=0.9)
    ax_plot.plot([curr_t], [state['t_max']], 'o', color='#EF4444', markersize=6)

    # Reference lines and 0.6 - 0.9 T_solidus Layer Formation Band (350 - 525 °C / 623.15 - 798.15 K)
    ax_plot.axhline(864.15, color='#F87171', linestyle=':', alpha=0.5, label='Solidus (864 K / 591 °C)')
    ax_plot.axhspan(623.15, 798.15, color='#F59E0B', alpha=0.12, label='0.6-0.9 T_sol Band (350-525 °C)')
    ax_plot.axhline(798.15, color='#FBBF24', linestyle='--', alpha=0.6, label='0.9 T_sol Gate (525 °C / 798 K)')
    ax_plot.axhline(623.15, color='#F59E0B', linestyle='--', alpha=0.7, label='0.6 T_sol Gate (350 °C / 623 K)')
    ax_plot.axhline(450.00, color='#38BDF8', linestyle=':', alpha=0.6, label='Def. Ability Onset (177 °C / 450 K)')

    ax_plot.set_xlim(0, 68)
    ax_plot.set_ylim(200, 920)
    ax_plot.set_xlabel("Simulation Time [s]", color='#94A3B8', fontsize=9)
    ax_plot.set_ylabel("Process Response", color='#94A3B8', fontsize=9)
    ax_plot.set_title("Synchronized Process Telemetry History", color='#38BDF8',
                      fontsize=12, fontweight='bold', pad=8)
    ax_plot.tick_params(colors='#94A3B8', labelsize=8)
    ax_plot.grid(True, linestyle='--', color='#1E293B', alpha=0.6)
    for spine in ax_plot.spines.values():
        spine.set_color('#334155')

    ax_plot.legend(loc='lower right', facecolor='#1E293B', edgecolor='#334155',
                   labelcolor='#E2E8F0', fontsize=8, framealpha=0.9)

    # Main Top Banner
    fig.text(0.30, 0.965, f"AFSD MULTI-BLOCK PROCESS SIMULATION  |  STAGE: {state['stage_badge']}",
             color='white', fontsize=14, fontweight='bold', ha='center', va='top',
             bbox=dict(boxstyle='round,pad=0.4', facecolor=state['stage_color'], edgecolor='none', alpha=0.95))

    fig.text(0.78, 0.965, f"t = {curr_t:4.1f} s | Rod: {state['rod_h']:4.1f} mm | Fz: {state['force_kn']:3.1f} kN | Fy: {state['fy_kn']:4.1f} kN",
             color='#E2E8F0', fontsize=9.5, family='monospace', fontweight='bold', ha='center', va='top',
             bbox=dict(boxstyle='round,pad=0.35', facecolor='#1E293B', edgecolor='#334155', alpha=0.9))

    fig.savefig(out_file, dpi=100, facecolor='#0B0F19')
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════════════════ #
#                     PARALLEL FRAME GENERATOR & ENCODER                      #
# ═══════════════════════════════════════════════════════════════════════════ #

def build_video_from_frames(frames_dir, output_mp4, output_gif, fps=16):
    """Encodes PNG frames into MP4 and high-quality animated GIF using ffmpeg."""
    print(f"\n[FFMPEG] Encoding MP4 -> {output_mp4} (FPS: {fps})...")
    cmd_mp4 = [
        "ffmpeg", "-y", "-framerate", str(fps),
        "-i", os.path.join(frames_dir, "frame_%04d.png"),
        "-c:v", "libx264", "-profile:v", "high", "-crf", "18",
        "-pix_fmt", "yuv420p", output_mp4
    ]
    subprocess.run(cmd_mp4, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"  [OK] Successfully created: {output_mp4} ({os.path.getsize(output_mp4) / 1024:.1f} KB)")

    print(f"[FFMPEG] Encoding GIF -> {output_gif}...")
    cmd_gif = [
        "ffmpeg", "-y", "-i", output_mp4,
        "-vf", "fps=10,scale=720:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse",
        output_gif
    ]
    subprocess.run(cmd_gif, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"  [OK] Successfully created: {output_gif} ({os.path.getsize(output_gif) / 1024:.1f} KB)")


def generate_all_simulation_videos(num_frames=160):
    t_start = time.time()
    num_cpus = mp.cpu_count()
    print("=" * 78)
    print("   AFSD MULTI-BLOCK SIMULATION VIDEO GENERATION SUITE")
    print(f"   CPUs Available: {num_cpus}  |  Target Frames: {num_frames} per video")
    print("=" * 78)

    states, curves = compute_frame_states(num_frames)

    # Temporary render directories
    tmp_iso = "/tmp/afsd_frames_iso"
    tmp_close = "/tmp/afsd_frames_closeup"
    tmp_multi = "/tmp/afsd_frames_multiview"

    for d in [tmp_iso, tmp_close, tmp_multi]:
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)

    # ── 1. RENDER ISOMETRIC VIDEO FRAMES ─────────────────────────────────── #
    print("\n[Phase 1/3] Rendering 3D Isometric Process Simulation Frames...")
    iso_tasks = [(s, os.path.join(tmp_iso, f"frame_{s['idx']:04d}.png")) for s in states]
    with mp.Pool(num_cpus) as pool:
        pool.map(render_isometric_frame, iso_tasks)
    print("  [OK] All Isometric frames rendered.")

    iso_mp4 = os.path.join(WORKSPACE_DIR, "afsd_simulation_isometric.mp4")
    iso_gif = os.path.join(WORKSPACE_DIR, "afsd_simulation_isometric.gif")
    build_video_from_frames(tmp_iso, iso_mp4, iso_gif, fps=16)

    # Also update the legacy path so existing references find the new high-fidelity video
    legacy_mp4 = os.path.join(WORKSPACE_DIR, "afsd_tool_motion_deposition.mp4")
    legacy_gif = os.path.join(WORKSPACE_DIR, "afsd_tool_motion_deposition.gif")
    shutil.copyfile(iso_mp4, legacy_mp4)
    shutil.copyfile(iso_gif, legacy_gif)

    # ── 2. RENDER CLOSE-UP VIDEO FRAMES ──────────────────────────────────── #
    print("\n[Phase 2/3] Rendering Tool Interaction & Flash Collar Dynamics Frames...")
    close_tasks = [(s, os.path.join(tmp_close, f"frame_{s['idx']:04d}.png")) for s in states]
    with mp.Pool(num_cpus) as pool:
        pool.map(render_closeup_frame, close_tasks)
    print("  [OK] All Close-Up frames rendered.")

    close_mp4 = os.path.join(WORKSPACE_DIR, "afsd_simulation_closeup.mp4")
    close_gif = os.path.join(WORKSPACE_DIR, "afsd_simulation_closeup.gif")
    build_video_from_frames(tmp_close, close_mp4, close_gif, fps=16)

    # ── 3. RENDER MULTI-VIEWPORT VIDEO FRAMES ────────────────────────────── #
    print("\n[Phase 3/3] Rendering Scientific Multi-Viewport Dashboard Frames...")
    multi_tasks = [(s, curves, os.path.join(tmp_multi, f"frame_{s['idx']:04d}.png")) for s in states]
    with mp.Pool(num_cpus) as pool:
        pool.map(render_multiview_frame, multi_tasks)
    print("  [OK] All Multi-Viewport frames rendered.")

    multi_mp4 = os.path.join(WORKSPACE_DIR, "afsd_simulation_multiview.mp4")
    multi_gif = os.path.join(WORKSPACE_DIR, "afsd_simulation_multiview.gif")
    build_video_from_frames(tmp_multi, multi_mp4, multi_gif, fps=16)

    # Cleanup temporary frame directories
    for d in [tmp_iso, tmp_close, tmp_multi]:
        if os.path.exists(d):
            shutil.rmtree(d)

    total_time = time.time() - t_start
    print("\n" + "=" * 78)
    print(f"  [SUCCESS] All 3 Simulation Video Suites generated in {total_time:.1f} s!")
    print(f"  1. Isometric 3D:    {iso_mp4}  |  {iso_gif}")
    print(f"  2. Close-up Macro:  {close_mp4}  |  {close_gif}")
    print(f"  3. Multi-Viewport:  {multi_mp4}  |  {multi_gif}")
    print("=" * 78)


if __name__ == '__main__':
    generate_all_simulation_videos(num_frames=160)
