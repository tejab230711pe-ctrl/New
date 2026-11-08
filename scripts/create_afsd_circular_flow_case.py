#!/usr/bin/env python3
"""Create a standalone circular-inlet ALE qualification case (not a dwell handoff)."""
import argparse
import json
import math
from pathlib import Path
import subprocess
from render_afsd_remesh_stage import replace_top_level_block, block_end

ROOT = Path(__file__).resolve().parents[1]


def create(out, size, initial_temperature, end_time, inlet_extension=.004, time_step=5e-7, scheme="bdf2", max_time_step=None, rod_layers=4):
    if not (math.isfinite(size) and 0 < size <= .01):
        raise ValueError('mesh size must be finite and in (0, 0.01] m')
    if not (math.isfinite(initial_temperature) and 293.15 <= initial_temperature <= 798.15):
        raise ValueError('qualification temperature must be within 293.15..798.15 K')
    if not math.isfinite(end_time) or end_time <= 4:
        raise ValueError('end time must exceed the qualification start time of 4 s')
    if not math.isfinite(inlet_extension) or inlet_extension < 0:
        raise ValueError("inlet extension must be finite and nonnegative")
    if not math.isfinite(time_step) or time_step <= 0 or time_step > 1e-4:
        raise ValueError("time step must be finite and in (0, 1e-4] s")
    if scheme not in ('implicit-euler', 'bdf2'):
        raise ValueError('unsupported time integration scheme')
    max_time_step = (max(time_step, 2e-5) if scheme == "bdf2" else time_step) if max_time_step is None else max_time_step
    if not math.isfinite(max_time_step) or not time_step <= max_time_step <= 1e-4:
        raise ValueError('maximum time step must lie between initial step and 1e-4 s')
    if rod_layers < 1:
        raise ValueError("rod_layers must be positive")
    inlet_z = .016 + inlet_extension
    out.mkdir(parents=True, exist_ok=True)
    mesh = out/'flow.msh'
    geo = out/'flow.geo'
    # Extrude a conforming disk/annulus mesh. Vertical inlet-adjacent facets
    # keep axial feed tangent to the rod side even on the polygonal mesh;
    # independently meshed cylinder rings would introduce artificial side flux.
    geo.write_text(f'''SetFactory("OpenCASCADE");
Disk(1) = {{0, 0.0125, 0.010, 0.020, 0.020}};
Disk(2) = {{0, 0.0125, 0.010, 0.0125, 0.0125}};
s[] = BooleanFragments{{ Surface{{1}}; Delete; }}{{ Surface{{2}}; Delete; }};
Extrude {{0,0,0.006}} {{ Surface{{s[]}}; Layers{{{max(1,math.ceil(.006/size))}}}; }}
If ({inlet_extension} > 0)
  core_top[] = Surface In BoundingBox{{-0.012501,-0.000001,0.015999,0.012501,0.025001,0.016001}};
  Extrude {{0,0,{inlet_extension}}} {{ Surface{{core_top[]}}; Layers{{{max(rod_layers,math.ceil(inlet_extension/size))}}}; }}
EndIf
v[] = Volume{{:}};
inlet[] = Surface In BoundingBox{{-0.012501,-0.000001,{inlet_z-1e-6},0.012501,0.025001,{inlet_z+1e-6}}};
bottom[] = Surface In BoundingBox{{-0.020001,-0.007501,0.009999,0.020001,0.032501,0.010001}};
external[] = CombinedBoundary{{ Volume{{v[]}}; }};
For i In {{0:#external[]-1}}
  external[i] = Abs(external[i]);
EndFor
free[] = external[];
free[] -= inlet[];
free[] -= bottom[];
Physical Volume("flow", 1) = {{v[]}};
Physical Surface("rod_inlet", 11) = {{inlet[]}};
Physical Surface("plate", 12) = {{bottom[]}};
Physical Surface("free_surface", 13) = {{free[]}};
Mesh.CharacteristicLengthMin = {size};
Mesh.CharacteristicLengthMax = {size};
Mesh.MshFileVersion = 2.2;
''')
    with (out/'gmsh.log').open('w') as log:
        subprocess.run(['gmsh',str(geo),'-3','-o',str(mesh)],check=True,
                       stdout=log,stderr=subprocess.STDOUT)
    text=(ROOT/'input/afsd_ale_flow_stage.i').read_text()
    text=replace_top_level_block(text,'Mesh',f'''[Mesh]
 [file]
  type = FileMeshGenerator
  file = {mesh}
 []
 [free_nodes]
  type = ParsedGenerateNodeset
  input = file
  new_nodeset_name = free_nodes
  expression = '1'
  included_nodesets = free_surface
  excluded_nodesets = 'rod_inlet plate'
 []
 displacements = 'mesh_x mesh_y mesh_z'
[]
''')
    text=replace_top_level_block(text,'Functions', '''[Functions]
 [center_y]
  type = ParsedFunction
  expression = '0.0125 + 0.00178571428571429*(t-4)'
 []
 [inlet_mesh_x]
  type = ParsedFunction
  expression = 'x*(cos(125.663706143592*(t-4))-1)-(y-0.0125)*sin(125.663706143592*(t-4))'
 []
 [inlet_mesh_y]
  type = ParsedFunction
  expression = 'x*sin(125.663706143592*(t-4))+(y-0.0125)*(cos(125.663706143592*(t-4))-1)+0.00178571428571429*(t-4)'
 []
 [shoulder_vx]
  type = ParsedFunction
  symbol_names = center
  symbol_values = center_y
  expression = '-125.663706143592*(y-center)'
 []
 [shoulder_vy]
  type = ParsedFunction
  expression = '125.663706143592*x + 0.00178571428571429'
 []
 [shoulder_vz]
  type = ConstantFunction
  value = -0.00125
 []
[]
''')
    # Divergence-free qualification initial velocity: no slip on the plate,
    # prescribed spin/traverse/feed at the inlet, outward feed accommodation.
    # This is an explicit assumed initial state, not a transferred dwell result.
    initial_functions = ""
    for component, expression in {
        'x': '-125.663706143592*(y-0.0125)*(z-0.010)/0.006 + 3*0.00125*(z-0.010)*(0.016-z)/0.006^3*x',
        'y': '(125.663706143592*x + 0.00178571428571429)*(z-0.010)/0.006 + 3*0.00125*(z-0.010)*(0.016-z)/0.006^3*(y-0.0125)',
        'z': '-0.00125*(3*((z-0.010)/0.006)^2 - 2*((z-0.010)/0.006)^3)',
    }.items():
        # Continue the inlet velocity as rigid spin plus axial plug feed above
        # the deforming pad. The upstream inlet avoids a coplanar source/free rim.
        expression = expression.replace("z-0.010", "min(z-0.010,0.006)").replace("0.016-z", "max(0.016-z,0)")
        initial_functions += f"  [initial_v{component}]\n    type = ParsedFunction\n    expression = '{expression}'\n  []\n"
    end = block_end(text, text.index('[Functions]'))
    close = text.rfind('[]', 0, end)
    text = text[:close] + initial_functions + text[close:]
    text += "\n[ICs]\n [initial_velocity]\n  type = VectorFunctionIC\n  variable = velocity\n  function_x = initial_vx\n  function_y = initial_vy\n  function_z = initial_vz\n []\n[]\n"
    text=text.replace('initial_condition = 623.15',f'initial_condition = {initial_temperature}')
    text=text.replace('boundary = back','boundary = plate').replace('boundary = front','boundary = rod_inlet')
    text=text.replace("boundary = 'left right bottom top'",'boundary = free_nodes')
    text=text.replace('associated_subdomain = 0','associated_subdomain = flow')
    # Dummy integrated terms require side sets; nodal motion uses disjoint node
    # sets so the inlet rim/plate edge cannot receive incompatible constraints.
    for component in ('x','y','z'):
        name=f'  [move_free_{component}_dummy]'
        a=text.index(name);b=text.index('  []',a)
        text=text[:a]+text[a:b].replace('boundary = free_nodes','boundary = free_surface')+text[b:]
    a=text.index('  [shoulder_inlet]');b=text.index('  []',a)
    text=text[:b]+'    use_displaced_mesh = true\n'+text[b:]
    new_bcs=''
    for component in ('x','y','z'):
        new_bcs+=f'''  [inlet_mesh_{component}]
    type = FunctionDirichletBC
    variable = mesh_{component}
    boundary = rod_inlet
    function = {'inlet_mesh_'+component if component in ('x','y') else '0'}
  []
'''
    new_bcs+=f'''  [inlet_temperature]
    type = DirichletBC
    variable = T
    boundary = rod_inlet
    value = {initial_temperature}
  []
  [free_cooling]
    type = ConvectiveFluxFunction
    variable = T
    boundary = free_surface
    coefficient = 25
    T_infinity = 293.15
    use_displaced_mesh = true
  []
'''
    end=block_end(text,text.index('[BCs]'));close=text.rfind('[]',0,end)
    text=text[:close]+new_bcs+text[close:]
    text=text.replace('type = INSADDisplaceBoundaryBC','type = AFSDDisplaceBoundaryBC')
    text=text.replace('  solve_type = NEWTON',f'  solve_type = NEWTON\n  scheme = {scheme}')
    text=text.replace('dtmin = 1.e-6',f'dtmin = {time_step}')
    text=text.replace('dtmax = 1.e-4',f'dtmax = {max_time_step}')
    text=text.replace('dt = 1.e-5',f'dt = {time_step}')
    text=text.replace('end_time = 8.0',f'end_time = {end_time}')
    text=text.replace('file_base = ale_flow_stage',f'file_base = {out/"flow"}')
    text=text.replace('execute_on = FINAL',"execute_on = 'INITIAL TIMESTEP_END'")
    text=text.replace('  csv = true',f'  csv = true\n  file_base = {out/"flow"}')
    text+='''
[Postprocessors]
 [volume]
  type = VolumePostprocessor
  use_displaced_mesh = true
  execute_on = 'INITIAL TIMESTEP_END'
 []
 [T_min]
  type = NodalExtremeValue
  variable = T
  value_type = min
  execute_on = 'INITIAL TIMESTEP_END'
 []
 [T_max]
  type = NodalExtremeValue
  variable = T
  value_type = max
  execute_on = 'INITIAL TIMESTEP_END'
 []
 [inlet_area]
  type = FunctionSideIntegral
  function = 1
  boundary = rod_inlet
  use_displaced_mesh = true
  execute_on = 'INITIAL TIMESTEP_END'
 []
[]
'''
    text='# Standalone hot-flow qualification; temperature is prescribed, not transferred from dwell.\n'+text
    (out/'flow.i').write_text(text)
    (out/'case.json').write_text(json.dumps(dict(kind='standalone_flow_qualification',
        initial_velocity='assumed divergence-free spin/feed profile; not a dwell transfer',
        rpm=1200,feed_m_per_s=.00125,traverse_m_per_s=.05/28,
        rod_radius_m=.0125,initial_flow_radius_m=.02,initial_flow_height_m=.006,
        inlet_extension_m=inlet_extension,inlet_z_m=inlet_z,time_step_s=time_step,
        time_scheme=scheme,max_time_step_s=max_time_step,rod_layers=rod_layers,
        inlet_mesh_motion="rigid rotation and traverse, fixed Z",mesh_method="layered extrusion",
        temperature_K=initial_temperature,start_s=4,end_s=end_time,mesh_size_m=size),indent=2)+'\n')
    return out/'flow.i'


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--mesh-size',type=float,default=.006)
    parser.add_argument('--temperature',type=float,default=723.15)
    parser.add_argument('--end-time',type=float,default=4.001)
    parser.add_argument('--inlet-extension',type=float,default=.004,
                        help='Resolved rod length above the flow pad (m); zero reproduces the coplanar defect')
    parser.add_argument('--time-step',type=float,default=5e-7)
    parser.add_argument('--scheme',choices=('implicit-euler','bdf2'),default='bdf2')
    parser.add_argument('--max-time-step',type=float)
    parser.add_argument('--rod-layers',type=int,default=4)
    args=parser.parse_args()
    print(create(args.output.resolve(),args.mesh_size,args.temperature,args.end_time,args.inlet_extension,args.time_step,args.scheme,args.max_time_step,args.rod_layers))
