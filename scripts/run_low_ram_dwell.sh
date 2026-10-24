#!/usr/bin/env bash
# Memory-safe AFSD dwell launcher for the 8 GB laptop trial.
set -euo pipefail

cd "$(dirname "$0")/.."
# This is a secondary per-process guard.  The cgroup below is the effective
# RSS limit: virtual-address limits alone do not prevent PETSc/Exodus from
# reserving address space that later turns into real memory pressure.
ulimit -v 4456448 # 4.25 GiB virtual-address ceiling.
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

input_file="${1:-remesh_stages/feed_5mm_literal_rotation/feed_5mm/dwell_low_ram.i}"
if [[ $# -gt 1 ]]; then
  echo "usage: $0 [input-file]" >&2
  exit 2
fi

# The generated AFSD decks use a distributed mesh, so up to four MPI ranks can
# share the model.  The executable links MPICH from the MOOSE environment, so
# do not use Ubuntu's default OpenMPI launcher (it fails before model setup
# with a PMI mismatch).
mpi_ranks="${AFSD_MPI_RANKS:-2}"
if [[ ! "$mpi_ranks" =~ ^[1-4]$ ]]; then
  echo "AFSD_MPI_RANKS must be an integer from 1 to 4." >&2
  exit 2
fi
mpich_launcher="${AFSD_MPICH_LAUNCHER:-/home/teja/miniforge3/envs/moose/bin/mpiexec.hydra}"
if [[ "$mpi_ranks" == 1 ]]; then
  solver=(./rotating_disk_deposition-opt --n-threads=1 -i "$input_file")
else
  if [[ ! -x "$mpich_launcher" ]]; then
    echo "Matching MPICH launcher not found: $mpich_launcher" >&2
    exit 2
  fi
  solver=("$mpich_launcher" -n "$mpi_ranks" ./rotating_disk_deposition-opt --n-threads=1 -i "$input_file")
fi

# Keep a solver overrun from exhausting the desktop.  A systemd user scope
# limits resident memory, unlike ulimit -v, and returns a normal nonzero exit
# rather than allowing global OOM pressure and a frozen laptop.
if command -v systemd-run >/dev/null && systemctl --user is-system-running >/dev/null 2>&1; then
  echo "AFSD memory guard: MemoryMax=4G, MemorySwapMax=1G, ${mpi_ranks} MPI rank(s), one thread/rank."
  exec systemd-run --user --scope --quiet --collect \
    -p MemoryMax=4G \
    -p MemorySwapMax=1G \
    "${solver[@]}"
fi

echo "WARNING: systemd user scope unavailable; using only the 4.25 GiB virtual-memory guard." >&2
exec "${solver[@]}"
