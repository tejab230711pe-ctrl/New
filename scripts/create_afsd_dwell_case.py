#!/usr/bin/env python3
"""Generate the confirmed cylindrical rod/plate dwell without a prescribed bead.

Initial interference is an explicit numerical/contact-loading assumption.
No complete dwell or solid-to-flow handoff is implied by input generation.
"""
import argparse
from dataclasses import asdict
import json
import math
from pathlib import Path
import subprocess

from create_afsd_remesh_stages import dwell_stage, geo_text
from render_afsd_remesh_stage import render
from enable_solved_contact_heat import convert
from enable_mortar_contact_heat import convert as convert_thermal_contact
from render_afsd_remesh_stage import block_end

ROOT = Path(__file__).resolve().parents[1]


def create(out, interference, mesh_min, mesh_max, end_time, stiffness, conductance,
           thermal_contact='direct'):
    if thermal_contact not in ('direct','quadrature'):
        raise ValueError('thermal_contact must be direct or quadrature')
    if not all(math.isfinite(v) for v in (interference, mesh_min, mesh_max, end_time, stiffness, conductance)):
        raise ValueError('all numerical parameters must be finite')
    if interference < 0 or mesh_min <= 0 or mesh_max < mesh_min or end_time <= 0 or stiffness <= 0 or conductance <= 0:
        raise ValueError('invalid geometry, interval or contact parameters')
    out.mkdir(parents=True, exist_ok=True)
    stage = dwell_stage()
    if end_time > stage.time_end_s:
        raise ValueError("dwell generator cannot extend beyond the specified dwell interval")
    geo = out/'dwell.geo'
    mesh = out/'dwell.msh'
    geo.write_text(geo_text(stage, mesh_min, mesh_max, interference, 0.))
    with (out/'gmsh.log').open('w') as log:
        subprocess.run(['gmsh','-3',str(geo),'-format','msh2','-o',str(mesh)],
                       check=True,stdout=log,stderr=subprocess.STDOUT)
    entry = dict(asdict(stage), mesh=str(mesh), previous_exodus=None,
                 output_exodus=str(out/'dwell.e'))
    # A requested short test interval is recorded in the actual input.
    entry['time_end_s'] = end_time
    approximate = out/'imposed_speed_heat_reference.i'
    render(ROOT/'input/deposition.i', entry, approximate, low_ram=True)
    target = out/'dwell.i'
    solved = out/'solved_slip_quadrature_reference.i' if thermal_contact == 'direct' else target
    convert(approximate, solved)
    text = solved.read_text()
    # Both heating and mechanical contact refer to this single penalty entry.
    import re
    text = re.sub(r'(?m)^(\s*penalty\s*=\s*)[^\n]+', lambda m:m.group(1)+str(stiffness), text)
    text = re.sub(r'(?m)^(\s*gap_conductance\s*=\s*)[^\n]+', lambda m:m.group(1)+str(conductance), text)
    solved.write_text(text)
    if thermal_contact == 'direct':
        convert_thermal_contact(solved,target,'direct')
    text = target.read_text()
    start = text.index('  [exodus]',text.index('[Outputs]'))
    end = block_end(text,start)
    output = text[start:end]
    if re.search(r'(?m)^\s*execute_on\s*=',output):
        output = re.sub(r'(?m)^(\s*execute_on\s*=)[^\n]+',r"\1 'INITIAL TIMESTEP_END'",output)
    else:
        output = output.replace('  [exodus]\n',"  [exodus]\n    execute_on = 'INITIAL TIMESTEP_END'\n",1)
    target.write_text(text[:start]+output+text[end:])
    specification = json.loads((ROOT/'input/process_specification.json').read_text())
    (out/'case.json').write_text(json.dumps(dict(
        kind='confirmed_geometry_contact_qualification', process=specification,
        initial_interference_mm=interference, mesh_min_mm=mesh_min, mesh_max_mm=mesh_max,
        end_s=end_time, penalty_N_per_m=stiffness, gap_conductance=conductance,
        heating='solved irreversible penalty slip; secondary-side source with thermal gap transfer',
        thermal_contact=thermal_contact,
        caveat='Contact parameters and initial interference are explicit assumptions, not calibration'),indent=2)+'\n')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--initial-interference-mm',type=float,required=True)
    parser.add_argument('--penalty',type=float,required=True)
    parser.add_argument('--gap-conductance',type=float,required=True)
    parser.add_argument('--mesh-min-mm',type=float,default=2.)
    parser.add_argument('--mesh-max-mm',type=float,default=4.)
    parser.add_argument('--end-time',type=float,default=4.)
    parser.add_argument('--thermal-contact',choices=('direct','quadrature'),default='direct',
                        help='direct conservative mortar; quadrature retains the failed comparison formulation')
    args = parser.parse_args()
    print(create(args.output.resolve(),args.initial_interference_mm,args.mesh_min_mm,
                 args.mesh_max_mm,args.end_time,args.penalty,args.gap_conductance,args.thermal_contact))
