#!/usr/bin/env python3
"""
AFSD Simulation Visualizer & Post-Processor
-------------------------------------------
Processes time-series CSV data from the RotatingDiskDepositionApp MOOSE
simulation of Additive Friction Stir Deposition for AA5083 Aluminum.

Generates:
  1. 4-panel process dashboard (temperature, power, force, pressure/strain)
  2. Individual high-resolution plots for each process variable
  3. Summary statistics text report

Usage:
  python3 visualize_results.py [workspace_dir]
  
  If workspace_dir is omitted, uses the current working directory.
"""

import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import pandas as pd

# ──────────────────────── Process Stage Definitions ────────────────────────
# These are the kinematic stages of the AFSD process
STAGES = {
    'Approach':       (0.0,  1.6,  '#4FC3F7'),
    'Dwell':          (1.6,  5.6,  '#FFB74D'),
    'Traverse':       (5.6,  45.6, '#81C784'),
    'Retract/Cool':   (45.6, 68.0, '#CE93D8'),
}

# ──────────────────────── Physical Constants (AA5083) ──────────────────────
T_SOLIDUS   = 864.15   # K (591 °C)
T_LIQUIDUS  = 911.15   # K (638 °C)
T_PLAST_LOW = 673.15   # K (400 °C) — onset of significant plasticization
T_PLAST_HI  = 803.15   # K (530 °C) — strong plasticization
T_AMBIENT   = 293.15   # K (20 °C)

MACHINE_POWER_LIMIT_kW = 22.0
MACHINE_FORCE_LIMIT_kN = 15.0
DEPOSITION_GATE_MPa    = 3.0


def add_stage_bands(ax, t_max):
    """Shade vertical bands indicating each process stage on a time axis."""
    for name, (t0, t1, color) in STAGES.items():
        if t0 > t_max:
            continue
        t1_eff = min(t1, t_max)
        ax.axvspan(t0, t1_eff, alpha=0.08, color=color, zorder=0)
        # Label near the top
        mid_t = (t0 + t1_eff) / 2.0
        ax.text(mid_t, ax.get_ylim()[1] * 0.97, name,
                ha='center', va='top', fontsize=7, fontstyle='italic',
                color=color, alpha=0.8, zorder=1)


def postprocess_simulation_data(workspace_dir):
    print(f"[AFSD Visualizer] Scanning workspace: {workspace_dir}")
    
    # ── Locate CSV files ──────────────────────────────────────────────────
    csv_candidates = [
        os.path.join(workspace_dir, "afsd_deposition_out.csv"),
        os.path.join(workspace_dir, "afsd_full_run_out.csv"),
        os.path.join(workspace_dir, "consumable_rod_history.csv"),
    ]
    
    csv_file = None
    for cand in csv_candidates:
        if os.path.exists(cand) and os.path.getsize(cand) > 100:
            csv_file = cand
            break
            
    if not csv_file:
        print("[AFSD Visualizer] ERROR: No simulation CSV found. Run the simulation first.")
        sys.exit(1)

    print(f"[AFSD Visualizer] Loading data from {csv_file}")
    df = pd.read_csv(csv_file)
    print(f"[AFSD Visualizer] Columns: {list(df.columns)}")
    print(f"[AFSD Visualizer] Rows: {len(df)}, Time range: {df['time'].min():.2f} – {df['time'].max():.2f} s")
    
    # Clean initial uninitialized values at t=0
    for col in ['T_max', 'T_avg_top']:
        if col in df.columns:
            df.loc[(df['time'] == 0) & (df[col] < 100), col] = T_AMBIENT
            
    t     = df['time'].values
    t_max = t.max()
    
    # ── Style Setup ───────────────────────────────────────────────────────
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.size': 11,
        'axes.grid': True,
        'grid.alpha': 0.3,
        'grid.linestyle': '--',
        'figure.facecolor': '#FAFAFA',
        'axes.facecolor': '#FFFFFF',
    })
    
    # ══════════════════════════════════════════════════════════════════════
    # DASHBOARD: 6-Panel Comprehensive Scientific Breakdown
    # ══════════════════════════════════════════════════════════════════════
    fig, axs = plt.subplots(3, 2, figsize=(18, 15))
    fig.suptitle(
        "Additive Friction Stir Deposition (AFSD) — Coupled Thermo-Mechanical Simulation\n"
        "Material: AA5083 Aluminum Alloy | Governing Equations: Energy, Momentum, JC Flow Stress, ALE & Process Forces",
        fontsize=15, fontweight='bold', y=0.985
    )
    
    # ── Panel 1: Temperature Evolution & 350-525 °C Gate ──────────────────
    ax = axs[0, 0]
    if 'T_max' in df.columns:
        ax.plot(t, df['T_max'].values, color='#D32F2F', linewidth=2.4, label='$T_{max}$ (Peak Interfacial)')
    if 'T_avg_top' in df.columns:
        ax.plot(t, df['T_avg_top'].values, color='#1976D2', linewidth=1.8, label='$T_{avg,top}$ (Substrate Surface)')
    
    ax.axhspan(623.15, 798.15, alpha=0.15, color='#F59E0B', label='0.6-0.9 $T_{sol}$ Gate (350–525 °C)')
    ax.axhline(T_SOLIDUS, color='#E53935', ls='--', alpha=0.7, lw=1.2, label=f'Solidus $T_s$ ({T_SOLIDUS:.0f} K / 591 °C)')
    ax.axhline(623.15, color='#D97706', ls=':', alpha=0.8, lw=1.2, label='Deposition Onset (350 °C / 623 K)')
    ax.set_ylim(bottom=270, top=950)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Temperature [K]")
    ax.set_title("1. Thermal Field & Viscoplastic Deposition Gate (350–525 °C)", fontweight='semibold')
    ax.legend(loc='lower right', fontsize=8, framealpha=0.9)
    add_stage_bands(ax, t_max)
    
    # ── Panel 2: Spindle Power & Torsional Torque ─────────────────────────
    ax = axs[0, 1]
    if 'power_kW' in df.columns:
        ax.plot(t, df['power_kW'].values, color='#7B1FA2', linewidth=2.2, label='Spindle Power $P$ [kW]')
        ax.axhline(MACHINE_POWER_LIMIT_kW, color='red', ls='--', alpha=0.5, label=f'Spindle Ceiling ({MACHINE_POWER_LIMIT_kW} kW)')
        ax.set_ylabel("Spindle Power [kW]", color='#7B1FA2')
        ax.tick_params(axis='y', labelcolor='#7B1FA2')
    
    if 'spindle_torque_Nm' in df.columns:
        ax2 = ax.twinx()
        ax2.plot(t, df['spindle_torque_Nm'].values, color='#C2185B', linewidth=2.0, ls='-', label='Torque $M_z$ [N·m]')
        ax2.set_ylabel("Spindle Torque $M_z$ [N·m]", color='#C2185B')
        ax2.tick_params(axis='y', labelcolor='#C2185B')
        ax2.legend(loc='center right', fontsize=8, framealpha=0.9)
    elif 'current_rpm' in df.columns:
        ax2 = ax.twinx()
        ax2.plot(t, df['current_rpm'].values, color='#00838F', linewidth=1.5, ls='-.', alpha=0.7, label='RPM')
        ax2.set_ylabel("Spindle Speed [RPM]", color='#00838F')
        ax2.tick_params(axis='y', labelcolor='#00838F')
        ax2.legend(loc='center right', fontsize=8, framealpha=0.9)
    
    ax.set_xlabel("Time [s]")
    ax.set_title("2. Spindle Mechanical Power & Torsional Torque ($M_z = P / \\omega$)", fontweight='semibold')
    ax.legend(loc='upper left', fontsize=8, framealpha=0.9)
    add_stage_bands(ax, t_max)
    
    # ── Panel 3: Normal Preload & Consumable Rod Shortening ───────────────
    ax = axs[1, 0]
    if 'force_kN' in df.columns:
        ax.plot(t, df['force_kN'].values, color='#0D47A1', linewidth=2.2, label='Normal Preload $F_z$ [kN]')
        ax.axhline(MACHINE_FORCE_LIMIT_kN, color='red', ls='--', alpha=0.5, label=f'Load Capacity ({MACHINE_FORCE_LIMIT_kN} kN)')
        ax.set_ylabel("Axial Force [kN]", color='#0D47A1')
        ax.tick_params(axis='y', labelcolor='#0D47A1')

    if 'rod_height_mm' in df.columns:
        ax_rod = ax.twinx()
        ax_rod.plot(t, df['rod_height_mm'].values, color='#059669', linewidth=2.2, ls='-', label='Rod Height $H_{rod}$')
        if 'consumed_length_mm' in df.columns:
            ax_rod.plot(t, df['consumed_length_mm'].values, color='#D97706', linewidth=1.8, ls=':', label=r'Consumed $\Delta H$')
        ax_rod.set_ylabel("Rod Dimension [mm]", color='#059669')
        ax_rod.tick_params(axis='y', labelcolor='#059669')
        ax_rod.set_ylim(-2, 58)
        ax_rod.legend(loc='center right', fontsize=8, framealpha=0.9)
    
    ax.set_xlabel("Time [s]")
    ax.set_title("3. Normal Servo Load & Consumable Rod Shortening ($50 \\to 15$ mm)", fontweight='semibold')
    ax.legend(loc='upper left', fontsize=8, framealpha=0.9)
    add_stage_bands(ax, t_max)
    
    # ── Panel 4: Process Forces (Traverse Fy & Transverse Fx) ──────────────
    ax = axs[1, 1]
    if 'traverse_force_N' in df.columns:
        ax.plot(t, df['traverse_force_N'].values / 1e3, color='#B91C1C', linewidth=2.2, label='Traverse Resistance $F_y$ [kN]')
    if 'transverse_force_N' in df.columns:
        ax.plot(t, df['transverse_force_N'].values / 1e3, color='#F97316', linewidth=1.8, ls='--', label='Transverse / Side Force $F_x$ [kN]')
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Translational Force [kN]")
    ax.set_title("4. Process Reaction Forces ($F_y$: Plowing/Traverse, $F_x$: AS/RS Asymmetry)", fontweight='semibold')
    ax.legend(loc='upper right', fontsize=8, framealpha=0.9)
    add_stage_bands(ax, t_max)
    
    # ── Panel 5: Viscoplastic Flow Stress & Zener-Hollomon ────────────────
    ax = axs[2, 0]
    if 'flow_stress_Pa' in df.columns:
        ax.plot(t, df['flow_stress_Pa'].values / 1e6, color='#4338CA', linewidth=2.2, label='Johnson-Cook Flow Stress $\\sigma_{flow}$ [MPa]')
        ax.set_ylabel("Flow Stress $\\sigma_{flow}$ [MPa]", color='#4338CA')
        ax.tick_params(axis='y', labelcolor='#4338CA')
    
    if 'ln_Zener_Hollomon' in df.columns:
        ax_z = ax.twinx()
        ax_z.plot(t, df['ln_Zener_Hollomon'].values, color='#0284C7', linewidth=1.8, ls='-.', label=r'Zener-Hollomon $\ln(Z)$')
        ax_z.set_ylabel(r"$\ln(Z) = \ln(\dot{\varepsilon}) + Q / (RT)$ [-]", color='#0284C7')
        ax_z.tick_params(axis='y', labelcolor='#0284C7')
        ax_z.legend(loc='center right', fontsize=8, framealpha=0.9)
    
    ax.set_xlabel("Time [s]")
    ax.set_title(r"5. Viscoplastic Flow Stress & Zener-Hollomon Parameter ($\ln Z$)", fontweight='semibold')
    ax.legend(loc='upper left', fontsize=8, framealpha=0.9)
    add_stage_bands(ax, t_max)
    
    # ── Panel 6: Contact Pressure & Plastic Strain ────────────────────────
    ax = axs[2, 1]
    if 'max_contact_pressure' in df.columns:
        ax.plot(t, df['max_contact_pressure'].values / 1e6, color='#1565C0', linewidth=2.0, label='Peak Contact Pressure $P_{max}$')
        ax.axhline(0.25, color='#F59E0B', ls=':', alpha=0.8, lw=1.2, label='Deposition Gate Threshold ($0.25$ MPa)')
        ax.set_ylabel("Contact Pressure [MPa]", color='#1565C0')
        ax.tick_params(axis='y', labelcolor='#1565C0')
    
    if 'max_plastic_strain' in df.columns:
        ax2 = ax.twinx()
        ax2.plot(t, df['max_plastic_strain'].values, color='#2E7D32', ls='--', linewidth=1.8, label='Max Plastic Strain $\\varepsilon_p$')
        ax2.set_ylabel("Equivalent Plastic Strain [-]", color='#2E7D32')
        ax2.tick_params(axis='y', labelcolor='#2E7D32')
        ax2.legend(loc='center right', fontsize=8, framealpha=0.9)
    
    ax.set_xlabel("Time [s]")
    ax.set_title("6. Interfacial Forging Pressure & Severe Plastic Strain", fontweight='semibold')
    ax.legend(loc='upper left', fontsize=8, framealpha=0.9)
    add_stage_bands(ax, t_max)
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    dashboard_path = os.path.join(workspace_dir, "afsd_simulation_dashboard.png")
    plt.savefig(dashboard_path, dpi=200, bbox_inches='tight')
    print(f"[AFSD Visualizer] Dashboard saved: {dashboard_path}")
    plt.close()
    
    # ══════════════════════════════════════════════════════════════════════
    # INDIVIDUAL HIGH-RES PLOTS
    # ══════════════════════════════════════════════════════════════════════
    
    # Temperature detail plot
    fig, ax = plt.subplots(figsize=(12, 6))
    if 'T_max' in df.columns:
        ax.plot(t, df['T_max'].values, color='#D32F2F', linewidth=2.5, label='$T_{max}$ (Peak)')
    if 'T_avg_top' in df.columns:
        ax.plot(t, df['T_avg_top'].values, color='#1976D2', linewidth=2.0, label='$T_{avg,top}$ (Surface Avg)')
    
    # Fill plasticization band
    ax.axhspan(T_PLAST_LOW, T_PLAST_HI, alpha=0.08, color='orange', label='Plasticization Band')
    ax.axhspan(T_SOLIDUS, T_LIQUIDUS, alpha=0.1, color='red', label='Mushy Zone (Solidus–Liquidus)')
    ax.axhline(T_AMBIENT, color='gray', ls=':', alpha=0.4, label='Ambient (293 K)')
    
    ax.set_xlabel("Time [s]", fontsize=13)
    ax.set_ylabel("Temperature [K]", fontsize=13)
    ax.set_title("AFSD Thermal History — AA5083 | RPM = 1200, F = 5 kN", fontsize=14, fontweight='bold')
    ax.legend(fontsize=10, framealpha=0.9, loc='best')
    ax.grid(True, alpha=0.3, ls='--')
    ax.set_ylim(bottom=270, top=950)
    add_stage_bands(ax, t_max)
    plt.tight_layout()
    
    temp_path = os.path.join(workspace_dir, "afsd_temperature_history.png")
    plt.savefig(temp_path, dpi=250, bbox_inches='tight')
    print(f"[AFSD Visualizer] Temperature plot saved: {temp_path}")
    plt.close()
    
    # ══════════════════════════════════════════════════════════════════════
    # TEXT SUMMARY REPORT
    # ══════════════════════════════════════════════════════════════════════
    report_lines = [
        "=" * 72,
        "  AFSD SIMULATION RESULTS SUMMARY",
        "  Material: AA5083 Aluminum Alloy",
        "  Framework: MOOSE (RotatingDiskDepositionApp)",
        "=" * 72,
        "",
        f"  Simulation Duration:  {t.min():.2f} – {t.max():.2f} s ({len(t)} timesteps)",
        f"  Timestep Size:        Δt ≈ {np.median(np.diff(t)):.4f} s",
        "",
    ]
    
    if 'T_max' in df.columns:
        T_max_val = df['T_max'].max()
        T_max_time = df.loc[df['T_max'].idxmax(), 'time']
        report_lines += [
            f"  Peak Temperature:     {T_max_val:.2f} K ({T_max_val - 273.15:.2f} °C) at t = {T_max_time:.2f} s",
            f"  Exceeded Solidus?     {'YES ⚠️' if T_max_val > T_SOLIDUS else 'NO ✅'} (Solidus = {T_SOLIDUS:.1f} K)",
            f"  Exceeded Liquidus?    {'YES ⚠️' if T_max_val > T_LIQUIDUS else 'NO ✅'} (Liquidus = {T_LIQUIDUS:.1f} K)",
        ]
    
    if 'force_kN' in df.columns:
        F_max = df['force_kN'].max()
        report_lines += [
            f"  Peak Axial Force:     {F_max:.2f} kN (Ceiling = {MACHINE_FORCE_LIMIT_kN} kN)",
            f"  Force Within Limits?  {'YES ✅' if F_max < MACHINE_FORCE_LIMIT_kN else 'NO ⚠️'}",
        ]
    
    if 'power_kW' in df.columns:
        P_max = df['power_kW'].max()
        report_lines += [
            f"  Peak Motor Power:     {P_max:.2f} kW (Ceiling = {MACHINE_POWER_LIMIT_kW} kW)",
            f"  Power Within Limits?  {'YES ✅' if P_max < MACHINE_POWER_LIMIT_kW else 'NO ⚠️'}",
        ]
    
    if 'max_plastic_strain' in df.columns:
        eps_max = df['max_plastic_strain'].max()
        report_lines += [
            f"  Max Plastic Strain:   {eps_max:.4f}",
        ]
    
    if 'max_contact_pressure' in df.columns:
        P_contact_max = df['max_contact_pressure'].max()
        report_lines += [
            f"  Peak Contact Pressure:{P_contact_max / 1e6:.2f} MPa",
        ]
    
    if 'deposited_bead_pct' in df.columns:
        bead_final = df['deposited_bead_pct'].iloc[-1] * 100.0
        report_lines += [
            f"  Deposited Bead Layer: {bead_final:.1f}% Track Volume Active (Gated at T >= 673 K)",
            f"  Layer Deposition:     {'COMPLETED ✅' if bead_final > 80.0 else 'PARTIAL ⚠️'}",
        ]
    
    report_lines += [
        "",
        "=" * 72,
        "  Generated Output Files:",
        f"    • Dashboard:   {os.path.basename(dashboard_path)}",
        f"    • Temperature: {os.path.basename(temp_path)}",
        f"    • Exodus 3D:   afsd_deposition_out.e (open in ParaView)",
        "=" * 72,
    ]
    
    report_text = "\n".join(report_lines)
    print(report_text)
    
    report_path = os.path.join(workspace_dir, "afsd_results_summary.txt")
    with open(report_path, 'w') as f:
        f.write(report_text)
    print(f"\n[AFSD Visualizer] Summary report saved: {report_path}")


if __name__ == "__main__":
    ws = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    postprocess_simulation_data(ws)
