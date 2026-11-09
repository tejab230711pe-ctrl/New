#!/usr/bin/env python3
"""Compare actual compiled ALE properties against the solid deck's parsed materials.

Agreement is a numerical compatibility check, not experimental calibration.
A broad plausible range cannot certify agreement between two constitutive laws.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
from check_process_mechanics import BASE,ROOT,run
from render_afsd_remesh_stage import block_end
from afsd_process import AFSDProcess


def evaluate_garofalo_stress(T_K,edot,p):
    if not math.isfinite(T_K) or T_K<=0 or not math.isfinite(edot) or edot<0:
        raise ValueError('positive temperature and nonnegative rate required')
    law=p.materials['flow_law']
    rate=math.sqrt(edot**2+law['strain_rate_floor_per_s']**2)
    argument=math.exp((math.log(rate)+law['activation_energy_J_per_mol']/(law['gas_constant_R']*T_K)-law['log_preexponential_lnA'])/law['stress_exponent_n'])
    stress=math.asinh(argument)/law['sinh_alpha_per_Pa'];raw=stress/(3*rate)
    viscosity=min(max(raw,law['mu_min_Pa_s']),law['mu_max_Pa_s'])
    return 3*viscosity*rate,viscosity,viscosity!=raw


def assess_materials(out,solid=ROOT/'moose/01_dwell_contact.i',tolerance=1e-6):
    if not math.isfinite(tolerance) or tolerance<=0:raise ValueError('positive tolerance required')
    out.mkdir(parents=True,exist_ok=True);text=solid.read_text();materials=[]
    for name in ('aa5083_k','aa5083_rho','aa5083_cp'):
        start=text.index('  ['+name+']')
        block=text[start:block_end(text,start)]
        materials.append(re.sub(r'(?m)^\s*block\s*=.*\n','\n',block))
    fields={'solid_k':('thermal_conductivity',False),'solid_cp':('specific_heat',False),
            'solid_rho':('density',False),'flow_k':('k',True),'flow_cp':('cp',True),'flow_rho':('rho',True)}
    samples=[]
    for temperature in [293.15,450.,623.15,723.15,798.15]:
        deck=BASE+'\n[AuxVariables]\n [T]\n  initial_condition = '+str(temperature)+'\n []\n [velocity]\n  family = LAGRANGE_VEC\n  order = FIRST\n []\n'
        for name in fields:deck+=' ['+name+']\n  family = MONOMIAL\n  order = CONSTANT\n []\n'
        deck+='[]\n[Materials]\n'+''.join(materials)+' [flow]\n  type = AA5083ALEViscoplasticMaterial\n  temperature = T\n  velocity = velocity\n []\n[]\n[AuxKernels]\n'
        for name,(prop,ad) in fields.items():
            deck+=f' [{name}]\n  type = {"AD" if ad else ""}MaterialRealAux\n  variable = {name}\n  property = {prop}\n []\n'
        deck+='[]\n[Postprocessors]\n'
        for name in fields:deck+=f' [{name}]\n  type = ElementAverageValue\n  variable = {name}\n []\n'
        deck+='[]\n';values=run(out,'material_'+str(temperature).replace('.','_'),deck)
        errors={prop:abs(values['flow_'+prop]-values['solid_'+prop])/abs(values['solid_'+prop]) for prop in ('k','cp','rho')}
        samples.append(dict(temperature_K=temperature,values=values,relative_differences=errors))
    worst=max(e for r in samples for e in r['relative_differences'].values())
    report=dict(passed=worst<=tolerance,scope='Actual MOOSE thermal-property compatibility only',
        maximum_relative_difference=worst,tolerance=tolerance,samples=samples,
        constitutive_overlap_validated=False,calibrated_range_validated=False,
        solid_input_sha256=hashlib.sha256(solid.read_bytes()).hexdigest(),
        note='Plasticization bounds and viscosity clamps are numerical choices, not proof of a calibrated solid-state range.')
    (out/'material_consistency.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'verification_runs/material_comparison')
    parser.add_argument('--solid-input',type=Path,default=ROOT/'moose/01_dwell_contact.i')
    args=parser.parse_args();report=assess_materials(args.output,args.solid_input)
    print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2))
    raise SystemExit(0 if report['passed'] else 2)
