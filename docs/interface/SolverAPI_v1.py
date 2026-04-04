"""
SolverAPI v1 — L→E Interface Contract Template
GENERATED — do NOT edit directly. Edit prompts/meta/*.md and regenerate.
Status: {pending} — awaiting L-Domain pipeline execution

This contract defines the API surface that E-Domain (ExperimentRunner)
may invoke from L-Domain (Core Library). Only methods listed here are
part of the contract; internal implementation details are NOT accessible.

IF-AGREEMENT:
  feature:      "Solver API v1 — simulation entry points"
  domain:       Library → Experiment
  gatekeeper:   CodeWorkflowCoordinator
  specialist:   ExperimentRunner
  inputs:
    - src/twophase/: solver implementation (L-Domain)
  outputs:
    - experiment/: raw simulation results
    - results/: validated outputs
  success_criteria: "All EXP-02 sanity checks (SC-1 through SC-4) PASS"
  created_at:   {pending}
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class SolverAPIv1(ABC):
    """Abstract interface for two-phase flow solver.

    E-Domain agents invoke ONLY these methods.
    Internal solver mechanics (src/core/) are invisible to E-Domain.
    """

    @abstractmethod
    def setup(self, config: Dict[str, Any]) -> None:
        """Initialize solver with experiment configuration."""
        ...

    @abstractmethod
    def run(self, n_steps: int) -> Dict[str, Any]:
        """Execute simulation for n_steps and return result package."""
        ...

    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """Return current simulation state for sanity checks."""
        ...
