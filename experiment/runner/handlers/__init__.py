"""ch14 experiment handlers (registered via @register_handler).

Handler types:
  capillary_wave  — sinusoidal-interface NS simulation (ns_simulation.py).
                    Used for capillary-wave and Rayleigh-Taylor benchmarks.
  circle          — bubble/droplet NS simulation (ns_simulation.py).
                    Used for the rising-bubble benchmark.
"""

from __future__ import annotations

# Side-effect import: registers ch14 NS-simulation handlers.
from . import ns_simulation  # noqa: F401
