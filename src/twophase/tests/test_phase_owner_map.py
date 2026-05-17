"""Tests for explicit phase-owner cell-measure maps."""

from __future__ import annotations

import numpy as np
import pytest

from twophase.geometry import (
    AtlasValidationError,
    CellMeasurePhase,
    map_cell_measure_to_phase_owner,
)


def test_runtime_liquid_measure_maps_to_gas_owner_by_exact_complement():
    cell_area = np.array(((0.10, 0.20), (0.15, 0.25)), dtype=float)
    liquid_q = np.array(((0.03, 0.14), (0.05, 0.10)), dtype=float)

    mapped = map_cell_measure_to_phase_owner(
        liquid_q,
        cell_area,
        source_phase=CellMeasurePhase.LIQUID,
        owner_phase=CellMeasurePhase.GAS,
    )

    np.testing.assert_allclose(mapped.q_owner, cell_area - liquid_q)
    np.testing.assert_allclose(mapped.q_source, liquid_q)
    assert mapped.source_phase is CellMeasurePhase.LIQUID
    assert mapped.owner_phase is CellMeasurePhase.GAS
    assert mapped.complement_used is True
    assert mapped.owner_volume == pytest.approx(float(np.sum(cell_area - liquid_q)))
    assert mapped.source_volume + mapped.owner_volume == pytest.approx(float(np.sum(cell_area)))
    assert mapped.q_min >= 0.0
    assert mapped.capacity_excess_linf <= 0.0


def test_matching_phase_owner_passes_measure_without_hidden_complement():
    cell_area = np.array(((0.10, 0.20), (0.15, 0.25)), dtype=float)
    gas_q = np.array(((0.07, 0.06), (0.10, 0.15)), dtype=float)

    mapped = map_cell_measure_to_phase_owner(
        gas_q,
        cell_area,
        source_phase="gas",
        owner_phase="gas",
    )

    np.testing.assert_allclose(mapped.q_owner, gas_q)
    assert mapped.source_phase is CellMeasurePhase.GAS
    assert mapped.owner_phase is CellMeasurePhase.GAS
    assert mapped.complement_used is False
    assert mapped.owner_volume == pytest.approx(float(np.sum(gas_q)))


def test_phase_owner_map_accepts_device_arrays_when_available():
    cp = pytest.importorskip("cupy")
    try:
        if cp.cuda.runtime.getDeviceCount() < 1:
            pytest.skip("CUDA device is unavailable")
    except cp.cuda.runtime.CUDARuntimeError as exc:
        pytest.skip(f"CUDA device is unavailable: {exc}")
    cell_area_cpu = np.array(((0.10, 0.20), (0.15, 0.25)), dtype=float)
    liquid_cpu = np.array(((0.03, 0.14), (0.05, 0.10)), dtype=float)

    mapped = map_cell_measure_to_phase_owner(
        cp.asarray(liquid_cpu),
        cp.asarray(cell_area_cpu),
        source_phase=CellMeasurePhase.LIQUID,
        owner_phase=CellMeasurePhase.GAS,
    )

    assert hasattr(mapped.q_owner, "__cuda_array_interface__")
    np.testing.assert_allclose(cp.asnumpy(mapped.q_owner), cell_area_cpu - liquid_cpu)
    assert mapped.owner_volume == pytest.approx(float(np.sum(cell_area_cpu - liquid_cpu)))
    assert mapped.complement_used is True


def test_phase_owner_map_fails_closed_on_shape_capacity_and_phase_errors():
    cell_area = np.ones((2, 2), dtype=float)

    with pytest.raises(AtlasValidationError, match="same shape"):
        map_cell_measure_to_phase_owner(
            np.ones((2, 3)),
            cell_area,
            source_phase=CellMeasurePhase.LIQUID,
            owner_phase=CellMeasurePhase.GAS,
        )

    with pytest.raises(AtlasValidationError, match="below zero"):
        map_cell_measure_to_phase_owner(
            np.array(((-1.0e-2, 0.0), (0.0, 0.0))),
            cell_area,
            source_phase=CellMeasurePhase.LIQUID,
            owner_phase=CellMeasurePhase.GAS,
        )

    with pytest.raises(AtlasValidationError, match="cell capacity"):
        map_cell_measure_to_phase_owner(
            np.array(((1.2, 0.0), (0.0, 0.0))),
            cell_area,
            source_phase=CellMeasurePhase.LIQUID,
            owner_phase=CellMeasurePhase.GAS,
        )

    with pytest.raises(AtlasValidationError, match="LIQUID or GAS"):
        map_cell_measure_to_phase_owner(
            np.zeros((2, 2)),
            cell_area,
            source_phase="vapor",
            owner_phase=CellMeasurePhase.GAS,
        )

    with pytest.raises(AtlasValidationError, match="finite and nonnegative"):
        map_cell_measure_to_phase_owner(
            np.zeros((2, 2)),
            cell_area,
            source_phase=CellMeasurePhase.LIQUID,
            owner_phase=CellMeasurePhase.GAS,
            capacity_tolerance=np.nan,
        )
