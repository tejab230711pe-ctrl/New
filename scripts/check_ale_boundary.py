#!/usr/bin/env python3
"""Verify manufactured constant-velocity surface motion with BE and BDF2."""
import csv
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='afsd-boundary-') as directory:
    for scheme in ('implicit-euler', 'bdf2'):
        base = Path(directory)/scheme
        command = [str(root/'rotating_disk_deposition-opt'), '-i',
                   str(root/'test/verification/ale_boundary_translation.i'),
                   f'Executioner/scheme={scheme}', f'Outputs/file_base={base}']
        result = subprocess.run(command, env=dict(os.environ, UCX_TLS='self'),
                                capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError(result.stdout+result.stderr)
        with base.with_suffix('.csv').open() as stream:
            rows = list(csv.DictReader(stream))
        if abs(float(rows[-1]['time'])-.3) > 1e-12:
            raise AssertionError('manufactured motion did not reach its endpoint')
        for row in rows:
            for speed, component in enumerate('xyz', 1):
                assert abs(float(row['m'+component])-speed*float(row['time'])) < 1e-10
        print(f'PASS {scheme}: manufactured surface translation at every accepted step')
