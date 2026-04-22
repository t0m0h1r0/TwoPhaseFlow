#!/usr/bin/env python3
"""Thin launcher — EXP= target for Makefile.

Usage:
    make run  EXP=experiment/run.py ARGS="--config exp11_01_ccd_convergence"
    make plot EXP=experiment/run.py ARGS="--config exp11_01_ccd_convergence"
    make run  EXP=experiment/run.py ARGS="--all"
"""
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent      # experiment/
SRC  = ROOT.parent / "src"

sys.path.insert(0, str(SRC))     # twophase library
sys.path.insert(0, str(ROOT))    # runner package

from runner.main import main  # noqa: E402

if __name__ == "__main__":
    main()
