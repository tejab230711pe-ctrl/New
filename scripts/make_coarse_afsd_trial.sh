#!/usr/bin/env bash
# Build a separate 1 s diagnostic campaign without overwriting production results.
set -euo pipefail

cd "$(dirname "$0")/.."

trial_root="remesh_stages/feed_5mm_dt1s/feed_5mm"
python3 scripts/create_afsd_remesh_stages.py \
  --feed-increment-mm 5 \
  --output-dir remesh_stages/feed_5mm_dt1s \
  --mesh-min-mm 2 \
  --mesh-max-mm 4 \
  --initial-interference-mm 0.00515 \
  --initial-clearance-mm 0 \
  --run-gmsh

# Only the dwell deck is valid before a predecessor Exodus result exists.
# The campaign renderer creates every traverse deck just after its predecessor finishes.
python3 scripts/render_afsd_remesh_stage.py \
  "$trial_root/manifest.json" 0 --low-ram --low-ram-dt 1.0

echo "Created isolated 1 s diagnostic mesh and dwell deck in $trial_root"
