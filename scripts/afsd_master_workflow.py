#!/usr/bin/env python3
"""Audit available numerical evidence. This does not execute a coupled deposition chain."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from afsd_process import AFSDProcess
from check_contact_thermal_balance import assess as thermal
from qualify_afsd_flow import qualify

ROOT=Path(__file__).resolve().parents[1]


def evidence_gate(report, scope):
    """A missing, false, or non-boolean acceptance result cannot pass."""
    return {'status':'PASS' if report.get('passed') is True else 'FAIL',
            'scope':scope,'evidence':report}


def assess_case(call, scope):
    try:
        return evidence_gate(call(),scope)
    except (ValueError,KeyError,OSError,RuntimeError) as error:
        return {'status':'UNAVAILABLE','scope':scope,'reason':str(error)}


def completion_gate(times, required_start, required_end):
    import math
    return bool(len(times)>1 and all(math.isfinite(t) for t in times)
                and all(b>a for a,b in zip(times,times[1:]))
                and abs(times[0]-required_start)<1e-10
                and abs(times[-1]-required_end)<1e-10)


def audit(out, contact, flow):
    p=AFSDProcess()
    out.mkdir(parents=True,exist_ok=True)
    results={}
    results['short_contact_thermal']=assess_case(lambda:thermal(contact,.02),
        'Discrete elastic thermal equation; not complete mechanical energy closure')
    results['short_hot_flow']=assess_case(lambda:qualify(flow,.02,.02,1e-6),
        'Standalone initially hot flow; no cold-dwell transfer')
    try:
        with (contact/'dwell.csv').open() as f:
            times=[float(r['time']) for r in csv.DictReader(f)]
        completed=completion_gate(times,0,p.dwell_s)
        results['full_dwell_interval']={'status':'PASS' if completed else 'INCOMPLETE',
            'required_end_s':p.dwell_s,'observed_end_s':times[-1] if times else None,
            'scope':'Time coverage only; does not establish feed onset or material validity'}
    except (OSError,ValueError,KeyError) as error:
        results['full_dwell_interval']={'status':'UNAVAILABLE','reason':str(error)}
    for name,reason in {
        'material_consistency':'Solid tables and ALE property laws require actual comparison; parameter declarations are not proof.',
        'coupled_state_handoff':'No accepted target flow solve consumes a verified transferred solid state.',
        'deposited_segment':'A trailing concentration or particle alone does not establish attachment or a deposited segment.',
        'full_track':'No complete linked feed/traverse/rezone history is available.',
        'actuator_energy_closure':'Stored elastic/kinetic energy, plastic work and boundary transport are not all measured.',
        'experimental_validation':'No independent measured dataset has been compared.'}.items():
        results[name]={'status':'INCOMPLETE','reason':reason}
    summary={'overall_status':'INCOMPLETE','predictive_workflow_complete':False,
        'scope':'Evidence audit; no solver is launched and no physical experiment is performed',
        'milestones':results,'nominal_kinematics_only':{
            'feed_mm_per_min':p.axial_feed_mm_min,'traverse_mm_per_s':p.traverse_speed_mm_s,
            'nominal_track_area_mm2':p.nominal_track_area_mm2},
        'process_specification_sha256':hashlib.sha256((ROOT/'input/process_specification.json').read_bytes()).hexdigest()}
    (out/'afsd_chain_execution_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'verification_runs/complete_chain_qualification')
    parser.add_argument('--contact',type=Path,default=ROOT/'verification_runs/direct_mortar_bulk')
    parser.add_argument('--flow',type=Path,default=ROOT/'verification_runs/variable_mu_flow')
    args=parser.parse_args()
    report=audit(args.output,args.contact,args.flow)
    print(json.dumps({k:v for k,v in report.items() if k!='milestones'},indent=2))
    for name,result in report['milestones'].items(): print(name,result['status'])
    raise SystemExit(0 if report['predictive_workflow_complete'] else 2)
