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


def geo_text(stage: Stage) -> str:
    """A non-overlapping stage geometry in millimetres for Gmsh/OpenCASCADE."""
    y_tool = stage.tool_center_y_mm
    rod_base_z = PLATE_LZ_MM
    rod_top_z = rod_base_z + stage.rod_height_mm
    bead_y_end = max(0.0, y_tool - ROD_RADIUS_MM)
    lines = [
        'SetFactory("OpenCASCADE");',
        '// AA5083 AFSD remesh stage; coordinates are mm.',
        f'Box(1) = {{{-PLATE_LX_MM/2}, 0, 0, {PLATE_LX_MM}, {PLATE_LY_MM}, {PLATE_LZ_MM}}};',
        f'Cylinder(2) = {{0, {y_tool}, {rod_base_z}, 0, 0, {rod_top_z-rod_base_z}, {ROD_RADIUS_MM}}};',
    ]
    volumes = '1, 2'
    if bead_y_end > 1e-9:
        lines.append(
            f'Box(3) = {{{-BEAD_WIDTH_MM/2}, 0, {PLATE_LZ_MM}, '
            f'{BEAD_WIDTH_MM}, {bead_y_end}, {stage.bead_height_mm}}};'
        )
        volumes = '1, 2, 3'
    lines.extend([
        'Mesh.CharacteristicLengthMin = 1.0;',
        'Mesh.CharacteristicLengthMax = 2.5;',
        f'Physical Volume("plate") = {{1}};',
        f'Physical Volume("rod") = {{2}};',
    ])
    if bead_y_end > 1e-9:
        lines.append('Physical Volume("bead") = {3};')
    lines.extend([
        '// Contact and thermal-contact surfaces are identified after import by',
        '// geometric bounding boxes; do not merge volumes at this stage.',
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
        'units': 'mm, s, kg assumed by MOOSE material conversion layer',
        'flash_fraction': FLASH_FRACTION,
        'dwell_s': DWELL_S,
        'deposition_s': DEPOSITION_S,
        'field_transfer': ['T', 'Ux', 'Uy', 'Uz', 'plastic_strain', 'is_deposited'],
        'stages': [],
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
            'previous_exodus': None if stage.index == 1 else str(root / f'stage_{stage.index-1:02d}.e'),
            'output_exodus': str(root / f'{stem}.e'),
        })
        manifest['stages'].append(entry)
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Created {len(stages)} remesh stages in {root}')


if __name__ == '__main__':
    main()
