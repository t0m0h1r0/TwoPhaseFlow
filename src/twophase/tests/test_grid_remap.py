"""Tests for grid remapping utilities."""

from __future__ import annotations

import numpy as np
import pytest

from twophase.backend import Backend
from twophase.core.grid_remap import (
    IdentityGridRemapper,
    build_grid_remapper,
    remap_field_to_uniform,
)


@pytest.fixture
def backend():
    return Backend(use_gpu=False)


def _nonuniform_coords():
    x = np.array([0.0, 0.07, 0.21, 0.45, 0.73, 1.0], dtype=float)
    y = np.array([0.0, 0.12, 0.39, 0.68, 1.0], dtype=float)
    return x, y


def test_identity_mapper_selected_for_same_coords(backend):
    x = np.linspace(0.0, 1.0, 9)
    y = np.linspace(0.0, 1.0, 7)
    remapper = build_grid_remapper(backend, [x, y], [x.copy(), y.copy()])
    assert isinstance(remapper, IdentityGridRemapper)

    xp = backend.xp
    q = xp.asarray(np.random.default_rng(0).normal(size=(x.size, y.size)))
    q2 = remapper.remap(q)
    np.testing.assert_allclose(
        np.asarray(backend.to_host(q2)),
        np.asarray(backend.to_host(q)),
        atol=0.0, rtol=0.0,
    )


def test_linear_remap_exact_for_linear_field(backend):
    x_src, y_src = _nonuniform_coords()
    x_tgt = np.linspace(0.0, 1.0, 11)
    y_tgt = np.linspace(0.0, 1.0, 13)

    Xs, Ys = np.meshgrid(x_src, y_src, indexing="ij")
    q_src = 2.0 * Xs - 3.0 * Ys + 1.25  # linear => exact under linear interpolation

    remapper = build_grid_remapper(backend, [x_src, y_src], [x_tgt, y_tgt])
    q_tgt = np.asarray(backend.to_host(remapper.remap(q_src)))

    Xt, Yt = np.meshgrid(x_tgt, y_tgt, indexing="ij")
    q_exact = 2.0 * Xt - 3.0 * Yt + 1.25
    np.testing.assert_allclose(q_tgt, q_exact, rtol=1e-12, atol=1e-12)


def test_mapping_info_exports_weights(backend):
    x_src, y_src = _nonuniform_coords()
    x_tgt = np.linspace(0.0, 1.0, 8)
    y_tgt = np.linspace(0.0, 1.0, 9)

    remapper = build_grid_remapper(backend, [x_src, y_src], [x_tgt, y_tgt])
    info = remapper.mapping_info(include_weights=True)

    assert info["type"] in {"identity", "linear", "cubic_lagrange"}
    assert len(info["source_coords"]) == 2
    assert len(info["target_coords"]) == 2
    if info["type"] == "linear":
        assert len(info["axis"]) == 2
        ax0 = info["axis"][0]
        ax1 = info["axis"][1]
        assert ax0.left_index.shape == (x_tgt.size,)
        assert ax1.left_index.shape == (y_tgt.size,)
        assert ax0.weight_right.shape == (x_tgt.size,)
        assert ax1.weight_right.shape == (y_tgt.size,)
        assert np.all(ax0.weight_right >= -1e-14)
        assert np.all(ax0.weight_right <= 1.0 + 1e-14)
        assert np.all(ax1.weight_right >= -1e-14)
        assert np.all(ax1.weight_right <= 1.0 + 1e-14)


def test_remap_field_to_uniform_linear_exact(backend):
    x_src, y_src = _nonuniform_coords()
    Xs, Ys = np.meshgrid(x_src, y_src, indexing="ij")
    q_src = 2.0 * Xs - 3.0 * Ys + 1.25

    q_uni, coords, remapper = remap_field_to_uniform(
        backend=backend,
        field=q_src,
        source_coords=[x_src, y_src],
        domain_lengths=[1.0, 1.0],
        clip_range=None,
    )
    Xt, Yt = np.meshgrid(coords[0], coords[1], indexing="ij")
    q_exact = 2.0 * Xt - 3.0 * Yt + 1.25
    np.testing.assert_allclose(q_uni, q_exact, rtol=1e-12, atol=1e-12)


def test_remap_field_to_uniform_clips(backend):
    x_src, y_src = _nonuniform_coords()
    Xs, Ys = np.meshgrid(x_src, y_src, indexing="ij")
    q_src = 5.0 * Xs - 2.0  # ranges from -2 to +3

    q_uni, _, _ = remap_field_to_uniform(
        backend=backend,
        field=q_src,
        source_coords=[x_src, y_src],
        domain_lengths=[1.0, 1.0],
        clip_range=(0.0, 1.0),
    )
    assert np.all(q_uni >= 0.0)
    assert np.all(q_uni <= 1.0)
