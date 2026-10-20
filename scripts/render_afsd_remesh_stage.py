#!/usr/bin/env python3
"""Render one executable AFSD remesh stage and its Exodus transfer fragment.

This script does no solve.  It turns the validated base physics deck into a
single-topology stage deck, and emits explicit Exodus sampling blocks for
stages after the first one.  Run it before launching each stage, never after a
normal MOOSE restart (the mesh topology has changed).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


STATE_VARIABLES = (
    "T is_deposited effective_plastic_strain "
    "plastic_strain_xx plastic_strain_yy plastic_strain_zz "
    "plastic_strain_xy plastic_strain_yz plastic_strain_zx"
)
PLASTIC_COMPONENTS = (
    "plastic_strain_xx plastic_strain_yy plastic_strain_zz "
    "plastic_strain_xy plastic_strain_yz plastic_strain_zx"
)


def block_end(text: str, start: int) -> int:
    """Return the end of a top-level MOOSE block beginning at *start*."""
    depth = 0
    offset = start
    for line in text[start:].splitlines(keepends=True):
        token = line.strip()
        if token == "[]":
            depth -= 1
            if depth == 0:
                return offset + len(line)
        elif token.startswith("[") and token.endswith("]"):
            depth += 1
        offset += len(line)
    raise ValueError("unclosed MOOSE block")


def replace_top_level_block(text: str, name: str, replacement: str) -> str:
    marker = f"[{name}]"
    start = text.index(marker)
    end = block_end(text, start)
    return text[:start] + replacement + text[end:]


def transfer_fragment(previous: Path) -> str:
    functions = []
    for variable in ("effective_plastic_strain", *PLASTIC_COMPONENTS.split()):
        functions.extend(
            [f"  [restart_{variable}]", "    type = SolutionFunction", "    solution = remesh_source", f"    from_variable = {variable}", "  []"]
        )
    ics = []
    for variable in ("T", "is_deposited"):
        ics.extend(
            [f"  [restart_{variable}]", "    type = SolutionIC", "    solution_uo = remesh_source", f"    variable = {variable}", f"    from_variable = {variable}", "  []"]
        )
    return "\n".join(
        [
            "# Generated Exodus-to-remesh transfer. Do not edit by hand.",
            "[UserObjects]",
            "  [remesh_source]",
            "    type = SolutionUserObject",
            f"    mesh = {previous.resolve()}",
            f"    system_variables = '{STATE_VARIABLES}'",
            "    timestep = LATEST",
            "    execute_on = INITIAL",
            "  []",
            "[]",
            "",
            "[Functions]",
            *functions,
            "[]",
            "",
            "[ICs]",
            *ics,
            "[]",
        ]
    ) + "\n"


def render(source: Path, stage: dict, target: Path, low_ram: bool = False) -> None:
    text = source.read_text(encoding="utf-8")
    mesh = Path(stage["mesh"]).resolve()
    text = replace_top_level_block(
        text,
        "Mesh",
        "[Mesh]\n"
        "  type = FileMesh\n"
        f"  file = {mesh}\n"
        "  parallel_type = replicated\n"
        "  # Update node-face contact search as the tool moves.\n"
        "  patch_update_strategy = iteration\n"
        "  displacements = 'Ux Uy Uz'\n"
        "[]\n",
    )
    text = text.replace("'plate rod'", "'workpiece rod'")
    text = text.replace("block = 'bead'", "block = 'workpiece'")
    # The diagnostic core point must remain inside the workpiece as the tool
    # advances and the bead grows.  Sample 1 mm below the local shoulder.
    text = text.replace(
        "point = '0.0 0.050 0.020'",
        f"point = '0.0 {stage['tool_center_y_mm'] * 1.0e-3:.12g} 0.009'",
    )
    for old, new in (
        ("front_to_plate", "workpiece_top"),
        ("back_to_plate", "workpiece_base"),
        ("front_to_rod", "rod_top"),
        ("back_to_rod", "rod_bottom"),
    ):
        text = text.replace(old, new)
    # Only generated named boundaries are admitted in stage meshes.  This
    # conservative cooling BC avoids references to synthetic-mesh side names.
    text = text.replace(
        "boundary = 'workpiece_top bottom_to_plate top_to_plate left_to_plate right_to_plate left_to_rod right_to_rod bottom_to_rod top_to_rod front_to_bead left_to_bead right_to_bead top_to_bead bottom_to_bead'",
        "boundary = 'workpiece_top rod_top'",
    )
    previous = stage["previous_exodus"]
    # A remesh stage starts from its own re-zoned reference configuration.  Do
    # not interpolate Ux/Uy/Uz into the already moved geometry: that would
    # apply the travel displacement twice and reintroduce mesh inversion.
    if previous:
        for variable in ("T", "is_deposited"):
            start = text.index(f"  [{variable}]", text.index("[Variables]") if variable == "T" else text.index("[AuxVariables]"))
            end = text.index("  []", start)
            section = text[start:end]
            section = "\n".join(line for line in section.splitlines() if "initial_condition" not in line)
            text = text[:start] + section + "\n" + text[end:]
    # The physical tool position is already embedded in each stage mesh.  The
    # actuator fields are therefore local zero increments, while friction uses
    # a constant physical tool-centre coordinate for the current stage.
    text = text.replace("function = rod_motion_y", "function = rod_stage_translation_y")
    text = text.replace("function = rod_motion_z_top", "function = rod_stage_translation_z")
    text = text.replace("tool_center_y = rod_motion_y", "tool_center_y = rod_stage_center_y")
    z_function = (
        "  [rod_stage_translation_z]\n    type = ConstantFunction\n    value = 0.0\n  []\n"
        if not low_ram
        else "  [rod_stage_translation_z]\n    type = ParsedFunction\n"
             f"    expression = 'if(t < {stage['time_start_s'] + 0.1}, -2.5e-4 * (t - {stage['time_start_s']}), -2.5e-5)'\n"
             "  []\n"
    )
    function_insertion = (
        "\n  # Local frame for this re-zoned stage; geometry already contains travel/feed.\n"
        "  [rod_stage_translation_y]\n    type = ConstantFunction\n    value = 0.0\n  []\n"
        + z_function
        + "  [rod_stage_center_y]\n    type = ConstantFunction\n"
        + f"    value = {stage['tool_center_y_mm'] * 1.0e-3:.12g}\n  []\n"
    )
    functions_start = text.index("[Functions]")
    functions_end = block_end(text, functions_start)
    functions_close = text.rfind("[]", functions_start, functions_end)
    text = text[:functions_close] + function_insertion + text[functions_close:]
    text = text.replace(
        "type = TemperatureDependentHardeningStressUpdate",
        "type = RemeshTemperatureDependentHardeningStressUpdate",
    )
    if previous:
        params = (
            "    initial_effective_plastic_strain = restart_effective_plastic_strain\n"
            "    initial_plastic_strain_functions = 'restart_plastic_strain_xx restart_plastic_strain_yy restart_plastic_strain_zz restart_plastic_strain_xy restart_plastic_strain_yz restart_plastic_strain_zx'\n"
        )
        needle = "    block = 'workpiece rod'\n  []\n\n  # Multi-inelastic radial return"
        text = text.replace(needle, params + needle, 1)
        text += "\n" + transfer_fragment(Path(previous))
    text = text.replace("file_base = afsd_deposition_out", f"file_base = {stage['output_exodus'][:-2]}")
    text = re.sub(r"(start_time\s*=\s*)[^\s]+", rf"\g<1>{stage['time_start_s']}", text)
    text = re.sub(r"(end_time\s*=\s*)[^\s]+", rf"\g<1>{stage['time_end_s']}", text)
    if low_ram:
        # A small sequential direct solve is more robust than AMG/ILU for the
        # first penalty-contact increment and remains within the launcher cap.
        text = text.replace("penalty = 1.0e10", "penalty = 1.0e9")
        text = text.replace("gap_conductance = 1.0e8", "gap_conductance = 1.0e7")
        text = text.replace(
            "petsc_options_iname = '-pc_type -pc_hypre_type -ksp_gmres_restart'\n"
            "  petsc_options_value = 'hypre boomeramg 200'",
            "petsc_options_iname = '-ksp_type -pc_type'\n"
            "  petsc_options_value = 'preonly lu'",
        )
        text = text.replace("line_search = 'none'", "line_search = 'bt'")
        text = text.replace("l_tol = 1.0e-2", "l_tol = 5.0e-2")
        text = text.replace("l_max_its = 200", "l_max_its = 1")
        text = text.replace("dtmax = 0.05", "dtmax = 0.025")
        text = text.replace("    dt = 0.25", "    dt = 0.025")
    target.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("stage", type=int, help="0 for dwell, then one-based feed stage index")
    parser.add_argument("--source", type=Path, default=Path("input/deposition.i"))
    parser.add_argument("--low-ram", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.stage == 0:
        stage = manifest["dwell"]
        target = args.manifest.parent / ("dwell_low_ram.i" if args.low_ram else "dwell.i")
    else:
        try:
            stage = manifest["stages"][args.stage - 1]
        except IndexError as exc:
            raise SystemExit(f"stage must be in 0..{len(manifest['stages'])}") from exc
        suffix = "_low_ram" if args.low_ram else ""
        target = args.manifest.parent / f"stage_{args.stage:02d}{suffix}.i"
    render(args.source.resolve(), stage, target, args.low_ram)
    print(target)


if __name__ == "__main__":
    main()
