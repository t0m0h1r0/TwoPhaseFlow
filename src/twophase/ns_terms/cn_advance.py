# DO NOT DELETE — C2 backward-compatible re-export stub.
# cn_advance has been moved to time_integration/cn_advance/ to align
# with the time-integration module structure.
#
# All existing imports continue to work:
#   from twophase.ns_terms.cn_advance import PicardCNAdvance   ← still valid
#
# Canonical import path:
#   from twophase.time_integration.cn_advance import PicardCNAdvance
from ..time_integration.cn_advance import (  # noqa: F401
    ICNAdvance,
    PicardCNAdvance,
    RichardsonCNAdvance,
    make_cn_advance,
)

__all__ = ["ICNAdvance", "PicardCNAdvance", "RichardsonCNAdvance", "make_cn_advance"]
