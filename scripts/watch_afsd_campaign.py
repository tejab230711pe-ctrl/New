#!/usr/bin/env python3
"""Low-memory one-second live/replay monitor for a staged AFSD campaign.

It reads only the final valid CSV row written by MOOSE.  Therefore it can be
run in a second terminal while the solver runs without opening Exodus files,
adding solver memory pressure, or changing the simulation.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path


DISPLAY_FIELDS = (
    ("time", "time [s]", "{:7.3f}"),
    ("command_machine_X_mm", "machine X / sim-Y [mm]", "{:8.3f}"),
    ("command_quill_Z_mm", "quill Z [mm]", "{:8.3f}"),
    ("consumed_length_mm", "rod consumed [mm]", "{:8.3f}"),
    ("rod_height_mm", "rod height [mm]", "{:8.3f}"),
    ("force_kN", "axial force [kN]", "{:8.3f}"),
    ("friction_power_kW", "friction power [kW]", "{:8.3f}"),
    ("T_max", "maximum T [K]", "{:8.2f}"),
    ("T_core", "core T [K]", "{:8.2f}"),
    ("max_contact_pressure", "contact pressure [MPa]", "{:8.3f}"),
)


def csv_files(root: Path) -> list[Path]:
    """Return only MOOSE stage histories, in physical campaign order."""
    ordered = [root / "dwell.csv"]
    ordered.extend(root / f"stage_{number:02d}.csv" for number in range(1, 8))
    return [path for path in ordered if path.is_file()]


def read_rows(path: Path) -> list[dict[str, str]]:
    """Read complete rows only; an active MOOSE write can leave a partial tail."""
    try:
        with path.open(newline="", encoding="utf-8") as stream:
            return list(csv.DictReader(stream))
    except (OSError, UnicodeDecodeError, csv.Error):
        return []


def number(row: dict[str, str], field: str) -> float | None:
    try:
        return float(row[field])
    except (KeyError, TypeError, ValueError):
        return None


def stage_name(path: Path) -> str:
    return "DWELL" if path.stem == "dwell" else path.stem.upper()


def print_header() -> None:
    print("\nAFSD live monitor (one-second refresh; Ctrl-C stops monitor only)")
    print("stage       time[s]  sim-Y[mm]  quill-Z[mm]  consumed[mm]  rod-H[mm]"
          "  Fz[kN]  Pfric[kW]  Tmax[K]  Tcore[K]  pmax[MPa]")


def print_row(path: Path, row: dict[str, str]) -> None:
    values = []
    for field, _label, fmt in DISPLAY_FIELDS:
        value = number(row, field)
        if value is not None and field == "max_contact_pressure":
            value /= 1.0e6
        values.append(fmt.format(value) if value is not None else "      n/a")
    print(f"{stage_name(path):<10} " + "  ".join(values), flush=True)


def replay(root: Path, interval: float) -> int:
    rows: list[tuple[Path, dict[str, str]]] = []
    for path in csv_files(root):
        rows.extend((path, row) for row in read_rows(path))
    rows.sort(key=lambda item: number(item[1], "time") or -1.0)
    if not rows:
        print(f"No stage CSV files found beneath {root}", file=sys.stderr)
        return 1
    print_header()
    for path, row in rows:
        print_row(path, row)
        time.sleep(interval)
    return 0


def watch(root: Path, interval: float) -> int:
    print_header()
    last_signature: tuple[Path, str, int] | None = None
    try:
        while True:
            files = csv_files(root)
            if not files:
                print(f"waiting for CSV output in {root}", flush=True)
            else:
                newest = files[-1]
                rows = read_rows(newest)
                if rows:
                    row = rows[-1]
                    signature = (newest, row.get("time", ""), len(rows))
                    if signature != last_signature:
                        print_row(newest, row)
                        last_signature = signature
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nMonitor stopped; the solver continues running.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "campaign_dir", nargs="?", type=Path,
        default=Path("remesh_stages/feed_5mm_dt1s_z75/feed_5mm"),
        help="directory containing dwell.csv and stage_01.csv ... stage_07.csv",
    )
    parser.add_argument("--replay", action="store_true",
                        help="replay all completed CSV rows instead of watching")
    parser.add_argument("--interval", type=float, default=1.0,
                        help="refresh/replay interval in seconds (default: 1)")
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval must be positive")
    return replay(args.campaign_dir, args.interval) if args.replay else watch(args.campaign_dir, args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
