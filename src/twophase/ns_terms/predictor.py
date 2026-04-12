# DO NOT DELETE — C2 backward-compatible re-export stub.
# Predictor has been moved to time_integration/ab2_predictor.py to align
# with the time-integration module structure (alongside IMEXPredictorARK3).
#
# All existing imports continue to work:
#   from twophase.ns_terms.predictor import Predictor   ← still valid
#
# Canonical import path:
#   from twophase.time_integration.ab2_predictor import Predictor
from ..time_integration.ab2_predictor import Predictor  # noqa: F401

__all__ = ["Predictor"]
