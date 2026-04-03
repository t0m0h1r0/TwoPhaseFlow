"""
HFE — Hermite Field Extension (§8.4).

Extends scalar fields across the interface Γ using CCD Hermite data (f, f', f''),
achieving O(h^6) accuracy without pseudo-time iteration.
"""

from .hermite_interp import hermite5_coeffs, hermite5_eval
from .field_extension import HermiteFieldExtension

__all__ = ["hermite5_coeffs", "hermite5_eval", "HermiteFieldExtension"]
