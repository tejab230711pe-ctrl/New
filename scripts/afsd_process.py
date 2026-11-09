#!/usr/bin/env python3
"""AFSD Process Specification API.

Single source of truth for geometry, kinematics, material properties,
mass/volume balances, and resource bounds.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "input" / "process_specification.json"


def load_process_spec() -> Dict[str, Any]:
    with open(SPEC_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class AFSDProcess:
    """Convenience wrapper for process parameters."""

    def __init__(self, spec: Dict[str, Any] | None = None):
        self.spec = spec or load_process_spec()
        self.confirmed = self.spec["confirmed"]
        self.assumed = self.spec["existing_code_assumptions"]
        self.kinematics = self.spec.get("kinematics", {})
        self.balance = self.spec.get("material_balance", {})
        self.materials = self.spec.get("material_properties", {})
        self.resources = self.spec.get("resource_limits", {})

        # Geometry in SI (meters) and mm
        self.rod_diameter_mm = float(self.confirmed["rod_diameter_mm"])
        self.rod_radius_mm = self.rod_diameter_mm / 2.0
        self.rod_length_mm = float(self.confirmed["rod_length_mm"])
        self.plate_width_mm = float(self.confirmed["plate_width_mm"])
        self.plate_length_mm = float(self.confirmed["plate_length_mm"])
        self.plate_thickness_mm = float(self.confirmed["plate_thickness_mm"])

        self.rod_diameter_m = self.rod_diameter_mm * 1e-3
        self.rod_radius_m = self.rod_radius_mm * 1e-3
        self.rod_length_m = self.rod_length_mm * 1e-3
        self.plate_width_m = self.plate_width_mm * 1e-3
        self.plate_length_m = self.plate_length_mm * 1e-3
        self.plate_thickness_m = self.plate_thickness_mm * 1e-3

        # Kinematics
        self.rpm = float(self.confirmed["rpm"])
        self.omega_rad_s = self.rpm * 2.0 * math.pi / 60.0
        self.axial_feed_mm_min = float(self.confirmed["axial_feed_mm_per_min"])
        self.axial_feed_mm_s = self.axial_feed_mm_min / 60.0
        self.axial_feed_m_s = self.axial_feed_mm_s * 1e-3

        self.dwell_s = float(self.assumed["dwell_s"])
        self.consumed_length_mm = float(self.assumed["consumed_length_mm"])
        self.consumed_length_m = self.consumed_length_mm * 1e-3
        self.traverse_mm = float(self.assumed["traverse_mm"])
        self.traverse_m = self.traverse_mm * 1e-3

        self.deposition_duration_s = self.consumed_length_mm / self.axial_feed_mm_s
        self.traverse_speed_mm_s = self.traverse_mm / self.deposition_duration_s
        self.traverse_speed_m_s = self.traverse_speed_mm_s * 1e-3
        self.total_time_s = self.dwell_s + self.deposition_duration_s

        # Material balance
        self.rod_area_mm2 = math.pi * (self.rod_radius_mm**2)
        self.rod_area_m2 = self.rod_area_mm2 * 1e-6
        self.feed_volume_rate_mm3_s = self.rod_area_mm2 * self.axial_feed_mm_s
        self.feed_volume_rate_m3_s = self.feed_volume_rate_mm3_s * 1e-9
        self.nominal_track_area_mm2 = self.feed_volume_rate_mm3_s / self.traverse_speed_mm_s
        self.nominal_track_area_m2 = self.nominal_track_area_mm2 * 1e-6

        # Density and mass
        self.rho = float(self.materials.get("density_kg_per_m3", 2650.0))
        self.total_consumed_volume_mm3 = self.rod_area_mm2 * self.consumed_length_mm
        self.total_consumed_mass_kg = self.total_consumed_volume_mm3 * 1e-9 * self.rho

    def spindle_center_y(self, t: float) -> float:
        """Returns the instantaneous tool center Y position in meters."""
        initial_y = float(self.assumed.get("initial_rod_center_y_mm", 12.5)) * 1e-3
        if t <= self.dwell_s:
            return initial_y
        elif t <= self.total_time_s:
            dt = t - self.dwell_s
            return initial_y + self.traverse_speed_m_s * dt
        else:
            return initial_y + self.traverse_m

    def spindle_velocity(self, x: float, y: float, t: float) -> tuple[float, float, float]:
        """Returns prescribed rigid spindle surface velocity (vx, vy, vz) in m/s."""
        cy = self.spindle_center_y(t)
        v_trav = self.traverse_speed_m_s if (self.dwell_s < t <= self.total_time_s) else 0.0
        v_feed = -self.axial_feed_m_s if (self.dwell_s < t <= self.total_time_s) else 0.0
        vx = -self.omega_rad_s * (y - cy)
        vy = self.omega_rad_s * x + v_trav
        vz = v_feed
        return (vx, vy, vz)

    def validate_conservation(self, delta_feed_volume_mm3: float,
                              bead_volume_mm3: float,
                              flash_volume_mm3: float,
                              tolerance: float = 0.02) -> tuple[bool, float]:
        """Checks volume conservation: Delta V_feed = V_bead + V_flash."""
        outflow_sum = bead_volume_mm3 + flash_volume_mm3
        rel_err = abs(delta_feed_volume_mm3 - outflow_sum) / max(1e-12, delta_feed_volume_mm3)
        return (rel_err <= tolerance, rel_err)


if __name__ == "__main__":
    p = AFSDProcess()
    print(f"AFSD Process Specification Loaded:")
    print(f"  Rod: D={p.rod_diameter_mm} mm, L={p.rod_length_mm} mm")
    print(f"  Plate: {p.plate_width_mm} x {p.plate_length_mm} x {p.plate_thickness_mm} mm")
    print(f"  Rotation: {p.rpm} RPM ({p.omega_rad_s:.3f} rad/s)")
    print(f"  Axial feed: {p.axial_feed_mm_min} mm/min ({p.axial_feed_mm_s:.4f} mm/s)")
    print(f"  Traverse speed: {p.traverse_speed_mm_s:.4f} mm/s")
    print(f"  Nominal track cross section: {p.nominal_track_area_mm2:.2f} mm^2")
    print(f"  Incoming volume rate: {p.feed_volume_rate_mm3_s:.2f} mm^3/s")
    print(f"  Available RAM limit: {p.resources.get('safe_memory_limit_mb')} MB")
