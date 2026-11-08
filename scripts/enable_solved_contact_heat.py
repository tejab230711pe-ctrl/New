#!/usr/bin/env python3
"""Generate a penalty-contact heat qualification deck from a solid contact input.

Restricted to this project's fixed, unnormalized Coulomb penalty formulation.
The original input is preserved. The resulting friction_heat field is nodal W,
not W/m2. This variant must pass coupled energy tests before production use.
"""
import argparse
from pathlib import Path
import re
from render_afsd_remesh_stage import block_end


def subblock(text, name):
    start = text.index(f'  [{name}]')
    return start, block_end(text, start)


def append_block(text, parent, body):
    end = block_end(text, text.index(f'[{parent}]'))
    close = text.rfind('[]', 0, end)
    return text[:close]+body+text[close:]


def convert(source, target):
    if source.resolve() == target.resolve():
        raise ValueError('use a separate target so the source input is preserved')
    text = source.read_text()
    a, b = subblock(text, 'rod_plate')
    contact = text[a:b]
    if not re.search(r'formulation\s*=\s*penalty\s*$', contact, re.M):
        raise ValueError('only full penalty contact is supported')
    if not re.search(r'model\s*=\s*coulomb\s*$', contact, re.M):
        raise ValueError('only Coulomb friction is supported')
    if re.search(r'normalize_penalty\s*=\s*true', contact):
        raise ValueError('normalized contact penalty is not supported by this heat variant')
    primary = re.search(r'primary\s*=\s*([^\n#]+)', contact).group(1).strip().strip("'\"")
    secondary = re.search(r'secondary\s*=\s*([^\n#]+)', contact).group(1).strip().strip("'\"")
    a, b = subblock(text, 'rod_friction_heat')
    text = text[:a]+text[b:]
    a, b = subblock(text, 'friction_heat_aux')
    text = text[:a]+'''  [friction_heat_aux]
    type = PenaltyContactHeatPowerAux
    variable = friction_heat
    boundary = front_to_plate
    paired_boundary = back_to_rod
    contact_stiffness = ${Contact/rod_plate/penalty}
    efficiency = 0.9
    execute_on = 'NONLINEAR TIMESTEP_END'
  []
'''+text[b:]
    text = append_block(text, 'AuxVariables', '''  [negative_contact_heat_power]
    order = FIRST
    family = LAGRANGE
  []
''')
    text = append_block(text, 'AuxKernels', '''  [negative_contact_heat_power]
    type = PenaltyContactHeatPowerAux
    variable = negative_contact_heat_power
    boundary = front_to_plate
    paired_boundary = back_to_rod
    contact_stiffness = ${Contact/rod_plate/penalty}
    efficiency = 0.9
    report_negative = true
    execute_on = 'NONLINEAR TIMESTEP_END'
  []
''')
    a, b = subblock(text, 'friction_power_W')
    text = text[:a]+text[a:b].replace('SideIntegralVariablePostprocessor', 'NodalSum')+text[b:]
    text = append_block(text, 'Postprocessors', '''  [discarded_negative_contact_power_W]
    type = NodalSum
    variable = negative_contact_heat_power
    boundary = front_to_plate
  []
''')
    text += '''
[NodalKernels]
  [solved_contact_heat]
    type = CoupledForceNodalKernel
    variable = T
    v = friction_heat
    boundary = front_to_plate
    coef = 1
  []
[]
'''
    # Remove superseded source comments rather than retain a contradictory heat law.
    lines = []
    for line in text.splitlines():
        if line.lstrip().startswith('#'):
            continue
        lines.append(line)
    # Generated stage decks use different boundary names than the main template.
    lines = [line.replace('front_to_plate', secondary).replace('back_to_rod', primary) for line in lines]
    lines = [re.sub(r'(file_base\s*=\s*).*', lambda m: m.group(1)+str(target.with_suffix('')), line)
             for line in lines]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('''# Solved penalty-contact heating qualification variant.
# Heat = eta * tangential force dot irreversible slip / dt, in nodal watts.
# Recoverable tangential penalty-spring motion is excluded; negative discarded
# power is reported explicitly. All heat enters the secondary side; gap transfer
# couples the bodies. Heat partition and total energy closure require verification.
# Only fixed unnormalized penalty is supported. Do not override heat stiffness
# independently of Contact/rod_plate/penalty or change the contact formulation.
'''+ '\n'.join(lines)+'\n')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('target', type=Path)
    args = parser.parse_args()
    print(convert(args.source.resolve(), args.target.resolve()))
