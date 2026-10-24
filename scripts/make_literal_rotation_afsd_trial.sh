#!/usr/bin/env bash
# Create literal 1200 RPM Coulomb-contact AFSD inputs; does not build or run.
set -euo pipefail

cd "$(dirname "$0")/.."
trial_root="remesh_stages/feed_5mm_literal_rotation/feed_5mm"

python3 scripts/create_afsd_remesh_stages.py \
  --feed-increment-mm 5 \
  --output-dir remesh_stages/feed_5mm_literal_rotation \
  --mesh-min-mm 2 \
  --mesh-max-mm 4 \
  --initial-interference-mm 0.00515 \
  --initial-clearance-mm 0 \
  --run-gmsh

python3 scripts/render_afsd_remesh_stage.py \
  "$trial_root/manifest.json" 0 --low-ram --low-ram-dt 0.000025

echo "Created literal-rotation campaign in $trial_root (dt = 0.000025 s)."
