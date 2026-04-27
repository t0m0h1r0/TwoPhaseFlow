"""ch13 experiment handlers (registered via @register_handler).

Handler types:
  capillary_wave  — ch13 capillary-wave NS simulation (ns_simulation.py)
  circle          — ch13 rising-bubble NS simulation (ns_simulation.py)
"""

from __future__ import annotations

# Side-effect import: registers ch13 NS-simulation handlers.
from . import ns_simulation  # noqa: F401
