#!/usr/bin/env bash
# Create the conservative 5 mm AFSD remesh trial for an 8 GB laptop.
set -euo pipefail

cd "$(dirname "$0")/.."
# Calibrated from the 5 ms contact smoke test: 1.0 um produced 0.256 kN,
# while the measured dwell mean is 0.586 kN.  This remains a small elastic
# displacement, not a prescribed force.
python3 scripts/create_afsd_remesh_stages.py \
  --feed-increment-mm 5 \
  --output-dir remesh_stages/feed_5mm_low_ram \
  --mesh-min-mm 2 \
  --mesh-max-mm 4 \
  --initial-interference-mm 0.00515 \
  --initial-clearance-mm 0 \
  --run-gmsh
trial_root=remesh_stages/feed_5mm_low_ram/feed_5mm
python3 scripts/render_afsd_remesh_stage.py \
  "$trial_root/manifest.json" 0 --low-ram

# The stabilization deck covers one 5 ms increment.  It proves contact convergence
# before the 4 s dwell is attempted and uses a distinct output base.
sed \
  -e 's/end_time = 4.0/end_time = 0.005/' \
  -e 's#file_base = remesh_stages/feed_5mm_low_ram/dwell#file_base = remesh_stages/feed_5mm_low_ram/dwell_contact_smoke#g' \
  "$trial_root/dwell_low_ram.i" \
  > "$trial_root/dwell_contact_smoke.i"

echo "Created low-RAM mesh and decks in $trial_root"
