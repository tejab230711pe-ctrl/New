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
import subprocess
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


def source_state_variables(previous: Path) -> tuple[str, bool]:
    """Return fields safely present in an existing Exodus result.

    The first completed dwell on this laptop predates full tensor output and
    has only the scalar J2 history.  Preserve that costly valid dwell by
    transferring scalar hardening alone for its next stage.  Later stages,
    which emit all six components, automatically use the full tensor state.
    """
    try:
        symbols = subprocess.run(
            ["strings", str(previous)], check=True, capture_output=True, text=True
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"cannot inspect Exodus state file {previous}: {exc}") from exc
    has_tensor = all(name in symbols for name in PLASTIC_COMPONENTS.split())
    names = ["T", "is_deposited", "effective_plastic_strain"]
    if has_tensor:
        names.extend(PLASTIC_COMPONENTS.split())
    return " ".join(names), has_tensor


def transfer_fragment(
    previous: Path,
    history_blocks: str,
    source_history_blocks: str,
    state_variables: str,
    has_tensor: bool,
) -> str:
    functions = []
    function_variables = ["effective_plastic_strain"]
    if has_tensor:
        function_variables.extend(PLASTIC_COMPONENTS.split())
    for variable in function_variables:
        functions.extend(
            [f"  [restart_{variable}]", "    type = SolutionFunction", "    solution = remesh_source", f"    from_variable = {variable}", "  []"]
        )
    ics = []
    outside_values = {"T": "293.15", "is_deposited": "0.0"}
    for variable in ("T", "is_deposited"):
        ics.extend(
            [
                f"  [restart_{variable}]",
                "    type = RemeshSolutionIC",
                "    solution_uo = remesh_source",
                f"    variable = {variable}",
                f"    from_variable = {variable}",
                f"    transfer_blocks = '{history_blocks}'",
                f"    from_subdomains = '{source_history_blocks}'",
                "    weighting_type = average",
                f"    outside_value = {outside_values[variable]}",
                "  []",
            ]
        )
    return "\n".join(
        [
            "# Generated Exodus-to-remesh transfer. Do not edit by hand.",
            "[UserObjects]",
            "  [remesh_source]",
            "    type = SolutionUserObject",
            f"    mesh = {previous.resolve()}",
            f"    system_variables = '{state_variables}'",
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


def render(
    source: Path, stage: dict, target: Path, low_ram: bool = False, low_ram_dt: float = 0.005
) -> None:
    text = source.read_text(encoding="utf-8")
    mesh = Path(stage["mesh"]).resolve()
    text = replace_top_level_block(
        text,
        "Mesh",
        "[Mesh]\n"
        "  [file_mesh]\n"
        "    type = FileMeshGenerator\n"
        f"    file = {mesh}\n"
        "  []\n"
        # A distributed mesh is essential when MPI is used: replicated meshes
        # make every rank retain the complete model, so two ranks cost almost
        # twice the RAM without reducing the per-rank contact work.
        "  parallel_type = distributed\n"
        # Let MOOSE rebuild the contact-search patch only when the relative
        # motion requires it.  This preserves the contact formulation while
        # avoiding a full locator rebuild on every nonlinear iteration.
        "  patch_update_strategy = auto\n"
        "  displacements = 'Ux Uy Uz'\n"
        "[]\n",
    )
    # Each mesh has only the blocks which physically exist at that rezone.
    # Stage 0 has plate+rod; later stages add fresh material and, after the
    # first feed increment, previously deposited material.
    history_blocks = "plate" + (" deposit" if stage["previous_bead_length_mm"] > 1.0e-9 else "")
    virgin_blocks = "rod" + (" fresh_deposit" if stage["bead_length_mm"] > stage["previous_bead_length_mm"] + 1.0e-9 else "")
    all_blocks = f"{history_blocks} {virgin_blocks}"
    text = text.replace("'plate rod'", f"'{all_blocks}'")
    text = text.replace("block = 'bead'", f"block = '{'fresh_deposit' if 'fresh_deposit' in virgin_blocks else 'rod'}'")
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
    # The stage mesh is generated at its end position.  Move its rod reference
    # configuration backward at the beginning of the stage, then translate it
    # continuously to that end position.  This preserves the fixed rezone mesh
    # while making the actual contact and friction source follow the CNC Y path.
    text = text.replace("function = rod_motion_y", "function = rod_stage_translation_y")
    text = text.replace("function = rod_motion_z_top", "function = rod_stage_translation_z")
    text = text.replace("tool_center_y = rod_motion_y", "tool_center_y = rod_stage_center_y")
    # The broad BC substitutions above must not alter diagnostic functions:
    # these report the absolute CNC program, not the local remesh-frame motion.
    text = text.replace(
        "  [command_machine_X_mm]\n"
        "    type = FunctionValuePostprocessor\n"
        "    function = rod_stage_translation_y",
        "  [command_machine_X_mm]\n"
        "    type = FunctionValuePostprocessor\n"
        "    function = rod_motion_y",
    )
    text = text.replace(
        "  [command_quill_Z_mm]\n"
        "    type = FunctionValuePostprocessor\n"
        "    function = rod_stage_translation_z",
        "  [command_quill_Z_mm]\n"
        "    type = FunctionValuePostprocessor\n"
        "    function = rod_motion_z_top",
    )
    stage_end_y_m = stage["tool_center_y_mm"] * 1.0e-3
    stage_start_y_m = (12.5 + stage["previous_bead_length_mm"]) * 1.0e-3
    stage_traverse_m = stage_end_y_m - stage_start_y_m
    stage_duration_s = stage["time_end_s"] - stage["time_start_s"]
    stage_speed_mps = stage_traverse_m / stage_duration_s if stage_duration_s else 0.0
    stage_start_s = stage["time_start_s"]
    stage_end_s = stage["time_end_s"]
    if stage["index"] == 0:
        y_translation = "  [rod_stage_translation_y]\n    type = ConstantFunction\n    value = 0.0\n  []\n"
        center_y = (
            "  [rod_stage_center_y]\n    type = ConstantFunction\n"
            f"    value = {stage_end_y_m:.12g}\n  []\n"
        )
    else:
        y_translation = (
            "  [rod_stage_translation_y]\n    type = ParsedFunction\n"
            "    # Reference mesh is at stage end; start at prior CNC Y and traverse forward.\n"
            f"    expression = 'if(t <= {stage_start_s:.12g}, {-stage_traverse_m:.12g}, if(t < {stage_end_s:.12g}, {-stage_traverse_m:.12g} + {stage_speed_mps:.12g} * (t - {stage_start_s:.12g}), 0.0))'\n"
            "  []\n"
        )
        center_y = (
            "  [rod_stage_center_y]\n    type = ParsedFunction\n"
            f"    expression = 'if(t <= {stage_start_s:.12g}, {stage_start_y_m:.12g}, if(t < {stage_end_s:.12g}, {stage_start_y_m:.12g} + {stage_speed_mps:.12g} * (t - {stage_start_s:.12g}), {stage_end_y_m:.12g}))'\n"
            "  []\n"
        )
    # G04 P4.0 is a true position hold.  Do not introduce an artificial
    # low-RAM plunge: it would turn the dwell into a hidden force ramp and
    # invalidate comparison with the measured axial-force trace.
    z_function = "  [rod_stage_translation_z]\n    type = ConstantFunction\n    value = 0.0\n  []\n"
    function_insertion = (
        "\n  # Local frame for this re-zoned stage; mesh is the stage-end reference state.\n"
        + y_translation
        + z_function
        + center_y
    )
    functions_start = text.index("[Functions]")
    functions_end = block_end(text, functions_start)
    functions_close = text.rfind("[]", functions_start, functions_end)
    text = text[:functions_close] + function_insertion + text[functions_close:]
    # Literal 1200 RPM spindle rotation.  Because the stage mesh is created at
    # its end centre, y - stage_end_y_m is its local shoulder coordinate.  At
    # each rezone the circular shoulder can restart its angular reference
    # without changing contact geometry; its physical tangential velocity and
    # Coulomb slip are continuous in magnitude.
    theta = f"125.663706143592 * (t - {stage_start_s:.12g})"
    spin_ux = (
        "  [rod_spin_ux]\n    type = ParsedFunction\n"
        f"    expression = 'x * (cos({theta}) - 1.0) - (y - {stage_end_y_m:.12g}) * sin({theta})'\n"
        "  []"
    )
    spin_uy = (
        "  [rod_spin_uy]\n    type = ParsedFunction\n"
        f"    expression = 'x * sin({theta}) + (y - {stage_end_y_m:.12g}) * (cos({theta}) - 1.0) + ({stage_start_y_m:.12g} + {stage_speed_mps:.12g} * (t - {stage_start_s:.12g}) - {stage_end_y_m:.12g})'\n"
        "  []"
    )
    for name, replacement in (("rod_spin_ux", spin_ux), ("rod_spin_uy", spin_uy)):
        begin = text.index(f"  [{name}]\n", text.index("[Functions]"))
        finish = text.index("  []", begin) + len("  []")
        text = text[:begin] + replacement + text[finish:]
    text = text.replace(
        "type = TemperatureDependentHardeningStressUpdate",
        "type = RemeshTemperatureDependentHardeningStressUpdate",
    )
    if previous:
        # State is transferred only into geometry that was present in the
        # preceding stage.  Fresh bead material and the newly supplied rod
        # deliberately start virgin; sampling Exodus there caused the prior
        # out-of-domain failure at the stage boundary.
        state_variables, has_tensor_state = source_state_variables(Path(previous))
        params = "    initial_effective_plastic_strain = restart_effective_plastic_strain\n"
        if has_tensor_state:
            params += (
                "    initial_plastic_strain_functions = 'restart_plastic_strain_xx restart_plastic_strain_yy restart_plastic_strain_zz restart_plastic_strain_xy restart_plastic_strain_yz restart_plastic_strain_zx'\n"
            )
        else:
            params += (
                "    # Legacy dwell source has scalar J2 history only; tensor state starts\n"
                "    # at zero for this one rezone, while hardening is preserved exactly.\n"
            )
        material_start = text.index("  [temp_dep_hardening]\n", text.index("[Materials]"))
        material_end = text.index("  []\n\n  # Multi-inelastic radial return", material_start) + len("  []")
        material = text[material_start:material_end]
        history_material = material.replace("[temp_dep_hardening]", "[temp_dep_hardening_history]", 1)
        history_material = history_material.replace(f"block = '{all_blocks}'", f"block = '{history_blocks}'", 1)
        history_material = history_material.replace(f"    block = '{history_blocks}'", params + f"    block = '{history_blocks}'", 1)
        virgin_material = material.replace("[temp_dep_hardening]", "[temp_dep_hardening_virgin]", 1)
        virgin_material = virgin_material.replace(f"block = '{all_blocks}'", f"block = '{virgin_blocks}'", 1)
        text = text[:material_start] + history_material + "\n\n" + virgin_material + text[material_end:]

        radial_start = text.index("  [radial_return_stress]\n", text.index("[Materials]"))
        radial_end = text.index("  []\n\n  # Stress : plastic-strain-rate", radial_start) + len("  []")
        radial = text[radial_start:radial_end]
        history_radial = radial.replace("[radial_return_stress]", "[radial_return_stress_history]", 1)
        history_radial = history_radial.replace("inelastic_models = 'temp_dep_hardening'", "inelastic_models = 'temp_dep_hardening_history'", 1)
        history_radial = history_radial.replace(f"block = '{all_blocks}'", f"block = '{history_blocks}'", 1)
        virgin_radial = radial.replace("[radial_return_stress]", "[radial_return_stress_virgin]", 1)
        virgin_radial = virgin_radial.replace("inelastic_models = 'temp_dep_hardening'", "inelastic_models = 'temp_dep_hardening_virgin'", 1)
        virgin_radial = virgin_radial.replace(f"block = '{all_blocks}'", f"block = '{virgin_blocks}'", 1)
        text = text[:radial_start] + history_radial + "\n\n" + virgin_radial + text[radial_end:]
        # The predecessor's just-created bead is named fresh_deposit.  At the
        # next rezone it becomes deposit, so source and target block names are
        # intentionally different from stage two onward.
        if stage["index"] == 1:
            source_history_blocks = "plate"
        elif stage["index"] == 2:
            source_history_blocks = "plate fresh_deposit"
        else:
            source_history_blocks = "plate deposit fresh_deposit"
        text += "\n" + transfer_fragment(
            Path(previous), history_blocks, source_history_blocks, state_variables, has_tensor_state
        )
    text = text.replace("file_base = afsd_deposition_out", f"file_base = {stage['output_exodus'][:-2]}")
    text = re.sub(r"(start_time\s*=\s*)[^\s]+", rf"\g<1>{stage['time_start_s']}", text)
    text = re.sub(r"(end_time\s*=\s*)[^\s]+", rf"\g<1>{stage['time_end_s']}", text)
    if low_ram:
        # A small sequential direct solve is more robust than AMG/ILU for the
        # first penalty-contact increment and remains within the launcher cap.
        text = text.replace("penalty = 1.0e10", "penalty = 1.0e7")
        text = text.replace("gap_conductance = 1.0e8", "gap_conductance = 1.0e7")
        text = text.replace(
            "petsc_options_iname = '-pc_type -pc_hypre_type -ksp_gmres_restart'\n"
            "  petsc_options_value = 'hypre boomeramg 200'",
            "petsc_options_iname = '-ksp_type -pc_type'\n"
            "  petsc_options_value = 'preonly lu'",
        )
        # Assemble the contact Jacobian.  Matrix-free Newton is inexpensive
        # before contact, but stalls once the normal constraint activates.
        text = text.replace("solve_type = PJFNK", "solve_type = NEWTON")
        text = text.replace("nl_rel_tol = 1.0e-3", "nl_rel_tol = 5.0e-3")
        text = text.replace("line_search = 'none'", "line_search = 'bt'")
        text = text.replace("l_tol = 1.0e-2", "l_tol = 5.0e-2")
        # Active contact needs a converged linear correction; one iteration
        # only works while the bodies are not touching.
        text = text.replace("l_max_its = 200", "l_max_its = 25")
        text = text.replace("dtmax = 0.05", f"dtmax = {low_ram_dt:.12g}")
        text = text.replace("    dt = 0.25", f"    dt = {low_ram_dt:.12g}")
        # Each remesh stage needs only its final Exodus state: it is the input
        # to the next re-zoned mesh.  Writing every 5 ms retains a large
        # in-memory Exodus history and eventually triggers the OOM killer on
        # the 8 GB laptop.  Keep CSV at every accepted step for lightweight
        # time histories and diagnostics.
        exodus_end = f"    file_base = {stage['output_exodus'][:-2]}\n  []\n  [csv]"
        exodus_final_only = (
            f"    file_base = {stage['output_exodus'][:-2]}\n"
            "    execute_on = FINAL\n"
            "  []\n"
            "  [csv]"
        )
        if exodus_end not in text:
            raise ValueError("could not set final-only Exodus output in low-RAM deck")
        text = text.replace(exodus_end, exodus_final_only, 1)
    target.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("stage", type=int, help="0 for dwell, then one-based feed stage index")
    parser.add_argument("--source", type=Path, default=Path("input/deposition.i"))
    parser.add_argument("--low-ram", action="store_true")
    parser.add_argument(
        "--low-ram-dt",
        type=float,
        default=0.005,
        help="Initial and maximum time step for a low-RAM deck (s; default: 0.005).",
    )
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
    if args.low_ram_dt <= 0.0:
        raise SystemExit("--low-ram-dt must be positive")
    render(args.source.resolve(), stage, target, args.low_ram, args.low_ram_dt)
    print(target)


if __name__ == "__main__":
    main()
