"""PPE parsing helpers for run-section config handling."""

from __future__ import annotations

from .config_sections import validate_choice

_PPE_DISCRETIZATION_SOLVERS = {
    ("fd", "direct"): "fd_direct",
    ("fd", "iterative"): "fd_iterative",
    ("fvm", "iterative"): "fvm_iterative",
    ("fvm", "direct"): "fvm_direct",
    ("fccd", "iterative"): "fccd_iterative",
}
_PPE_SOLVER_KINDS = ("iterative", "direct", "defect_correction")
_PPE_ITERATION_METHODS = ("gmres", "cg")
_PPE_PRECONDITIONERS = ("jacobi", "line_pcr", "none")


def parse_ppe_solver_config(
    solver_cfg: dict,
    path: str,
    discretization: str = "fvm",
    discretization_path: str = "projection.poisson.operator.discretization",
) -> tuple[str, str | None, str, float, int, int | None, str, int | None, float, bool, int, float, float]:
    kind = validate_choice(solver_cfg["kind"], _PPE_SOLVER_KINDS, f"{path}.kind")
    if kind != "defect_correction" and "base_solver" in solver_cfg:
        raise ValueError(
            f"{path}.base_solver is only valid when {path}.kind='defect_correction'"
        )
    dc_enabled = kind == "defect_correction"
    dc_max_iterations = 0
    dc_tolerance = 0.0
    dc_relaxation = 1.0
    effective_solver_cfg = solver_cfg
    effective_kind = kind
    effective_path = path
    base_discretization = discretization
    if dc_enabled:
        allowed_dc_keys = {"kind", "corrections", "base_solver"}
        extra_keys = sorted(set(solver_cfg) - allowed_dc_keys)
        if extra_keys:
            raise ValueError(
                f"{path}.kind='defect_correction' does not accept base-solver "
                f"options at the DC level: {extra_keys}"
            )
        if "base_solver" not in solver_cfg:
            raise ValueError(f"{path}.kind='defect_correction' requires {path}.base_solver")
        effective_solver_cfg = solver_cfg["base_solver"]
        effective_kind = validate_choice(
            effective_solver_cfg["kind"],
            ("iterative", "direct"),
            f"{path}.base_solver.kind",
        )
        if "base_solver" in effective_solver_cfg:
            raise ValueError(f"{path}.base_solver.base_solver is not allowed")
        effective_path = f"{path}.base_solver"
        base_discretization = validate_choice(
            effective_solver_cfg.get(
                "discretization",
                "fd" if discretization == "fccd" else discretization,
            ),
            _PPE_DISCRETIZATION_SOLVERS_BY_KIND,
            f"{effective_path}.discretization",
        )
        if base_discretization == "fvm" and effective_kind == "direct":
            raise ValueError(
                f"{effective_path}.discretization='fvm' with kind='direct' is "
                "not a valid L_L correction solver for defect_correction; use "
                "discretization='fd'."
            )
        if base_discretization == discretization and effective_kind == "iterative":
            raise ValueError(
                f"{effective_path}.discretization must select a lower-order L_L "
                "operator for defect_correction; using the same operator would "
                "bypass the paper's L_H residual / L_L correction contract."
            )
        corrections = solver_cfg.get("corrections", {}) or {}
        dc_max_iterations = int(corrections.get("max_iterations", 3))
        dc_tolerance = float(corrections.get("tolerance", 1.0e-8))
        dc_relaxation = float(corrections.get("relaxation", 1.0))
        if dc_max_iterations <= 0:
            raise ValueError(f"{path}.corrections.max_iterations must be > 0")
        if dc_tolerance <= 0.0:
            raise ValueError(f"{path}.corrections.tolerance must be > 0")
        if dc_relaxation <= 0.0:
            raise ValueError(f"{path}.corrections.relaxation must be > 0")
    target_kind = "iterative" if dc_enabled else effective_kind
    solver_key = (discretization, target_kind)
    if solver_key not in _PPE_DISCRETIZATION_SOLVERS:
        raise ValueError(
            f"{discretization_path}={discretization!r} does not support "
            f"{effective_path}.kind={target_kind!r}"
        )
    ppe_solver = _PPE_DISCRETIZATION_SOLVERS[solver_key]
    base_solver = None
    if dc_enabled:
        base_solver_key = (base_discretization, effective_kind)
        if base_solver_key not in _PPE_DISCRETIZATION_SOLVERS:
            raise ValueError(
                f"{effective_path}.discretization={base_discretization!r} does not support "
                f"{effective_path}.kind={effective_kind!r}"
            )
        base_solver = _PPE_DISCRETIZATION_SOLVERS[base_solver_key]
    if base_discretization == "fccd" and effective_kind == "iterative":
        effective_solver_cfg = dict(effective_solver_cfg)
        effective_solver_cfg.setdefault("preconditioner", "none")
    (
        ppe_iteration_method,
        ppe_tolerance,
        ppe_max_iterations,
        ppe_restart,
        ppe_preconditioner,
        ppe_pcr_stages,
        ppe_c_tau,
    ) = parse_ppe_solver_options(effective_kind, effective_solver_cfg, effective_path)
    if base_discretization == "fccd" and ppe_preconditioner not in {"jacobi", "none"}:
        raise ValueError(
            f"{effective_path}.preconditioner for FCCD PPE must be 'jacobi' or 'none', "
            f"got {ppe_preconditioner!r}"
        )
    return (
        ppe_solver,
        base_solver,
        ppe_iteration_method,
        ppe_tolerance,
        ppe_max_iterations,
        ppe_restart,
        ppe_preconditioner,
        ppe_pcr_stages,
        ppe_c_tau,
        dc_enabled,
        dc_max_iterations,
        dc_tolerance,
        dc_relaxation,
    )


_PPE_DISCRETIZATION_SOLVERS_BY_KIND = tuple(
    sorted({key[0] for key in _PPE_DISCRETIZATION_SOLVERS})
)


def parse_ppe_solver_options(
    kind: str,
    solver_cfg: dict,
    path: str,
) -> tuple[str, float, int, int | None, str, int | None, float]:
    iterative_keys = {
        "method", "tolerance", "max_iterations", "restart",
        "preconditioner", "pcr_stages", "c_tau",
    }
    if kind == "direct":
        present = sorted(iterative_keys.intersection(solver_cfg))
        if present:
            raise ValueError(
                f"{path}.kind='direct' does not accept iterative options: {present}"
            )
        return "none", 0.0, 0, None, "none", None, 0.0
    ppe_iteration_method = validate_choice(
        solver_cfg.get("method", "gmres"),
        _PPE_ITERATION_METHODS,
        f"{path}.method",
    )
    default_preconditioner = "jacobi" if ppe_iteration_method == "cg" else "line_pcr"
    ppe_preconditioner = validate_choice(
        solver_cfg.get("preconditioner", default_preconditioner),
        _PPE_PRECONDITIONERS,
        f"{path}.preconditioner",
    )
    if ppe_iteration_method == "cg" and ppe_preconditioner == "line_pcr":
        raise ValueError(
            f"{path}.preconditioner='line_pcr' is not valid with method='cg'; "
            "use 'jacobi' or 'none'."
        )
    ppe_tolerance = float(solver_cfg.get("tolerance", 1.0e-8))
    if ppe_tolerance <= 0.0:
        raise ValueError(f"{path}.tolerance must be > 0")
    ppe_max_iterations = int(solver_cfg.get("max_iterations", 500))
    if ppe_max_iterations <= 0:
        raise ValueError(f"{path}.max_iterations must be > 0")
    ppe_restart = int(solver_cfg["restart"]) if "restart" in solver_cfg else None
    if ppe_restart is not None and ppe_restart <= 0:
        raise ValueError(f"{path}.restart must be > 0")
    if ppe_preconditioner != "line_pcr":
        for key in ("pcr_stages", "c_tau"):
            if key in solver_cfg:
                raise ValueError(
                    f"{path}.{key} is only valid when preconditioner='line_pcr', "
                    f"got preconditioner={ppe_preconditioner!r}"
                )
    ppe_pcr_stages = int(solver_cfg["pcr_stages"]) if "pcr_stages" in solver_cfg else None
    if ppe_pcr_stages is not None and ppe_pcr_stages <= 0:
        raise ValueError(f"{path}.pcr_stages must be > 0")
    ppe_c_tau = float(solver_cfg.get("c_tau", 2.0))
    if ppe_c_tau <= 0.0:
        raise ValueError(f"{path}.c_tau must be > 0")
    return (
        ppe_iteration_method,
        ppe_tolerance,
        ppe_max_iterations,
        ppe_restart,
        ppe_preconditioner,
        ppe_pcr_stages,
        ppe_c_tau,
    )
