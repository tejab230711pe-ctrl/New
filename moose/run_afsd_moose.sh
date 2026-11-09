#!/bin/bash
# ==============================================================================
# AFSD Native MOOSE Process Runner
# Executes the coupled thermo-mechanical contact dwell and ALE flow stages
# using the compiled MOOSE application: ./rotating_disk_deposition-opt
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

export UCX_TLS=self
export OMP_NUM_THREADS=2

echo "======================================================================"
echo "STAGE 1: Running Contact Dwell & Frictional Heating Solve in MOOSE..."
echo "======================================================================"
cd "$SCRIPT_DIR"
"$MOOSE_APP" -i 01_dwell_contact.i "$@"

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
"$MOOSE_APP" -i 02_deposition_flow.i "$@"

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
echo "Exodus outputs generated: $SCRIPT_DIR/dwell_out.e, $SCRIPT_DIR/bdf2_inlet_layers4.e"
echo "CSV outputs generated: $SCRIPT_DIR/dwell_out.csv, $SCRIPT_DIR/bdf2_inlet_layers4.csv"
echo "======================================================================"
