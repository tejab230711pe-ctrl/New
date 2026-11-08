#!/usr/bin/env python3
"""Reject incomplete/nonconservative standalone ALE runs using supplied feed volume."""
import argparse
import csv
import json
import math
from pathlib import Path


def assess(csv_path, case_path, tolerance):
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('acceptance tolerance must be finite and positive')
    case = json.loads(case_path.read_text())
    if any(not math.isfinite(case[k]) or case[k] <= 0
           for k in ('feed_m_per_s', 'rod_radius_m')):
        raise ValueError('feed and radius must be finite and positive')
    if not all(math.isfinite(case[k]) for k in ('start_s', 'end_s')) or case['end_s'] <= case['start_s']:
        raise ValueError('case must have a finite, positive duration')
    with csv_path.open() as stream:
        rows = [{k:float(v) for k,v in row.items()} for row in csv.DictReader(stream)]
    if len(rows) < 2:
        raise ValueError('no accepted transient output')
    for row in rows:
        if any(not math.isfinite(row[k]) for k in ('time','volume','inlet_area')):
            raise ValueError('nonfinite time, volume or inlet area')
        if row['volume'] <= 0 or row['inlet_area'] <= 0:
            raise ValueError('nonpositive volume or inlet area')
    if abs(rows[0]['time']-case['start_s']) > 1e-10:
        raise ValueError('CSV lacks the specified initial state')
    supplied = 0.0
    records = []
    for old,new in zip(rows,rows[1:]):
        dt = new['time']-old['time']
        if dt <= 0:
            raise ValueError('times must be strictly increasing')
        # This case keeps its inlet flat and at fixed Z. Its mesh moves only
        # in its own plane, so axial feed equals relative normal inlet velocity.
        supplied += dt * case['feed_m_per_s'] * .5 * (old['inlet_area']+new['inlet_area'])
        error = new['volume']-rows[0]['volume']-supplied
        records.append(dict(time=new['time'],supplied_volume_m3=supplied,
                            volume_error_m3=error,relative_to_feed=error/supplied,
                            relative_to_initial_volume=error/rows[0]['volume']))
    final_time=rows[-1]['time']
    complete=math.isclose(final_time,case['end_s'],rel_tol=0,abs_tol=1e-10)
    worst=max(abs(r['relative_to_feed']) for r in records)
    return dict(passed=complete and worst <= tolerance,completed_requested_interval=complete,
                final_time=final_time,maximum_relative_feed_error=worst,
                allowed_relative_feed_error=tolerance,
                inlet_area_relative_geometry_error=rows[0]['inlet_area']/(math.pi*case['rod_radius_m']**2)-1,
                samples=records,
                scope='Volume screen for constant-density standalone flow; not an energy or validation certificate')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--max-relative-feed-error',type=float,required=True,
                        help='Explicit screening tolerance; 0.02 means 2 percent of supplied volume')
    args=parser.parse_args()
    result=assess(args.directory/'flow.csv',args.directory/'case.json',args.max_relative_feed_error)
    (args.directory/'balance.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['passed'] else 2)
