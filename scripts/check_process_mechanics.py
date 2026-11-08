#!/usr/bin/env python3
"""Analytical checks of actual MOOSE motion functions, torque and flow material."""
import csv
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

from render_afsd_remesh_stage import block_end, render

ROOT = Path(__file__).resolve().parents[1]
ENV = dict(os.environ, UCX_TLS='self', OMP_NUM_THREADS='1')
BASE = '''
[Mesh]
 type = GeneratedMesh
 dim = 3
[]
[Problem]
 solve = false
[]
[Executioner]
 type = Transient
 num_steps = 1
 dt = 1
[]
[Outputs]
 csv = true
[]
'''


def run(directory, name, contents):
    path = directory / (name + '.i')
    path.write_text(contents)
    result = subprocess.run([str(ROOT / 'rotating_disk_deposition-opt'), '-i', str(path),
                             f'Outputs/file_base={directory / name}'],
                            env=ENV, cwd=ROOT, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, timeout=60)
    (directory / (name + '.log')).write_text(result.stdout)
    if result.returncode:
        raise RuntimeError(result.stdout)
    with (directory / (name + '.csv')).open() as stream:
        return {key: float(value) for key, value in list(csv.DictReader(stream))[-1].items()}


def close(actual, expected, name, atol=1e-10):
    if not math.isclose(actual, expected, rel_tol=1e-8, abs_tol=atol):
        raise AssertionError(f'{name}: {actual} != {expected}')


def motion(directory, text, name, reference_y, start_y, start_time, speed, center_name):
    start = text.index('[Functions]')
    functions = text[start:block_end(text, start)]
    pp = []
    expected = {}
    # Quarter turn, complete turn, and a later time verify spin + translation.
    for i, delta in enumerate((0.0, 0.0125, 0.05, 0.213)):
        t = start_time + delta
        theta = 40 * math.pi * delta
        center = start_y + speed * delta
        values = {'ux': 0.0125 * (math.cos(theta) - 1),
                  'uy': 0.0125 * math.sin(theta) + center - reference_y,
                  'center': center}
        for field, function in [('ux', 'rod_spin_ux'), ('uy', 'rod_spin_uy'),
                                ('center', center_name)]:
            key = f'{field}_{i}'
            pp.append(f'[{key}]\n type = FunctionValuePostprocessor\n function = {function}\n'
                      f' time = {t}\n point = "0.0125 {reference_y} 0"\n[]')
            expected[key] = values[field]
    result = run(directory, name, BASE + functions + '\n[Postprocessors]\n' + '\n'.join(pp) + '\n[]')
    for key, value in expected.items():
        close(result[key], value, name + '/' + key)
    print(f'PASS {name}: radius, rotation phase, traverse and shared center')


def torque(directory):
    for name, force, center, expected in [('cancellation', '1', '0.5', 0),
                                          ('moving', '1', '0.75', 2),
                                          ('signed', '2*y-1', '0.5', -4)]:
        deck = BASE + f'''
[Functions]
 [force]
  type = ParsedFunction
  expression = '{force}'
 []
 [center]
  type = ConstantFunction
  value = {center}
 []
[]
[AuxVariables]
 [rx]
 []
 [ry]
 []
[]
[ICs]
 [rx]
  type = FunctionIC
  variable = rx
  function = force
 []
[]
[Postprocessors]
 [torque]
  type = MovingAxisTorqueReaction
  reaction_force_variables = 'rx ry'
  center_y = center
  direction_vector = '0 0 1'
 []
[]
'''
        close(run(directory, 'torque_' + name, deck)['torque'], expected, name)
    print('PASS torque: opposing moments cancel, translating axis, negative resultant')


def material(directory):
    for name, vx, vy, vz, expected in [('shear', '6*y', '0', '0', 6/math.sqrt(3)),
                                     ('extension', '2*x', '-y', '-z', 2),
                                     ('rotation', '-3*y', '3*x', '0', 0)]:
        deck = BASE + f'''
[Functions]
 [vx]
  type = ParsedFunction
  expression = '{vx}'
 []
 [vy]
  type = ParsedFunction
  expression = '{vy}'
 []
 [vz]
  type = ParsedFunction
  expression = '{vz}'
 []
[]
[AuxVariables]
 [velocity]
  family = LAGRANGE_VEC
  order = FIRST
 []
 [T]
  initial_condition = 723.15
 []
 [rate]
  family = MONOMIAL
  order = CONSTANT
 []
 [heat]
  family = MONOMIAL
  order = CONSTANT
 []
 [viscosity]
  family = MONOMIAL
  order = CONSTANT
 []
[]
[ICs]
 [velocity]
  type = VectorFunctionIC
  variable = velocity
  function_x = vx
  function_y = vy
  function_z = vz
 []
[]
[Materials]
 [flow]
  type = AA5083ALEViscoplasticMaterial
  temperature = T
  velocity = velocity
 []
[]
[AuxKernels]
 [rate]
  type = ADMaterialRealAux
  variable = rate
  property = effective_strain_rate
 []
 [heat]
  type = ADMaterialRealAux
  variable = heat
  property = viscoplastic_heat
 []
 [viscosity]
  type = ADMaterialRealAux
  variable = viscosity
  property = mu
 []
[]
[Postprocessors]
 [rate]
  type = ElementAverageValue
  variable = rate
 []
 [heat]
  type = ElementAverageValue
  variable = heat
 []
 [viscosity]
  type = ElementAverageValue
  variable = viscosity
 []
[]
'''
        result = run(directory, name, deck)
        rate = math.hypot(expected, 1e-3)
        sigma = math.asinh(math.exp((math.log(rate)+174700/(8.314*723.15)-24.98)/5.23))/0.015e-6
        mu = min(1e10, max(1e4, sigma/(3*rate)))
        close(result['rate'], rate, name + ' equivalent rate')
        close(result['viscosity'], mu, name + ' viscosity')
        close(result['heat'], .9*3*mu*expected**2, name + ' dissipation')
    print('PASS flow law: simple shear, uniaxial extension, rigid rotation')


def main():
    with tempfile.TemporaryDirectory(prefix='afsd-mechanics-') as tmp:
        directory = Path(tmp)
        source = ROOT / 'input/deposition.i'
        motion(directory, source.read_text(), 'template_dwell', .05, .05, 0, 0, 'rod_center_y')
        motion(directory, source.read_text(), 'template_traverse', .05, .05, 4,
               .05/28, 'rod_center_y')
        # Synthetic manifest metadata only: no historical solution is needed to
        # test the renderer's kinematics, and no deposition solve is claimed.
        manifest = json.loads((ROOT / 'remesh_stages/feed_5mm_literal_rotation/feed_5mm/manifest.json').read_text())
        for stage in (manifest['dwell'], manifest['stages'][0]):
            stage = dict(stage, previous_exodus=None, output_exodus=str(directory/'unused.e'))
            target = directory/'rendered.i'
            render(source, stage, target)
            regular = target.read_text()
            low_target = directory / 'low_memory.i'
            render(source, stage, low_target, low_ram=True)
            # Resource choices must not silently change physical coefficients.
            import re
            for parameter in ('penalty', 'gap_conductance', 'nl_abs_tol', 'nl_rel_tol'):
                pattern = rf'^\s*{parameter}\s*=\s*(\S+)'
                normal_value = re.search(pattern, regular, re.MULTILINE).group(1)
                low_value = re.search(pattern, low_target.read_text(), re.MULTILINE).group(1)
                if normal_value != low_value:
                    raise AssertionError(f'low-memory mode changed {parameter}')
            start_y = (.0125 + stage['previous_bead_length_mm']/1000)
            end_y = stage['tool_center_y_mm']/1000
            speed = (end_y-start_y)/(stage['time_end_s']-stage['time_start_s'])
            motion(directory, target.read_text(), f'stage_{stage["index"]}', end_y,
                   start_y, stage['time_start_s'], speed, 'rod_stage_center_y')
        torque(directory)
        material(directory)
        result = run(directory, 'thermal_contact',
                     (ROOT / 'test/verification/thermal_contact_equilibrium.i').read_text())
        close(result['time'], 0.001, 'thermal-contact final time')
        close(result['minimum'], 293.15, 'thermal-contact minimum', atol=1e-8)
        close(result['maximum'], 293.15, 'thermal-contact maximum', atol=1e-8)
        print('PASS partial-footprint thermal contact: uniform equilibrium preserved')


if __name__ == '__main__':
    main()
