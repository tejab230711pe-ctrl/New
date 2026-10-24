#!/usr/bin/env python3
"""Generate AFSD remesh stages from a solved/measured free-surface profile.

This is intentionally a *geometry and run-manifest generator*.  A remeshed
MOOSE solve must transfer fields from the preceding Exodus result before the
next stage begins; the manifest records every source/target pair explicitly.

Usage:
  python3 scripts/create_afsd_remesh_stages.py --feed-increment-mm 5 \
      --bead-profile-csv results/free_surface_profile.csv --run-gmsh

The old implementation invented a 25 mm bead width and a 5 percent flash
fraction.  Neither quantity follows from rod feed alone.  This generator now
accepts them only as *results* of a free-surface material-flow calculation (or
of a measured deposited cross-section), validates volume conservation, and
uses those results to make the rezone meshes.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


# The process specification is kept in mm, but MOOSE's existing constitutive
# data use SI.  Every coordinate written to Gmsh is therefore converted to m.
MM = 1.0e-3
ROD_RADIUS_MM = 12.5
ROD_LENGTH_MM = 200.0
TOTAL_FEED_MM = 35.0
# User-specified machine control: 75 mm/min is the Z-axis rod-consumption
# rate.  The machine X axis maps to AFSD simulation Y and completes 50 mm
# during the same 35 mm Z consumption.
TRAVERSE_MM = 50.0
AXIAL_FEED_MM_PER_MIN = 75.0
DWELL_S = 4.0
DEPOSITION_S = TOTAL_FEED_MM / AXIAL_FEED_MM_PER_MIN * 60.0
PLATE_LX_MM = 50.0
PLATE_LY_MM = 100.0
PLATE_LZ_MM = 10.0
# A small imposed overlap provides the initial contact pressure on the
# displacement-controlled CNC shoulder without prescribing a second tip BC.
INITIAL_INTERFERENCE_MM = 0.25
# OpenCASCADE bounding boxes carry geometry tolerances.  A 10 micrometre
# selection envelope robustly captures planar contact faces without selecting
# adjacent cylindrical/side faces.
SURFACE_TOL_M = 1.0e-5


@dataclass(frozen=True)
class Stage:
    index: int
    feed_start_mm: float
    feed_end_mm: float
    time_start_s: float
    time_end_s: float
    tool_center_y_mm: float
    previous_bead_length_mm: float
    bead_length_mm: float
    bead_width_mm: float
    bead_height_mm: float
    rod_height_mm: float
    feed_volume_mm3: float
    bead_volume_mm3: float
    flash_volume_mm3: float


def read_profile(path: Path) -> dict[float, tuple[float, float, float]]:
    """Read free-surface results indexed by cumulative consumed length.

    Required CSV columns are
    ``feed_end_mm,width_mm,height_mm,bead_volume_mm3,flash_volume_mm3``.
    Width and height describe the deposited cross-section at the rezone;
    ``bead_volume_mm3`` is the integral of its actual free-surface shape, not
    width times height times length. The cumulative flash volume is the
    material that has crossed the two open lateral free boundaries. It is not
    a user-selected loss percentage.
    """
    try:
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            required = {"feed_end_mm", "width_mm", "height_mm", "bead_volume_mm3", "flash_volume_mm3"}
            if reader.fieldnames is None or not required.issubset(reader.fieldnames):
                raise ValueError(f"{path} must contain columns: {', '.join(sorted(required))}")
            values: dict[float, tuple[float, float, float, float]] = {}
            for row in reader:
                feed = float(row["feed_end_mm"])
                width = float(row["width_mm"])
                height = float(row["height_mm"])
                bead_volume = float(row["bead_volume_mm3"])
                flash = float(row["flash_volume_mm3"])
                if feed <= 0.0 or width <= 0.0 or height <= 0.0 or bead_volume <= 0.0 or flash < 0.0:
                    raise ValueError(f"{path}: all dimensions must be positive and flash non-negative")
                values[round(feed, 9)] = (width, height, bead_volume, flash)
    except OSError as exc:
        raise ValueError(f"cannot read bead profile {path}: {exc}") from exc
    return values


def stage_schedule(feed_increment_mm: float,
                   profile: dict[float, tuple[float, float, float, float]]) -> list[Stage]:
    """Return stages whose geometry comes from the solved free surface."""
    if feed_increment_mm <= 0:
        raise ValueError("feed increment must be positive")
    rod_area = math.pi * ROD_RADIUS_MM**2
    stages: list[Stage] = []
    consumed = 0.0
    index = 1
    while consumed < TOTAL_FEED_MM - 1e-9:
        next_consumed = min(TOTAL_FEED_MM, consumed + feed_increment_mm)
        fraction = next_consumed / TOTAL_FEED_MM
        bead_length = TRAVERSE_MM * fraction
        feed_volume = rod_area * next_consumed
        try:
            bead_width, bead_height, bead_volume, flash_volume = profile[round(next_consumed, 9)]
        except KeyError as exc:
            raise ValueError(
                f"bead profile has no row for feed_end_mm={next_consumed:g}; "
                "it must contain every remesh endpoint"
            ) from exc
        # Volume conservation is the acceptance check for the free-surface
        # solve. The actual cross-section integral, rather than a rectangular
        # width*height approximation, is used for this check.
        residual = feed_volume - bead_volume - flash_volume
        if abs(residual) > max(1.0, 0.02 * feed_volume):
            raise ValueError(
                f"free-surface volume is not conservative at {next_consumed:g} mm: "
                f"rod={feed_volume:.3f}, bead={bead_volume:.3f}, flash={flash_volume:.3f} mm^3"
            )
        stages.append(
            Stage(
                index=index,
                feed_start_mm=consumed,
                feed_end_mm=next_consumed,
                time_start_s=DWELL_S + DEPOSITION_S * (consumed / TOTAL_FEED_MM),
                time_end_s=DWELL_S + DEPOSITION_S * fraction,
                tool_center_y_mm=ROD_RADIUS_MM + bead_length,
                previous_bead_length_mm=TRAVERSE_MM * (consumed / TOTAL_FEED_MM),
                bead_length_mm=bead_length,
                bead_width_mm=bead_width,
                bead_height_mm=bead_height,
                rod_height_mm=ROD_LENGTH_MM - next_consumed,
                feed_volume_mm3=feed_volume,
                bead_volume_mm3=bead_volume,
                flash_volume_mm3=flash_volume,
            )
        )
        consumed = next_consumed
        index += 1
    return stages


def dwell_stage() -> Stage:
    """Stationary 4 s shoulder dwell before any rod consumption."""
    return Stage(
        index=0,
        feed_start_mm=0.0,
        feed_end_mm=0.0,
        time_start_s=0.0,
        time_end_s=DWELL_S,
        tool_center_y_mm=ROD_RADIUS_MM,
        previous_bead_length_mm=0.0,
        bead_length_mm=0.0,
        bead_width_mm=0.0,
        bead_height_mm=0.0,
        rod_height_mm=ROD_LENGTH_MM,
        feed_volume_mm3=0.0,
        bead_volume_mm3=0.0,
        flash_volume_mm3=0.0,
    )


def geo_text(stage: Stage,
             mesh_min_mm: float,
             mesh_max_mm: float,
             initial_interference_mm: float,
             initial_clearance_mm: float) -> str:
    """A non-overlapping stage geometry in metres for Gmsh/OpenCASCADE."""
    y_tool = stage.tool_center_y_mm * MM
    rod_base_z = (PLATE_LZ_MM + initial_clearance_mm - initial_interference_mm) * MM
    rod_top_z = rod_base_z + stage.rod_height_mm * MM
    bead_y_end = max(0.0, y_tool - ROD_RADIUS_MM * MM)
    # Until the rezone writer consumes the full free-surface polygon, its box
    # is an equal-volume envelope.  Never use the reported crest height here:
    # width*crest-height is generally not the true cross-sectional area.
    rezone_height_mm = (
        stage.bead_volume_mm3 / (stage.bead_width_mm * stage.bead_length_mm)
        if stage.bead_length_mm > 0.0 else 0.0
    )
    lines = [
        'SetFactory("OpenCASCADE");',
        '// AA5083 AFSD remesh stage; coordinates are SI metres.',
        f'Box(1) = {{{-PLATE_LX_MM*MM/2}, 0, 0, {PLATE_LX_MM*MM}, {PLATE_LY_MM*MM}, {PLATE_LZ_MM*MM}}};',
    ]
    rod_tag = 10
    volumes = ['1']
    prior_bead_length = stage.previous_bead_length_mm * MM
    if bead_y_end > 1e-9:
        if prior_bead_length > 1e-9:
            lines.append(
                f'Box(3) = {{{-stage.bead_width_mm*MM/2}, 0, {PLATE_LZ_MM*MM}, '
                f'{stage.bead_width_mm*MM}, {prior_bead_length}, {rezone_height_mm*MM}}};'
            )
            volumes.append('3')
        fresh_start = prior_bead_length
        fresh_length = bead_y_end - fresh_start
        if fresh_length > 1e-9:
            lines.append(
                f'Box(4) = {{{-stage.bead_width_mm*MM/2}, {fresh_start}, {PLATE_LZ_MM*MM}, '
                f'{stage.bead_width_mm*MM}, {fresh_length}, {rezone_height_mm*MM}}};'
            )
            volumes.append('4')
        # Fragmenting makes the bonded plate/deposit interface conformal while
        # retaining the physical tags for plate, prior deposit, and the newly
        # supplied (virgin) deposit.
        lines.append(f'all_solid[] = BooleanFragments{{ Volume{{{", ".join(volumes)}}}; Delete; }}{{}};')
        lines.append('Coherence;')
    lines.append(
        f'Cylinder({rod_tag}) = {{0, {y_tool}, {rod_base_z}, 0, 0, '
        f'{rod_top_z-rod_base_z}, {ROD_RADIUS_MM*MM}}};'
    )
    lines.extend([
        f'Mesh.CharacteristicLengthMin = {mesh_min_mm * MM};',
        f'Mesh.CharacteristicLengthMax = {mesh_max_mm * MM};',
        'Physical Volume("plate") = {1};',
        'Physical Volume("deposit") = {3};' if prior_bead_length > 1e-9 else '',
        'Physical Volume("fresh_deposit") = {4};' if bead_y_end > prior_bead_length + 1e-9 else '',
        f'Physical Volume("rod") = {{{rod_tag}}};',
    ])
    lines.extend([
        '// The named surfaces below are consumed by the stage input deck.',
        f'Physical Surface("rod_bottom") = {{ Surface In BoundingBox{{{-ROD_RADIUS_MM*MM-SURFACE_TOL_M}, {y_tool-ROD_RADIUS_MM*MM-SURFACE_TOL_M}, {rod_base_z-SURFACE_TOL_M}, {ROD_RADIUS_MM*MM+SURFACE_TOL_M}, {y_tool+ROD_RADIUS_MM*MM+SURFACE_TOL_M}, {rod_base_z+SURFACE_TOL_M}}} }};',
        f'Physical Surface("rod_top") = {{ Surface In BoundingBox{{{-ROD_RADIUS_MM*MM-SURFACE_TOL_M}, {y_tool-ROD_RADIUS_MM*MM-SURFACE_TOL_M}, {rod_top_z-SURFACE_TOL_M}, {ROD_RADIUS_MM*MM+SURFACE_TOL_M}, {y_tool+ROD_RADIUS_MM*MM+SURFACE_TOL_M}, {rod_top_z+SURFACE_TOL_M}}} }};',
        f'Physical Surface("workpiece_top") = {{ Surface In BoundingBox{{{-PLATE_LX_MM*MM/2-SURFACE_TOL_M}, {-SURFACE_TOL_M}, {PLATE_LZ_MM*MM-SURFACE_TOL_M}, {PLATE_LX_MM*MM/2+SURFACE_TOL_M}, {PLATE_LY_MM*MM+SURFACE_TOL_M}, {PLATE_LZ_MM*MM+SURFACE_TOL_M}}} }};',
        f'Physical Surface("workpiece_base") = {{ Surface In BoundingBox{{{-PLATE_LX_MM*MM/2-SURFACE_TOL_M}, {-SURFACE_TOL_M}, {-SURFACE_TOL_M}, {PLATE_LX_MM*MM/2+SURFACE_TOL_M}, {PLATE_LY_MM*MM+SURFACE_TOL_M}, {SURFACE_TOL_M}}} }};',
        f'// Active volumes: {", ".join(volumes + [str(rod_tag)])}',
        '',
    ])
    return '\n'.join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--feed-increment-mm', type=float, required=True, choices=(1.0, 2.5, 5.0))
    parser.add_argument('--bead-profile-csv', type=Path, required=True,
                        help='CSV from free-surface solve or measured cross-sections; never guessed dimensions')
    parser.add_argument('--output-dir', type=Path, default=Path('remesh_stages'))
    parser.add_argument('--run-gmsh', action='store_true')
    parser.add_argument('--mesh-min-mm', type=float, default=1.0)
    parser.add_argument('--mesh-max-mm', type=float, default=2.5)
    parser.add_argument('--initial-interference-mm', type=float, default=INITIAL_INTERFERENCE_MM)
    parser.add_argument('--initial-clearance-mm', type=float, default=0.0)
    args = parser.parse_args()
    if (args.mesh_min_mm <= 0 or args.mesh_max_mm < args.mesh_min_mm or
            args.initial_interference_mm < 0 or args.initial_clearance_mm < 0):
        parser.error('mesh sizes must be valid and interference must be non-negative')

    label = f"feed_{args.feed_increment_mm:g}mm"
    root = args.output_dir / label
    root.mkdir(parents=True, exist_ok=True)
    profile = read_profile(args.bead_profile_csv)
    stages = stage_schedule(args.feed_increment_mm, profile)
    manifest = {
        'mesh_units': 'm (SI; compatible with the MOOSE AA5083 model)',
        'process_units': 'mm and s',
        'bead_geometry_source': str(args.bead_profile_csv),
        'flash_definition': 'cumulative volume crossing open lateral free boundaries',
        'initial_interference_mm': args.initial_interference_mm,
        'initial_clearance_mm': args.initial_clearance_mm,
        'mesh_min_mm': args.mesh_min_mm,
        'mesh_max_mm': args.mesh_max_mm,
        'dwell_s': DWELL_S,
        'deposition_s': DEPOSITION_S,
        'gcode': 'G04 P4.0; G01 X50 Z-35 (Z-axis feed prescribed at 75 mm/min)',
        'axial_feed_mm_per_min': AXIAL_FEED_MM_PER_MIN,
        'machine_x_maps_to_simulation_y': True,
        'field_transfer': ['T', 'plastic_strain', 'effective_plastic_strain', 'is_deposited'],
        'stages': [],
    }
    dwell = dwell_stage()
    dwell_geo = root / 'dwell.geo'
    dwell_msh = root / 'dwell.msh'
    dwell_geo.write_text(
        geo_text(dwell, args.mesh_min_mm, args.mesh_max_mm, args.initial_interference_mm,
                 args.initial_clearance_mm),
        encoding='utf-8')
    if args.run_gmsh:
        subprocess.run(['gmsh', '-3', str(dwell_geo), '-format', 'msh2', '-o', str(dwell_msh)], check=True)
    manifest['dwell'] = {
        **asdict(dwell),
        'geometry': str(dwell_geo),
        'mesh': str(dwell_msh),
        'previous_exodus': None,
        'output_exodus': str(root / 'dwell.e'),
    }
    for stage in stages:
        stem = f'stage_{stage.index:02d}'
        geo = root / f'{stem}.geo'
        msh = root / f'{stem}.msh'
        geo.write_text(
            geo_text(stage, args.mesh_min_mm, args.mesh_max_mm, args.initial_interference_mm,
                     args.initial_clearance_mm),
            encoding='utf-8')
        if args.run_gmsh:
            subprocess.run(['gmsh', '-3', str(geo), '-format', 'msh2', '-o', str(msh)], check=True)
        entry = asdict(stage)
        entry.update({
            'geometry': str(geo),
            'mesh': str(msh),
            'previous_exodus': str(root / 'dwell.e') if stage.index == 1 else str(root / f'stage_{stage.index-1:02d}.e'),
            'output_exodus': str(root / f'{stem}.e'),
        })
        manifest['stages'].append(entry)
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Created {len(stages)} remesh stages in {root}')


if __name__ == '__main__':
    main()
