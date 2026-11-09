#!/bin/bash
# ==============================================================================
# AFSD Native MOOSE Process Runner (MPI Parallel Execution)
# Executes the coupled thermo-mechanical contact dwell and ALE flow stages
# using MPI on 2 cores with the compiled application: ./rotating_disk_deposition-opt
# Memory safety bounds enforced for systems with <= 2 GB available RAM.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
MOOSE_APP="$REPO_ROOT/rotating_disk_deposition-opt"

if [[ ! -x "$MOOSE_APP" ]]; then
    echo "ERROR: MOOSE application executable not found: $MOOSE_APP" >&2
    exit 1
fi

NUM_CORES="${NUM_CORES:-2}"

# Prefer conda moose environment mpirun
if [[ -x "/home/teja/miniforge3/envs/moose/bin/mpirun" ]]; then
    MPIRUN="/home/teja/miniforge3/envs/moose/bin/mpirun"
elif command -v mpirun >/dev/null 2>&1; then
    MPIRUN="$(command -v mpirun)"
else
    MPIRUN=""
fi

export UCX_TLS=shm,self
export OMP_NUM_THREADS=1

if [[ -n "$MPIRUN" && "$NUM_CORES" -gt 1 ]]; then
    RUN_CMD=("$MPIRUN" -n "$NUM_CORES" "$MOOSE_APP")
    echo "Using MPI with $NUM_CORES cores: $MPIRUN -n $NUM_CORES"
else
    RUN_CMD=("$MOOSE_APP")
    echo "Running in serial mode: $MOOSE_APP"
fi

echo "======================================================================"
echo "STAGE 1: Running Contact Dwell & Frictional Heating Solve in MOOSE..."
echo "======================================================================"
cd "$SCRIPT_DIR"
"${RUN_CMD[@]}" -i 01_dwell_contact.i "$@"

# Ensure output links in moose/
mkdir -p "$REPO_ROOT/verification_runs/direct_mortar_bulk"
if [[ -f "$REPO_ROOT/verification_runs/direct_mortar_bulk/dwell.e" ]]; then
    ln -sf "$REPO_ROOT/verification_runs/direct_mortar_bulk/dwell.e" "$SCRIPT_DIR/dwell_out.e"
fi
if [[ -f "$REPO_ROOT/verification_runs/direct_mortar_bulk/dwell.csv" ]]; then
    ln -sf "$REPO_ROOT/verification_runs/direct_mortar_bulk/dwell.csv" "$SCRIPT_DIR/dwell_out.csv"
fi

echo "======================================================================"
echo "STAGE 2: Running Viscoplastic Flow & Spreading Solve in MOOSE..."
echo "======================================================================"
"${RUN_CMD[@]}" -i 02_deposition_flow.i "$@"

# Ensure output links in moose/
mkdir -p "$REPO_ROOT/verification_runs/bdf2_inlet_layers4"
if [[ -f "$REPO_ROOT/verification_runs/bdf2_inlet_layers4/flow.e" ]]; then
    ln -sf "$REPO_ROOT/verification_runs/bdf2_inlet_layers4/flow.e" "$SCRIPT_DIR/bdf2_inlet_layers4.e"
fi
if [[ -f "$REPO_ROOT/verification_runs/bdf2_inlet_layers4/flow.csv" ]]; then
    ln -sf "$REPO_ROOT/verification_runs/bdf2_inlet_layers4/flow.csv" "$SCRIPT_DIR/bdf2_inlet_layers4.csv"
fi

echo "======================================================================"
echo "MOOSE Simulation Pipeline Completed Successfully!"
echo "Exodus outputs: $SCRIPT_DIR/dwell_out.e, $SCRIPT_DIR/bdf2_inlet_layers4.e"
echo "CSV outputs:    $SCRIPT_DIR/dwell_out.csv, $SCRIPT_DIR/bdf2_inlet_layers4.csv"
echo "======================================================================"
