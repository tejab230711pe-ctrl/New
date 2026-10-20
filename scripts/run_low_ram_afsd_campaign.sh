#!/usr/bin/env bash
# Run the complete 5 mm AA5083 AFSD campaign on an 8 GB laptop.
# Stages are rendered immediately before use so each reads the latest Exodus
# result from its predecessor.  Stop on the first error; do not run stages in
# parallel because each stage depends on the previous state-transfer file.
set -euo pipefail

cd "$(dirname "$0")/.."

trial_root="remesh_stages/feed_5mm_low_ram/feed_5mm"
manifest="$trial_root/manifest.json"
start_stage="${1:-0}"

if [[ ! -f "$manifest" ]]; then
  echo "Missing $manifest. Run ./scripts/make_low_ram_afsd_trial.sh first." >&2
  exit 2
fi
if [[ ! "$start_stage" =~ ^[0-7]$ ]]; then
  echo "usage: $0 [starting-stage: 0..7]" >&2
  exit 2
fi

run_stage() {
  local index="$1"
  local deck

  python3 scripts/render_afsd_remesh_stage.py "$manifest" "$index" --low-ram
  if [[ "$index" == 0 ]]; then
    deck="$trial_root/dwell_low_ram.i"
    echo "Starting dwell: physical time 0 to 4 s"
  else
    printf -v deck '%s/stage_%02d_low_ram.i' "$trial_root" "$index"
    echo "Starting re-mesh stage $index of 7"
  fi
  ./scripts/run_low_ram_dwell.sh "$deck"
}

if [[ "$start_stage" == 0 ]]; then
  run_stage 0
  start_stage=1
fi
for ((index=start_stage; index<=7; index++)); do
  run_stage "$index"
done

echo "AFSD campaign completed. Results are in $trial_root/*.e and $trial_root/*.csv"
