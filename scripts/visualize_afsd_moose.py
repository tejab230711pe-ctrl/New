#!/usr/bin/env python3
"""AFSD Native MOOSE Post-Processing and Visualization Suite.

Reads MOOSE simulation results (Exodus .e and CSV tables) and renders:
  1. AFSD Process Dashboard (Temperature, Forces, Torque, Power Balance)
  2. 3D Free-Surface Morphology & Mushroom Spreading
  3. Trailing Bead Cross-Section and Material Balance
  4. Spatial Temperature Field Distribution

Strictly used for visualization only. All physical fields and equations
are solved natively by MOOSE.
"""

import argparse
import csv
import json
import math
import os
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.io import netcdf_file

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "input" / "process_specification.json"


def load_spec():
    if SPEC_PATH.exists():
        with open(SPEC_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def plot_process_dashboard(csv_path: Path, output_png: Path):
    """Plots the 4-panel process dashboard from MOOSE CSV output."""
    df = pd.read_csv(csv_path)
    if "time" not in df.columns:
        print(f"Warning: 'time' not in {csv_path}, skipping dashboard")
        return

    spec = load_spec()
    kin = spec.get("kinematics", {})
    omega = kin.get("omega_rad_per_s", 125.664)
    v_feed = kin.get("axial_feed_mm_per_s", 1.25) * 1e-3

    fig, axs = plt.subplots(2, 2, figsize=(14, 10), dpi=150)
    fig.suptitle("AFSD Native MOOSE Thermo-Mechanical Process Dashboard", fontsize=16, fontweight="bold")

    # Time axis (scaled to ms or s)
    t = df["time"].values
    t_plot = t * 1e3 if t.max() < 0.1 else t
    time_label = "Time (ms)" if t.max() < 0.1 else "Time (s)"

    # Panel 1: Temperature
    ax1 = axs[0, 0]
    if "T_max" in df.columns:
        ax1.plot(t_plot, df["T_max"], "r-", lw=2, label=r"$T_{\max}$")
    if "T_core" in df.columns:
        ax1.plot(t_plot, df["T_core"], "b--", lw=1.5, label=r"$T_{\text{core}}$")
    if "T_min" in df.columns:
        ax1.plot(t_plot, df["T_min"], "g:", lw=1.5, label=r"$T_{\min}$")
    ax1.axhline(623.15, color="orange", ls="--", alpha=0.7, label=r"Softening Onset ($350^\circ$C)")
    ax1.axhline(798.15, color="purple", ls="--", alpha=0.7, label=r"Flow Threshold ($525^\circ$C)")
    ax1.axhline(864.15, color="darkred", ls=":", alpha=0.5, label=r"Solidus ($591^\circ$C)")
    ax1.set_xlabel(time_label)
    ax1.set_ylabel("Temperature (K)")
    ax1.set_title("Thermal History & Softening Regimes")
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="upper left", fontsize=8)

    # Panel 2: Machine Reactions (Forces & Torque)
    ax2 = axs[0, 1]
    ax2_twin = ax2.twinx()
    if "force_kN" in df.columns:
        ax2.plot(t_plot, df["force_kN"], "b-", lw=2, label="Axial Forging Force (kN)")
    elif "spindle_reaction_z_N" in df.columns:
        ax2.plot(t_plot, np.abs(df["spindle_reaction_z_N"]) * 1e-3, "b-", lw=2, label="Axial Force (kN)")

    if "traverse_force_N" in df.columns:
        ax2.plot(t_plot, np.abs(df["traverse_force_N"]) * 1e-3, "g-.", lw=1.5, label="Traverse Force (kN)")

    if "spindle_torque_Nm" in df.columns:
        ax2_twin.plot(t_plot, np.abs(df["spindle_torque_Nm"]), "r--", lw=2, label="Spindle Torque (N·m)")
        ax2_twin.set_ylabel("Spindle Torque (N·m)", color="r")
        ax2_twin.tick_params(axis="y", labelcolor="r")

    ax2.set_xlabel(time_label)
    ax2.set_ylabel("Axial / Traverse Force (kN)", color="b")
    ax2.tick_params(axis="y", labelcolor="b")
    ax2.set_title("Machine Reactions (Solved Contact Output)")
    ax2.grid(True, alpha=0.3)

    # Panel 3: Actuator Power vs Friction Dissipation
    ax3 = axs[1, 0]
    p_spindle = np.zeros_like(t)
    if "spindle_torque_Nm" in df.columns:
        p_spindle = np.abs(df["spindle_torque_Nm"].values) * omega * 1e-3  # kW
        ax3.plot(t_plot, p_spindle, "b-", lw=2, label=r"Spindle Actuator Power $P_{\text{spindle}} = M_z\omega$")

    if "friction_power_W" in df.columns:
        p_fric = df["friction_power_W"].values * 1e-3  # kW
        ax3.plot(t_plot, p_fric, "r--", lw=2, label=r"Friction Dissipation $\eta \boldsymbol{\tau} \cdot \mathbf{v}_{\text{slip}}$")
    elif "friction_power_kW" in df.columns:
        ax3.plot(t_plot, df["friction_power_kW"], "r--", lw=2, label=r"Friction Dissipation (kW)")

    ax3.set_xlabel(time_label)
    ax3.set_ylabel("Power (kW)")
    ax3.set_title("Machine-Work Accounting & Contact Dissipation")
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc="upper left", fontsize=8)

    # Panel 4: Contact Pressure & Plastic Strain
    ax4 = axs[1, 1]
    ax4_twin = ax4.twinx()
    if "max_contact_pressure" in df.columns:
        ax4.plot(t_plot, df["max_contact_pressure"] * 1e-6, "m-", lw=2, label="Max Contact Pressure (MPa)")
        ax4.set_ylabel("Contact Pressure (MPa)", color="m")
        ax4.tick_params(axis="y", labelcolor="m")

    if "max_effective_plastic_strain" in df.columns:
        ax4_twin.plot(t_plot, df["max_effective_plastic_strain"], "c--", lw=2, label="Max Plastic Strain")
        ax4_twin.set_ylabel("Equivalent Plastic Strain", color="c")
        ax4_twin.tick_params(axis="y", labelcolor="c")

    ax4.set_xlabel(time_label)
    ax4.set_title("Contact Interface & Plastic Deformation Evolution")
    ax4.grid(True, alpha=0.3)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved Process Dashboard: {output_png}")


def plot_free_surface_and_wake(exodus_path: Path, output_png: Path):
    """Extracts and plots 3D free surface mesh spreading and wake deposition from MOOSE Exodus."""
    if not exodus_path.exists():
        print(f"Warning: Exodus file {exodus_path} not found")
        return

    with netcdf_file(exodus_path, mmap=False) as f:
        v = f.variables
        names = [b"".join(r).decode().strip("\x00 ") for r in v["name_nod_var"].data]
        times = np.array(v["time_whole"].data)
        base = np.column_stack([v["coord" + a].data for a in "xyz"])

        last_step = len(times) - 1

        disp = np.zeros_like(base)
        for i, a in enumerate(["Ux", "Uy", "Uz"]):
            if a in names:
                var_idx = names.index(a) + 1
                disp[:, i] = v[f"vals_nod_var{var_idx}"].data[last_step]
            elif f"mesh_{a}" in names:
                var_idx = names.index(f"mesh_{a}") + 1
                disp[:, i] = v[f"vals_nod_var{var_idx}"].data[last_step]

        curr_pos = (base + disp) * 1e3  # convert to mm

        T_field = np.full(len(base), 293.15)
        if "T" in names:
            var_idx = names.index("T") + 1
            T_field = v[f"vals_nod_var{var_idx}"].data[last_step]

    fig = plt.figure(figsize=(15, 6), dpi=150)

    # 3D Mesh & Temperature Scatter
    ax1 = fig.add_subplot(1, 2, 1, projection="3d")
    p1 = ax1.scatter(curr_pos[:, 0], curr_pos[:, 1], curr_pos[:, 2],
                     c=T_field, cmap="plasma", s=6, alpha=0.8)
    ax1.set_xlabel("X (Width, mm)")
    ax1.set_ylabel("Y (Traverse, mm)")
    ax1.set_zlabel("Z (Height, mm)")
    ax1.set_title(f"3D Solved Mesh & Thermal Distribution (t = {times[last_step]*1e3:.2f} ms)")
    fig.colorbar(p1, ax=ax1, shrink=0.6, label="Temperature (K)")

    # 2D Cross Section & Mushroom Expansion
    ax2 = fig.add_subplot(1, 2, 2)
    # Filter points near tool center Y
    y_center = np.median(curr_pos[:, 1])
    slice_mask = np.abs(curr_pos[:, 1] - y_center) < 3.0
    if np.any(slice_mask):
        p2 = ax2.scatter(curr_pos[slice_mask, 0], curr_pos[slice_mask, 2],
                         c=T_field[slice_mask], cmap="plasma", s=25, edgecolors="k", lw=0.3)
        fig.colorbar(p2, ax=ax2, label="Temperature (K)")
    else:
        p2 = ax2.scatter(curr_pos[:, 0], curr_pos[:, 2], c=T_field, cmap="plasma", s=10)

    # Nominal bead envelope comparison
    ax2.axvline(-12.5, color="gray", ls="--", label="Initial Rod Radius (R = 12.5 mm)")
    ax2.axvline(12.5, color="gray", ls="--")
    ax2.set_xlabel("Transverse X (mm)")
    ax2.set_ylabel("Vertical Z (mm)")
    ax2.set_title("Transverse Section: Mushroom Spreading & Free Surface")
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="upper right", fontsize=8)

    plt.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved Morphology & Spreading Plot: {output_png}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dwell-dir", type=Path, default=ROOT / "verification_runs" / "direct_mortar_bulk")
    parser.add_argument("--flow-dir", type=Path, default=ROOT / "verification_runs" / "bdf2_inlet_layers4")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs" / "visualization")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Dwell & Contact Process Dashboard
    dwell_csv = args.dwell_dir / "dwell.csv"
    if not dwell_csv.exists():
        dwell_csv = ROOT / "moose" / "dwell_out.csv"
    if dwell_csv.exists():
        plot_process_dashboard(dwell_csv, args.output_dir / "moose_dwell_dashboard.png")

    # 2. Flow & Spreading Process Dashboard
    flow_csv = args.flow_dir / "flow.csv"
    if not flow_csv.exists():
        flow_csv = ROOT / "moose" / "bdf2_inlet_layers4.csv"
    if flow_csv.exists():
        plot_process_dashboard(flow_csv, args.output_dir / "moose_flow_dashboard.png")

    # 3. 3D Free-Surface & Mushroom Morphology
    flow_e = args.flow_dir / "flow.e"
    if not flow_e.exists():
        flow_e = ROOT / "moose" / "bdf2_inlet_layers4.e"
    if flow_e.exists():
        plot_free_surface_and_wake(flow_e, args.output_dir / "moose_flow_morphology.png")

    dwell_e = args.dwell_dir / "dwell.e"
    if not dwell_e.exists():
        dwell_e = ROOT / "moose" / "dwell_out.e"
    if dwell_e.exists():
        plot_free_surface_and_wake(dwell_e, args.output_dir / "moose_dwell_contact_mesh.png")

    print("\nVisualization generation complete!")
    print(f"Artifacts saved in: {args.output_dir}")


if __name__ == "__main__":
    main()
