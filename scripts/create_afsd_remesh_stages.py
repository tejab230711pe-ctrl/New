#!/usr/bin/env python3
"""Generate conservative AFSD remesh stages for the AA5083 trial campaign.

This is intentionally a *geometry and run-manifest generator*.  A remeshed
MOOSE solve must transfer fields from the preceding Exodus result before the
next stage begins; the manifest records every source/target pair explicitly.

Usage:
  python3 scripts/create_afsd_remesh_stages.py --feed-increment-mm 5
  python3 scripts/create_afsd_remesh_stages.py --feed-increment-mm 2.5
  python3 scripts/create_afsd_remesh_stages.py --feed-increment-mm 1
  python3 scripts/create_afsd_remesh_stages.py --feed-increment-mm 5 --run-gmsh
"""

from __future__ import annotations

import argparse
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
TRAVERSE_MM = 75.0
DWELL_S = 4.0
DEPOSITION_S = 35.0
FLASH_FRACTION = 0.05
PLATE_LX_MM = 50.0
PLATE_LY_MM = 100.0
PLATE_LZ_MM = 10.0
BEAD_WIDTH_MM = 25.0
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
    bead_length_mm: float
    bead_height_mm: float
    rod_height_mm: float
    feed_volume_mm3: float
    bead_volume_mm3: float


def stage_schedule(feed_increment_mm: float) -> list[Stage]:
    """Return stages satisfying V_bead = (1 - flash) V_rod exactly."""
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
        bead_volume = (1.0 - FLASH_FRACTION) * feed_volume
        bead_height = bead_volume / (BEAD_WIDTH_MM * bead_length) if bead_length else 0.0
        stages.append(
            Stage(
                index=index,
                feed_start_mm=consumed,
                feed_end_mm=next_consumed,
                time_start_s=DWELL_S + DEPOSITION_S * (consumed / TOTAL_FEED_MM),
                time_end_s=DWELL_S + DEPOSITION_S * fraction,
                tool_center_y_mm=ROD_RADIUS_MM + bead_length,
                bead_length_mm=bead_length,
                bead_height_mm=bead_height,
                rod_height_mm=ROD_LENGTH_MM - next_consumed,
                feed_volume_mm3=feed_volume,
                bead_volume_mm3=bead_volume,
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
        bead_length_mm=0.0,
        bead_height_mm=0.0,
        rod_height_mm=ROD_LENGTH_MM,
        feed_volume_mm3=0.0,
        bead_volume_mm3=0.0,
    )


def geo_text(stage: Stage) -> str:
    """A non-overlapping stage geometry in metres for Gmsh/OpenCASCADE."""
    y_tool = stage.tool_center_y_mm * MM
    rod_base_z = (PLATE_LZ_MM - INITIAL_INTERFERENCE_MM) * MM
    rod_top_z = rod_base_z + stage.rod_height_mm * MM
    bead_y_end = max(0.0, y_tool - ROD_RADIUS_MM * MM)
    lines = [
        'SetFactory("OpenCASCADE");',
        '// AA5083 AFSD remesh stage; coordinates are SI metres.',
        f'Box(1) = {{{-PLATE_LX_MM*MM/2}, 0, 0, {PLATE_LX_MM*MM}, {PLATE_LY_MM*MM}, {PLATE_LZ_MM*MM}}};',
    ]
    rod_tag = 2
    workpiece = '1'
    if bead_y_end > 1e-9:
        lines.append(
            f'Box(3) = {{{-BEAD_WIDTH_MM*MM/2}, 0, {PLATE_LZ_MM*MM}, '
            f'{BEAD_WIDTH_MM*MM}, {bead_y_end}, {stage.bead_height_mm*MM}}};'
        )
        # The deposited material is bonded to the substrate.  BooleanFragments
        # makes this interface conformal and eliminates the duplicate nodes
        # that a separate plate/bead mesh would otherwise create.
        lines.append('workpiece[] = BooleanFragments{ Volume{1, 3}; Delete; }{};')
        lines.append('Coherence;')
        workpiece = 'workpiece[]'
        # The Boolean operation may reuse low entity tags.  Create the rod
        # afterwards with a high, explicit tag to keep physical IDs stable.
        rod_tag = 10
    lines.append(
        f'Cylinder({rod_tag}) = {{0, {y_tool}, {rod_base_z}, 0, 0, '
        f'{rod_top_z-rod_base_z}, {ROD_RADIUS_MM*MM}}};'
    )
    volumes = f'{workpiece}, {rod_tag}'
    lines.extend([
        'Mesh.CharacteristicLengthMin = 0.001;',
        'Mesh.CharacteristicLengthMax = 0.0025;',
        f'Physical Volume("workpiece") = {{{workpiece}}};',
        f'Physical Volume("rod") = {{{rod_tag}}};',
    ])
    lines.extend([
        '// The named surfaces below are consumed by the stage input deck.',
        f'Physical Surface("rod_bottom") = {{ Surface In BoundingBox{{{-ROD_RADIUS_MM*MM-SURFACE_TOL_M}, {y_tool-ROD_RADIUS_MM*MM-SURFACE_TOL_M}, {rod_base_z-SURFACE_TOL_M}, {ROD_RADIUS_MM*MM+SURFACE_TOL_M}, {y_tool+ROD_RADIUS_MM*MM+SURFACE_TOL_M}, {rod_base_z+SURFACE_TOL_M}}} }};',
        f'Physical Surface("rod_top") = {{ Surface In BoundingBox{{{-ROD_RADIUS_MM*MM-SURFACE_TOL_M}, {y_tool-ROD_RADIUS_MM*MM-SURFACE_TOL_M}, {rod_top_z-SURFACE_TOL_M}, {ROD_RADIUS_MM*MM+SURFACE_TOL_M}, {y_tool+ROD_RADIUS_MM*MM+SURFACE_TOL_M}, {rod_top_z+SURFACE_TOL_M}}} }};',
        f'Physical Surface("workpiece_top") = {{ Surface In BoundingBox{{{-PLATE_LX_MM*MM/2-SURFACE_TOL_M}, {-SURFACE_TOL_M}, {PLATE_LZ_MM*MM-SURFACE_TOL_M}, {PLATE_LX_MM*MM/2+SURFACE_TOL_M}, {PLATE_LY_MM*MM+SURFACE_TOL_M}, {PLATE_LZ_MM*MM+SURFACE_TOL_M}}} }};',
        f'Physical Surface("workpiece_base") = {{ Surface In BoundingBox{{{-PLATE_LX_MM*MM/2-SURFACE_TOL_M}, {-SURFACE_TOL_M}, {-SURFACE_TOL_M}, {PLATE_LX_MM*MM/2+SURFACE_TOL_M}, {PLATE_LY_MM*MM+SURFACE_TOL_M}, {SURFACE_TOL_M}}} }};',
        f'// Active volumes: {volumes}',
        '',
    ])
    return '\n'.join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--feed-increment-mm', type=float, required=True, choices=(1.0, 2.5, 5.0))
    parser.add_argument('--output-dir', type=Path, default=Path('remesh_stages'))
    parser.add_argument('--run-gmsh', action='store_true')
    args = parser.parse_args()

    label = f"feed_{args.feed_increment_mm:g}mm"
    root = args.output_dir / label
    root.mkdir(parents=True, exist_ok=True)
    stages = stage_schedule(args.feed_increment_mm)
    manifest = {
        'mesh_units': 'm (SI; compatible with the MOOSE AA5083 model)',
        'process_units': 'mm and s',
        'flash_fraction': FLASH_FRACTION,
        'initial_interference_mm': INITIAL_INTERFERENCE_MM,
        'dwell_s': DWELL_S,
        'deposition_s': DEPOSITION_S,
        'field_transfer': ['T', 'plastic_strain', 'effective_plastic_strain', 'is_deposited'],
        'stages': [],
    }
    dwell = dwell_stage()
    dwell_geo = root / 'dwell.geo'
    dwell_msh = root / 'dwell.msh'
    dwell_geo.write_text(geo_text(dwell), encoding='utf-8')
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
        geo.write_text(geo_text(stage), encoding='utf-8')
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
