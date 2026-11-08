#!/usr/bin/env python3
"""Check conservative partial-footprint heat exchange and open-gap insulation."""
import csv
import os
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def check(directory,gap):
    z=1+gap
    geo=f'''SetFactory("OpenCASCADE");
Box(1)={{0,0,0,1,1,1}};
Box(2)={{.2,.2,{z},.5,.5,.5}};
a[]=Surface In BoundingBox{{-.001,-.001,.9999999,1.001,1.001,1.0000001}};
b[]=Surface In BoundingBox{{.199,.199,{z-1e-7},.701,.701,{z+1e-7}}};
Physical Volume("plate")={{1}};
Physical Volume("rod")={{2}};
Physical Surface("primary")={{a[]}};
Physical Surface("secondary")={{b[]}};
Mesh.MeshSizeMin=.16;
Mesh.MeshSizeMax=.23;
'''
    (directory/'mesh.geo').write_text(geo)
    with (directory/'gmsh.log').open('w') as f:
        subprocess.run(['gmsh','-3',str(directory/'mesh.geo'),'-format','msh2','-o',str(directory/'mesh.msh')],check=True,stdout=f,stderr=subprocess.STDOUT)
    deck=f'''[Mesh]
 [mesh]
  type = FileMeshGenerator
  file = {directory/'mesh.msh'}
 []
[]
[Variables]
 [T]
  block = 'plate rod'
 []
[]
[ICs]
 [plate]
  type = ConstantIC
  variable = T
  block = plate
  value = 300
 []
 [rod]
  type = ConstantIC
  variable = T
  block = rod
  value = 400
 []
[]
[Kernels]
 [time]
  type = TimeDerivative
  variable = T
  block = 'plate rod'
 []
 [diffusion]
  type = Diffusion
  variable = T
  block = 'plate rod'
 []
[]
[UserObjects]
 [flux]
  type = AFSDContactGapFlux
  boundary = secondary
  temperature = T
  conductance = 10
 []
[]
[MortarGapHeatTransfer]
 [exchange]
  temperature = T
  boundary = secondary
  primary_boundary = primary
  secondary_boundary = secondary
  use_displaced_mesh = false
  user_created_gap_flux_models = flux
 []
[]
[Postprocessors]
 [energy]
  type = ElementIntegralVariablePostprocessor
  variable = T
  block = 'plate rod'
  execute_on = 'INITIAL TIMESTEP_END'
 []
 [rod_temperature]
  type = ElementAverageValue
  variable = T
  block = rod
  execute_on = 'INITIAL TIMESTEP_END'
 []
[]
[Executioner]
 type = Transient
 solve_type = NEWTON
 dt = .001
 end_time = .003
 nl_abs_tol = 1e-10
 nl_rel_tol = 1e-10
 petsc_options_iname = '-pc_type -pc_factor_mat_solver_type'
 petsc_options_value = 'lu mumps'
[]
[Preconditioning]
 [all]
  type = SMP
  full = true
 []
[]
[Outputs]
 file_base = {directory/'result'}
 csv = true
 execute_on = 'INITIAL TIMESTEP_END'
[]
'''
    (directory/'test.i').write_text(deck)
    with (directory/'run.log').open('w') as f:
        result=subprocess.run([str(ROOT/'rotating_disk_deposition-opt'),'-i',str(directory/'test.i')],env=dict(os.environ,UCX_TLS='self'),stdout=f,stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError((directory/'run.log').read_text()[-5000:])
    with (directory/'result.csv').open() as f:
        rows=[{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]
    assert abs(rows[-1]['time']-.003)<1e-12
    assert max(abs(r['energy']-rows[0]['energy']) for r in rows)<1e-8
    if gap<0:
        assert rows[-1]['rod_temperature']<399.9
    else:
        assert abs(rows[-1]['rod_temperature']-400)<1e-9


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='afsd-mortar-') as name:
        for gap in [-.001,.001]:
            directory=Path(name)/str(gap);directory.mkdir()
            check(directory,gap)
    print('PASS mortar heat: partial-footprint conservation, hot-to-cold transfer, open-gap insulation')
