#!/usr/bin/env python3
"""Report signed actuator power. Full energy closure requires missing storage/work fields."""
import argparse
import csv
import json
import math
from pathlib import Path
from afsd_process import AFSDProcess


def assess_power_balance(case_dir, tolerance=.05):
    if not math.isfinite(tolerance) or tolerance<=0:
        raise ValueError('positive finite tolerance required')
    case=json.loads((case_dir/'case.json').read_text())
    p=AFSDProcess(case.get('process'))
    with (case_dir/'dwell.csv').open() as f:
        rows=[{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]
    required=['time','spindle_torque_Nm','spindle_reaction_z_N','spindle_reaction_y_N','friction_power_W']
    if len(rows)<2 or any(not math.isfinite(r[k]) for r in rows for k in required):
        raise ValueError('finite complete reaction history required')
    if any(b['time']<=a['time'] for a,b in zip(rows,rows[1:])):
        raise ValueError('strictly increasing time required')
    records=[]
    for row in rows[1:]:
        feeding=p.dwell_s<=row['time']<p.total_time_s
        # Saved reaction vectors are driven-boundary residual reactions. Torque
        # uses the same vector cross lever arm convention; preserve signs.
        rotation=row['spindle_torque_Nm']*p.omega_rad_s
        feed=row['spindle_reaction_z_N']*(-p.axial_feed_m_s if feeding else 0.)
        travel=row['spindle_reaction_y_N']*(p.traverse_speed_m_s if feeding else 0.)
        records.append(dict(time_s=row['time'],P_spindle_W=rotation,P_feed_W=feed,
            P_travel_W=travel,P_input_W=rotation+feed+travel,
            P_friction_heat_W=row['friction_power_W']))
    result=dict(passed=False,status='INCOMPLETE',scope='Signed actuator power diagnostic, not a complete energy balance',
        missing_terms=['elastic and kinetic energy increments','bulk plastic work and stored fraction',
                       'recoverable contact penalty energy','energy transported across open boundaries'],records=records)
    (case_dir/'actuator_power_balance.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--tolerance',type=float,default=.05)
    args=parser.parse_args();print(json.dumps(assess_power_balance(args.directory,args.tolerance),indent=2))
    raise SystemExit(2)
