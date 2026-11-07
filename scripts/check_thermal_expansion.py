#!/usr/bin/env python3
"""Run finite-strain thermal coupling against free/constrained cube references."""
import csv
import math
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    env = os.environ.copy()
    # Serial-only tests: avoid shared-memory/socket transports on sandboxed hosts.
    env.setdefault('UCX_TLS', 'self')
    with tempfile.TemporaryDirectory(prefix='afsd-thermal-') as directory:
        for constrained in (False, True):
            name = 'constrained' if constrained else 'free'
            base = Path(directory) / name
            command = [str(ROOT / 'rotating_disk_deposition-opt'), '-i',
                       str(ROOT / 'test/verification/thermal_expansion.i'),
                       f'Outputs/file_base={base}']
            if constrained:
                command += ['BCs/x/boundary=left right',
                            'BCs/y/boundary=bottom top',
                            'BCs/z/boundary=back front']
            result = subprocess.run(command, env=env, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    timeout=60, cwd=ROOT)
            if result.returncode:
                raise RuntimeError(result.stdout)
            with base.with_suffix('.csv').open() as stream:
                row = list(csv.DictReader(stream))[-1]
            if float(row['time']) != 1.0:
                raise AssertionError(f'{name}: simulation did not reach final time')
            displacement = 0.0 if constrained else 2.38e-5 * 0.01 * 0.01
            stress = -70.3e9 * 2.38e-5 * 0.01 / (1 - 2 * 0.33) if constrained else 0.0
            for field in ('ux_right', 'uy_top', 'uz_front'):
                actual = float(row[field])
                if not math.isclose(actual, displacement, rel_tol=1e-5, abs_tol=1e-14):
                    raise AssertionError(f'{name} {field}: {actual} != {displacement}')
            for field in ('sxx', 'syy', 'szz'):
                actual = float(row[field])
                if not math.isclose(actual, stress, rel_tol=1e-5, abs_tol=1e-3):
                    raise AssertionError(f'{name} {field}: {actual} != {stress}')
            print(f'PASS {name}: displacement={row["ux_right"]} m, stress={row["sxx"]} Pa')


if __name__ == '__main__':
    main()
