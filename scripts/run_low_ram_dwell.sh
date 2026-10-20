#!/usr/bin/env bash
# Memory-safe AFSD dwell launcher for the 8 GB laptop trial.
set -euo pipefail

cd "$(dirname "$0")/.."
ulimit -v 5767168 # 5.5 GiB: fail cleanly before the OS starts swapping/freezing.
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

input_file="${1:-remesh_stages/feed_5mm_low_ram/feed_5mm/dwell_low_ram.i}"
if [[ $# -gt 1 ]]; then
  echo "usage: $0 [input-file]" >&2
  exit 2
fi

exec ./rotating_disk_deposition-opt --n-threads=1 -i "$input_file"
