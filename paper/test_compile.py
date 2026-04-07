#!/usr/bin/env python3
import subprocess
import os

os.chdir("/Users/tomohiro/Downloads/TwoPhaseFlow/paper")
result = subprocess.run(["python3", "main.py"], capture_output=True, text=True)
print(result.stdout[-2000:] if result.stdout else "No output")
print(result.stderr[-1000:] if result.stderr else "No errors")
