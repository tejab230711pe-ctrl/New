#!/usr/bin/env bash
# Validate only the sharp-interface ALE flow deck. It neither builds nor runs.
set -euo pipefail

cd "$(dirname "$0")/.."
./rotating_disk_deposition-opt -i input/afsd_ale_flow_stage.i --check-input
