#!/usr/bin/env python3
"""Create a conservative mortar thermal-contact qualification variant.

Preserves the source deck. Uses the same prescribed closed-contact conductance;
open gaps have zero transfer. Mechanical Coulomb penalty contact is unchanged.
"""
import argparse
from pathlib import Path
import re
from render_afsd_remesh_stage import block_end
from enable_solved_contact_heat import append_block


def convert(source, target, formulation='multiplier'):
    if source.resolve() == target.resolve():
        raise ValueError('source and target must differ')
    text = source.read_text()
    start = text.index('[ThermalContact]')
    end = block_end(text, start)
    old = text[start:end]
    def value(key):
        match = re.search(r'^\s*'+key+r'\s*=\s*([^\n#]+)', old, re.M)
        if not match:
            raise ValueError('missing '+key)
        return match.group(1).strip().strip("'\"")
    # Put the smaller rod face on the multiplier side. The plate extends far
    # outside its footprint; using that whole plate as secondary leaves many
    # unsupported multiplier faces. This does not change mechanical contact.
    if value('primary') != 'rod_bottom' or value('secondary') != 'workpiece_top':
        raise ValueError('this converter requires the confirmed rod/plate boundary names')
    primary, secondary = value('secondary'), value('primary')
    conductance = float(value('gap_conductance'))
    if formulation not in ('multiplier','direct'):
        raise ValueError('unknown thermal formulation')
    replacement = f'''[MortarGapHeatTransfer]
  [conservative_contact]
    temperature = T
    primary_boundary = {primary}
    secondary_boundary = {secondary}
    boundary = {secondary}
    use_displaced_mesh = true
    displacements = 'Ux Uy Uz'
    user_created_gap_flux_models = closed_contact_flux
  []
[]
'''
    if formulation == 'direct':
        replacement = f'''[Constraints]
  [conservative_contact]
    type = AFSDConservativeContactHeat
    secondary_variable = T
    primary_boundary = {primary}
    secondary_boundary = {secondary}
    primary_subdomain = thermal_primary
    secondary_subdomain = thermal_secondary
    use_displaced_mesh = true
    conductance = {conductance}
  []
[]
'''
    text = text[:start]+replacement+text[end:]
    # Mortar adds lower-dimensional elements. Bulk heat storage/conduction must
    # not also integrate over those interface elements (which would introduce
    # spurious surface heat capacity with inconsistent units).
    for parent in ('Kernels','Materials'):
        start = text.index('['+parent+']')
        end = block_end(text,start)
        objects = text[start:end]
        for match in reversed(list(re.finditer(r'(?m)^  \[[^]\n]+\]\n',objects))):
            stop = block_end(objects,match.start())
            if not re.search(r'(?m)^\s*block\s*=',objects[match.start():stop]):
                objects = objects[:match.end()]+"    block = 'plate rod'\n"+objects[match.end():]
        text = text[:start]+objects+text[end:]
    start = text.index('  [T_mean]',text.index('[Postprocessors]'))
    stop = block_end(text,start)
    if not re.search(r'(?m)^\s*block\s*=',text[start:stop]):
        text = text[:start]+text[start:].replace('  [T_mean]\n',"  [T_mean]\n    block = 'plate rod'\n",1)
    if formulation == 'direct':
        text = append_block(text, 'Mesh', f'''  [thermal_primary]
    type = LowerDBlockFromSidesetGenerator
    input = file_mesh
    sidesets = {primary}
    new_block_name = thermal_primary
  []
  [thermal_secondary]
    type = LowerDBlockFromSidesetGenerator
    input = thermal_primary
    sidesets = {secondary}
    new_block_name = thermal_secondary
  []
''')
    else:
        text = append_block(text, 'UserObjects', f'''  [closed_contact_flux]
    type = AFSDContactGapFlux
    temperature = T
    boundary = {secondary}
    conductance = {conductance}
    use_displaced_mesh = true
  []
''')
    text = re.sub(r'(?m)^(\s*file_base\s*=\s*)[^\n]+',
                  lambda m:m.group(1)+str(target.with_suffix('').resolve()),text)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('target',type=Path)
    parser.add_argument('--formulation', choices=('multiplier','direct'), default='multiplier')
    args = parser.parse_args()
    convert(args.source,args.target,args.formulation)
