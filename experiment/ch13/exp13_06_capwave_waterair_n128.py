#!/usr/bin/env python3
"""
exp13_06_capwave_waterair_n128.py — Wrapper for ch13 unified runner

Remote-compatible wrapper for ch13/run.py with config ch13_capillary_water_air_alpha2_n128.
Enables: make cycle EXP=experiment/ch13/exp13_06_capwave_waterair_n128.py

Background: WIKI-X-020 (Ridge-Eikonal → IIM chain)
            WIKI-X-021 (J³ scaling at N=128)
            WIKI-X-022 (R-1.5 BF-consistent architecture)

Physics: Water-air (ρ_l=1000, ρ_g=1.2, σ=0.072)
Grid: N=128, non-uniform (α=2.0)
Method: Ridge-Eikonal + GFM + HFE + IIM + FCCD + R-1.5 CSF
"""

import sys
import os

# Add ch13 directory to path so run.py can be imported
ch13_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ch13_dir)

# Import and delegate to run.py
from run import main

if __name__ == "__main__":
    # Override sys.argv to inject config name
    sys.argv = ["run.py", "ch13_capillary_water_air_alpha2_n128"]
    main()
