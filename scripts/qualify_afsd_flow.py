#!/usr/bin/env python3
"""Gate a circular hot-flow run on volume, surface leakage and mesh validity.

Passing this numerical screen does not validate a full deposition process.
All tolerances are explicit; any failed or incomplete run returns exit code 2.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from analyze_afsd_surface_flux import analyze
from check_afsd_flow_balance import assess


def qualify(directory, volume_tolerance, surface_tolerance, continuity_tolerance):
    if any(not math.isfinite(x) or x <= 0 for x in
           (volume_tolerance, surface_tolerance, continuity_tolerance)):
        raise ValueError('all tolerances must be finite and positive')
    balance = assess(directory/'flow.csv', directory/'case.json', volume_tolerance)
    surfaces = analyze(directory)
    samples = surfaces['samples']
    with (directory/'flow.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    csv_times = [float(r['time']) for r in rows]
    exodus_times = [r['time_s'] for r in samples]
    if len(csv_times)-1 != len(exodus_times) or any(
        abs(a-b) > 1e-10 for a,b in zip(csv_times[1:], exodus_times)):
        raise ValueError('CSV and Exodus do not contain the same accepted times')
    worst_leak = max(r['absolute_free_surface_leak_relative_to_feed'] for r in samples)
    worst_continuity = max(abs(r['fluid_net_relative_to_feed']) for r in samples)
    minimum_ratio = min(r['minimum_element_volume_ratio'] for r in samples)
    # The diagnostic upper plasticization threshold is a conservative screening
    # limit here, not a measured solidus or a validated constitutive range.
    temperature_ok = all(math.isfinite(float(r[key])) and 293.15 <= float(r[key]) <= 798.15
                         for r in rows for key in ('T_min','T_max'))
    checks = dict(complete_and_volume=balance['passed'],
                  surface_leakage=worst_leak <= surface_tolerance,
                  fluid_continuity=worst_continuity <= continuity_tolerance,
                  positive_elements=minimum_ratio > 0,
                  temperature_screen=temperature_ok)
    report = dict(passed=all(checks.values()), checks=checks,
                  scope='Numerical hot-flow qualification only; no dwell handoff or experimental validation',
                  maximum_absolute_surface_leak_relative_to_feed=worst_leak,
                  maximum_fluid_net_relative_to_feed=worst_continuity,
                  minimum_element_volume_ratio=minimum_ratio,
                  surface_tolerance=surface_tolerance, continuity_tolerance=continuity_tolerance,
                  volume=balance,
                  artifact_sha256={name: hashlib.sha256((directory/name).read_bytes()).hexdigest()
                                   for name in ('flow.i','flow.msh','flow.csv','flow.e','case.json')})
    (directory/'balance.json').write_text(json.dumps(balance, indent=2)+'\n')
    (directory/'surface_flux.json').write_text(json.dumps(surfaces, indent=2)+'\n')
    (directory/'qualification.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--volume-tolerance', type=float, required=True)
    parser.add_argument('--surface-tolerance', type=float, required=True)
    parser.add_argument('--continuity-tolerance', type=float, required=True)
    args = parser.parse_args()
    result = qualify(args.directory, args.volume_tolerance, args.surface_tolerance,
                     args.continuity_tolerance)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 2)
