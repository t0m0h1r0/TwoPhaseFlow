"""Closed import manifest for direct-branch AO geometry symbols.

A3 chain:
  Equation: SP-AO requires exact geometric ``Q_h/S_h/J_q/dS_h`` operators.
  Discretization: direct-branch symbols are admitted only after classification
  as dense oracle, GPU production, or reject.
  Code: this manifest records the classification contract before runtime use.

The manifest is intentionally independent of runtime construction.  It prevents
unclassified direct-AO code from becoming an implicit dense fallback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping


class ImportClassification(str, Enum):
    """Closed production classification enum for imported AO symbols."""

    ORACLE_ONLY = "oracle_only"
    CPU_EXACT_RUNTIME = "cpu_exact_runtime"
    GPU_PRODUCTION = "gpu_production"
    REJECT = "reject"


class MigrationStatus(str, Enum):
    """Separate migration status; never used as production classification."""

    DIAGNOSTIC_ORACLE = "diagnostic_oracle"
    PENDING_REWRITE = "pending_rewrite"
    PENDING_GPU_AUDIT = "pending_gpu_audit"
    DELAYED_ADAPTER = "delayed_adapter"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ImportedSymbol:
    """One direct-branch symbol classification record."""

    source_symbol: str
    classification: ImportClassification
    migration_status: MigrationStatus
    allowed_import_module: str
    forbidden_runtime_callers: tuple[str, ...] = field(default_factory=tuple)
    required_tests: tuple[str, ...] = field(default_factory=tuple)
    no_d2h_audit: str = "not_applicable"
    rationale: str = ""

    def validate(self) -> None:
        """Raise if the manifest row is incomplete or semantically unsafe."""
        if not self.source_symbol:
            raise ValueError("import manifest row requires source_symbol")
        if not self.allowed_import_module:
            raise ValueError(f"{self.source_symbol}: allowed_import_module is required")
        if not self.required_tests:
            raise ValueError(f"{self.source_symbol}: required_tests must be declared")
        if self.classification is ImportClassification.GPU_PRODUCTION:
            if self.no_d2h_audit not in {"pending", "pass"}:
                raise ValueError(
                    f"{self.source_symbol}: gpu_production requires pending/pass "
                    "no-D2H audit"
                )
        if self.classification is ImportClassification.CPU_EXACT_RUNTIME:
            if self.no_d2h_audit != "gpu_fail_closed":
                raise ValueError(
                    f"{self.source_symbol}: cpu_exact_runtime requires "
                    "no_d2h_audit='gpu_fail_closed'"
                )
        if self.classification is ImportClassification.ORACLE_ONLY:
            if not self.forbidden_runtime_callers:
                raise ValueError(
                    f"{self.source_symbol}: oracle_only row must forbid runtime callers"
                )
        if self.classification is ImportClassification.REJECT:
            if self.migration_status is not MigrationStatus.REJECTED:
                raise ValueError(
                    f"{self.source_symbol}: reject classification requires rejected status"
                )


def normalize_classification(value: str | ImportClassification) -> ImportClassification:
    """Normalize a raw classification string through the closed enum."""
    if isinstance(value, ImportClassification):
        return value
    try:
        return ImportClassification(str(value).strip().lower())
    except ValueError as exc:
        allowed = tuple(item.value for item in ImportClassification)
        raise ValueError(f"import classification must be one of {allowed}") from exc


def normalize_migration_status(value: str | MigrationStatus) -> MigrationStatus:
    """Normalize a raw migration status string through the closed enum."""
    if isinstance(value, MigrationStatus):
        return value
    try:
        return MigrationStatus(str(value).strip().lower())
    except ValueError as exc:
        allowed = tuple(item.value for item in MigrationStatus)
        raise ValueError(f"migration_status must be one of {allowed}") from exc


def manifest_row_from_mapping(raw: Mapping[str, object]) -> ImportedSymbol:
    """Build one validated :class:`ImportedSymbol` from a mapping."""
    row = ImportedSymbol(
        source_symbol=str(raw.get("source_symbol", "")),
        classification=normalize_classification(raw.get("classification", "")),
        migration_status=normalize_migration_status(raw.get("migration_status", "")),
        allowed_import_module=str(raw.get("allowed_import_module", "")),
        forbidden_runtime_callers=tuple(raw.get("forbidden_runtime_callers", ()) or ()),
        required_tests=tuple(raw.get("required_tests", ()) or ()),
        no_d2h_audit=str(raw.get("no_d2h_audit", "not_applicable")),
        rationale=str(raw.get("rationale", "")),
    )
    row.validate()
    return row


def validate_manifest(rows: Iterable[ImportedSymbol]) -> tuple[ImportedSymbol, ...]:
    """Validate uniqueness and completeness for a manifest row collection."""
    validated: list[ImportedSymbol] = []
    seen: set[str] = set()
    for row in rows:
        row.validate()
        if row.source_symbol in seen:
            raise ValueError(f"duplicate import manifest row: {row.source_symbol}")
        seen.add(row.source_symbol)
        validated.append(row)
    return tuple(validated)


DEFAULT_IMPORT_MANIFEST: tuple[ImportedSymbol, ...] = validate_manifest(
    (
        ImportedSymbol(
            source_symbol="geometry.p1_cut_geometry.cut_geometry_2d",
            classification=ImportClassification.CPU_EXACT_RUNTIME,
            migration_status=MigrationStatus.PENDING_GPU_AUDIT,
            allowed_import_module="twophase.geometry",
            required_tests=(
                "test_dense_reference_q_sum_matches_p1_area",
                "test_direct_dense_geometry_rejects_gpu_backend",
            ),
            no_d2h_audit="gpu_fail_closed",
            rationale=(
                "Dense exact Q_h/S_h CPU runtime and oracle; CUDA arrays fail closed."
            ),
        ),
        ImportedSymbol(
            source_symbol="geometry.cell_complex.MetricCellComplex",
            classification=ImportClassification.CPU_EXACT_RUNTIME,
            migration_status=MigrationStatus.PENDING_GPU_AUDIT,
            allowed_import_module="twophase.geometry",
            required_tests=(
                "test_metric_cell_complex_cache_invalidates_on_new_coords",
                "test_direct_dense_geometry_rejects_gpu_backend",
            ),
            no_d2h_audit="gpu_fail_closed",
            rationale=(
                "Dense exact metric-cell CPU runtime; active GPU metric cache is separate."
            ),
        ),
        ImportedSymbol(
            source_symbol="geometry.compatibility_projection.project_cell_volume_compatibility_2d",
            classification=ImportClassification.CPU_EXACT_RUNTIME,
            migration_status=MigrationStatus.PENDING_GPU_AUDIT,
            allowed_import_module="twophase.geometry",
            required_tests=(
                "test_geometric_runtime_rejects_active_projection_schedule",
                "test_direct_dense_geometry_rejects_gpu_backend",
            ),
            no_d2h_audit="gpu_fail_closed",
            rationale=(
                "Dense exact projection is CPU-only; active projection schedule is "
                "blocked until the fused path is wired."
            ),
        ),
        ImportedSymbol(
            source_symbol="geometry.swept_flux.construct_p1_swept_flux_2d",
            classification=ImportClassification.CPU_EXACT_RUNTIME,
            migration_status=MigrationStatus.PENDING_GPU_AUDIT,
            allowed_import_module="twophase.geometry",
            required_tests=("test_direct_dense_geometry_rejects_gpu_backend",),
            no_d2h_audit="gpu_fail_closed",
            rationale="Dense exact swept-volume CPU runtime; CUDA arrays fail closed.",
        ),
        ImportedSymbol(
            source_symbol="geometry.bundle_capillary.geometric_pressure_capillary_hodge_2d",
            classification=ImportClassification.CPU_EXACT_RUNTIME,
            migration_status=MigrationStatus.PENDING_GPU_AUDIT,
            allowed_import_module="twophase.geometry",
            required_tests=("test_direct_dense_geometry_rejects_gpu_backend",),
            no_d2h_audit="gpu_fail_closed",
            rationale="Dense exact capillary Hodge CPU runtime; CUDA arrays fail closed.",
        ),
    )
)
