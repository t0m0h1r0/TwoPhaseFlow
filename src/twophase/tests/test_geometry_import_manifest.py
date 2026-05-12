"""Closed import manifest tests for AO-Fast C1."""

from __future__ import annotations

import pytest

from twophase.geometry.import_manifest import (
    DEFAULT_IMPORT_MANIFEST,
    ImportClassification,
    ImportedSymbol,
    MigrationStatus,
    manifest_row_from_mapping,
    normalize_classification,
    validate_manifest,
)


def test_import_manifest_uses_closed_classification_enum():
    assert normalize_classification("oracle_only") is ImportClassification.ORACLE_ONLY
    assert normalize_classification("gpu_production") is ImportClassification.GPU_PRODUCTION
    assert normalize_classification("reject") is ImportClassification.REJECT

    with pytest.raises(ValueError, match="classification"):
        normalize_classification("pending_rewrite")


def test_default_manifest_forbids_dense_projection_runtime_fallback():
    rows = {row.source_symbol: row for row in DEFAULT_IMPORT_MANIFEST}
    projection = rows["geometry.compatibility_projection.project_cell_volume_compatibility_2d"]

    assert projection.classification is ImportClassification.ORACLE_ONLY
    assert projection.allowed_import_module == "none"
    assert "runtime" in projection.forbidden_runtime_callers


def test_manifest_rows_require_tests_and_runtime_forbidden_oracle():
    with pytest.raises(ValueError, match="required_tests"):
        ImportedSymbol(
            source_symbol="geometry.p1_cut_geometry.cut_geometry_2d",
            classification=ImportClassification.ORACLE_ONLY,
            migration_status=MigrationStatus.DIAGNOSTIC_ORACLE,
            allowed_import_module="twophase.geometry.dense_reference",
            forbidden_runtime_callers=("runtime",),
        ).validate()

    with pytest.raises(ValueError, match="forbid runtime"):
        ImportedSymbol(
            source_symbol="geometry.p1_cut_geometry.cut_geometry_2d",
            classification=ImportClassification.ORACLE_ONLY,
            migration_status=MigrationStatus.DIAGNOSTIC_ORACLE,
            allowed_import_module="twophase.geometry.dense_reference",
            required_tests=("test_dense_reference_q_sum_matches_p1_area",),
        ).validate()


def test_manifest_mapping_and_duplicate_validation_fail_closed():
    row = manifest_row_from_mapping(
        {
            "source_symbol": "geometry.cell_complex.MetricCellComplex",
            "classification": "oracle_only",
            "migration_status": "diagnostic_oracle",
            "allowed_import_module": "twophase.geometry.dense_reference",
            "forbidden_runtime_callers": ("runtime",),
            "required_tests": ("test_metric_cell_complex_cache_invalidates_on_new_coords",),
        }
    )
    assert row.classification is ImportClassification.ORACLE_ONLY

    with pytest.raises(ValueError, match="duplicate"):
        validate_manifest((row, row))
