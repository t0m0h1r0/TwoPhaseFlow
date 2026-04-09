# Simulation diagnostics — reusable analysis functions extracted from experiments.
from .field_diagnostics import (
    kinetic_energy,
    kinetic_energy_periodic,
    divergence_linf,
    divergence_l2,
)
from .interface_diagnostics import (
    measure_eps_eff,
    interface_area,
    parasitic_current_linf,
    find_interface_crossing,
)

__all__ = [
    "kinetic_energy",
    "kinetic_energy_periodic",
    "divergence_linf",
    "divergence_l2",
    "measure_eps_eff",
    "interface_area",
    "parasitic_current_linf",
    "find_interface_crossing",
]
