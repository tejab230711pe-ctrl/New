#!/usr/bin/env python3
"""
AFSD 3D Dynamic Deposition Animation & Simulation Video Generator
-----------------------------------------------------------------
Publication-Quality Simulation Video Suite (Refined Q1 Journal Standard)
based on `process_schematic.py`:
  - 3D Isometric Process Simulation (`afsd_simulation_isometric.mp4`, `.gif`)
  - Close-up Tool & Flash Collar Dynamics (`afsd_simulation_closeup.mp4`, `.gif`)
  - Scientific Multi-Viewport Engineering Dashboard (`afsd_simulation_multiview.mp4`, `.gif`)

Run via:
  python3 scripts/generate_3d_animation.py
"""

import os
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from generate_simulation_videos import generate_all_simulation_videos

if __name__ == '__main__':
    generate_all_simulation_videos(num_frames=160)

