"""
VTK RectilinearGrid XML output writer.

Writes simulation fields to ParaView-compatible .vtr (VTK XML RectilinearGrid)
files.  Each timestep produces one .vtr file; an optional .pvd collection
file links all timesteps for time-series animation in ParaView.

No external VTK libraries are required — the XML + binary (base64) format
is assembled from first principles using Python stdlib and NumPy.

Data ordering (VTK RectilinearGrid convention):
    WholeExtent = "0 Nx 0 Ny 0 0" for 2-D grids.
    Flat index:  k = ix + iy*(Nx+1)  — x varies FASTEST.
    Our C-order arrays (axis-0 = x, axis-1 = y, y-fastest in memory) are
    ravelled with order='F' to obtain x-fastest ordering for VTK.

Binary encoding:
    Each DataArray uses format="binary" (base64 encoding of
    [UInt32 byte-count header][float64 data bytes]).  This is the default
    VTK inline binary format supported by all VTK-based viewers (ParaView,
    VisIt, VTK.js).

Usage::

    from twophase.io.vtk_writer import VTKWriter

    writer = VTKWriter(backend, grid, directory="vtk_out")
    sim.run(..., callback=writer.make_callback(interval=10))
    writer.write_pvd()          # emit collection file after run
"""

from __future__ import annotations
import base64
import os
import struct
from typing import Dict, List, Optional, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.grid import Grid


# ── Low-level encoding helpers ─────────────────────────────────────────────

def _b64_encode(arr: np.ndarray) -> str:
    """Encode a float64 numpy array as base64 VTK binary.

    Format: [UInt32 little-endian byte-count header][float64 data bytes],
    then the whole thing base64-encoded to ASCII.

    Parameters
    ----------
    arr : np.ndarray — array to encode (will be cast to float64)

    Returns
    -------
    encoded : str — base64 ASCII string for insertion into VTK XML
    """
    # float64 little-endian bytes
    data = np.ascontiguousarray(arr, dtype='<f8').tobytes()
    # UInt32 header = number of data bytes
    header = struct.pack('<I', len(data))
    return base64.b64encode(header + data).decode('ascii')


def _vtk_order(arr: np.ndarray) -> np.ndarray:
    """Ravel a C-order 2-D/3-D array in VTK x-fastest order.

    VTK RectilinearGrid flat index: k = ix + iy*(Nx+1) + iz*(Nx+1)*(Ny+1),
    so x (axis 0) is the fastest-varying index.  Our arrays are stored in
    C-order where y (axis 1) is fastest.  Fortran-order ravel gives x-fastest.

    Parameters
    ----------
    arr : np.ndarray, shape (Nx+1[, Ny+1[, Nz+1]])

    Returns
    -------
    flat : np.ndarray, shape (n_pts,) — x-fastest flat order
    """
    return np.asarray(arr, dtype=np.float64).ravel(order='F')


# ── VTKWriter ────────────────────────────────────────────────────────────────

class VTKWriter:
    """Write simulation fields to VTK XML RectilinearGrid (.vtr) format.

    Supports 2-D (ndim=2) collocated structured grids.  The output is
    readable by ParaView, VisIt, and any VTK-compatible viewer.

    Each call to ``write()`` or ``write_step()`` produces one ``.vtr`` file.
    After the run, call ``write_pvd()`` to produce a ``.pvd`` collection that
    links all timesteps for time-series animation.

    Parameters
    ----------
    backend   : Backend  — array namespace (NumPy / CuPy)
    grid      : Grid     — node coordinates and shape
    directory : str      — output directory (created on first write)
    """

    def __init__(
        self,
        backend: "Backend",
        grid: "Grid",
        directory: str = "vtk_output",
    ) -> None:
        self.backend = backend
        self.grid = grid
        self.directory = directory
        # (step, time, filename) records accumulated for PVD generation
        self._pvd_entries: List[tuple] = []

    # ── Public API ────────────────────────────────────────────────────────

    def write(
        self,
        fields: Dict[str, object],
        step: int = 0,
        time: float = 0.0,
        directory: Optional[str] = None,
    ) -> str:
        """Write a fields dict to a .vtr file.

        Implements VTK XML RectilinearGrid format (VTK File Formats §6,
        VTK 4.2 / VTK XML format specification).

        Parameters
        ----------
        fields : dict
            Expected keys (all shapes must equal ``grid.shape``):

            - ``"psi"``      : array — level set ψ
            - ``"pressure"`` : array — pressure p
            - ``"velocity"`` : list of ``ndim`` arrays — velocity components
            - ``"rho"``      : array (optional) — density ρ
            - ``"kappa"``    : array (optional) — curvature κ
        step      : int   — timestep index (used for filename)
        time      : float — physical time (stored in PVD entry)
        directory : str   — override output directory

        Returns
        -------
        path : str — absolute path of the written .vtr file
        """
        out_dir = directory or self.directory
        os.makedirs(out_dir, exist_ok=True)

        fname = f"step_{step:08d}.vtr"
        path = os.path.join(out_dir, fname)

        xml_str = self._build_vtr_xml(fields)
        with open(path, 'w', encoding='ascii') as f:
            f.write(xml_str)

        # Record for PVD
        self._pvd_entries.append((step, time, fname))
        return path

    def write_step(
        self,
        sim,
        step: Optional[int] = None,
        directory: Optional[str] = None,
    ) -> str:
        """Write the current simulation state to a .vtr file.

        Convenience wrapper around ``write()`` that extracts all relevant
        fields from a ``TwoPhaseSimulation`` instance.

        Parameters
        ----------
        sim       : TwoPhaseSimulation
        step      : int (default: sim.step)
        directory : str (default: self.directory)

        Returns
        -------
        path : str — path of the written file
        """
        be = self.backend
        ndim = sim.config.grid.ndim
        s = step if step is not None else sim.step

        # 速度成分を各軸ごとにホストへ転送
        vel = [
            np.asarray(be.to_host(sim.velocity[ax]))
            for ax in range(ndim)
        ]

        fields: Dict[str, object] = {
            "psi":      np.asarray(be.to_host(sim.psi.data)),
            "pressure": np.asarray(be.to_host(sim.pressure.data)),
            "velocity": vel,
            "rho":      np.asarray(be.to_host(sim.rho.data)),
            "kappa":    np.asarray(be.to_host(sim.kappa.data)),
        }

        return self.write(fields, step=s, time=sim.time, directory=directory)

    def make_callback(self, interval: int = 1):
        """Return a callback suitable for ``sim.run(callback=...)``.

        Parameters
        ----------
        interval : int — write a .vtr file every ``interval`` callback calls

        Returns
        -------
        callback : Callable[sim] → None
        """
        counter = {"n": 0}

        def callback(sim) -> None:
            counter["n"] += 1
            if counter["n"] % interval == 0:
                path = self.write_step(sim)
                print(f"  [vtk] wrote → {path}")

        return callback

    def write_pvd(self, directory: Optional[str] = None) -> str:
        """Write a ParaView Data (.pvd) collection file.

        Links all .vtr files recorded since construction into a single
        time-annotated collection, enabling time-series animation in
        ParaView.  The file is written to ``directory/simulation.pvd``.

        Parameters
        ----------
        directory : str (default: self.directory)

        Returns
        -------
        path : str — path of the written .pvd file
        """
        out_dir = directory or self.directory
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, "simulation.pvd")

        lines = [
            '<?xml version="1.0"?>',
            '<VTKFile type="Collection" version="0.1"'
            ' byte_order="LittleEndian">',
            '  <Collection>',
        ]
        for step, time, fname in sorted(self._pvd_entries, key=lambda e: e[0]):
            lines.append(
                f'    <DataSet timestep="{time:.6g}" group="" part="0"'
                f' file="{fname}"/>'
            )
        lines += [
            '  </Collection>',
            '</VTKFile>',
            '',
        ]

        with open(path, 'w', encoding='ascii') as f:
            f.write('\n'.join(lines))
        return path

    # ── Private XML assembly ─────────────────────────────────────────────

    def _build_vtr_xml(self, fields: dict) -> str:
        """Assemble the complete VTK XML RectilinearGrid string.

        Parameters
        ----------
        fields : dict — see ``write()`` for the expected keys

        Returns
        -------
        xml_str : str — complete VTK XML file content
        """
        grid = self.grid
        ndim = grid.ndim

        # "0 Nx 0 Ny 0 0" for 2-D, "0 Nx 0 Ny 0 Nz" for 3-D
        ext_parts: list = []
        for ax in range(ndim):
            ext_parts += [0, grid.N[ax]]
        if ndim == 2:
            ext_parts += [0, 0]   # 2-D: single z-layer
        extent_str = ' '.join(str(v) for v in ext_parts)

        coords_xml   = self._coordinates_xml(ndim)
        point_data_xml = self._point_data_xml(fields, ndim)

        return (
            '<?xml version="1.0"?>\n'
            '<VTKFile type="RectilinearGrid" version="0.1"'
            ' byte_order="LittleEndian">\n'
            f'  <RectilinearGrid WholeExtent="{extent_str}">\n'
            f'    <Piece Extent="{extent_str}">\n'
            f'{coords_xml}'
            f'{point_data_xml}'
            '    </Piece>\n'
            '  </RectilinearGrid>\n'
            '</VTKFile>\n'
        )

    def _coordinates_xml(self, ndim: int) -> str:
        """Emit the <Coordinates> block with per-axis 1-D node positions.

        Uses ``grid.coords[ax]`` (physical coordinates) so that non-uniform
        grids are correctly represented in the VTK file.
        """
        grid = self.grid
        axis_names = ['x', 'y', 'z']
        lines = ['      <Coordinates>\n']

        for ax in range(ndim):
            coords = np.asarray(grid.coords[ax], dtype=np.float64)
            encoded = _b64_encode(coords)
            lines.append(
                f'        <DataArray type="Float64" Name="{axis_names[ax]}"'
                f' format="binary">{encoded}</DataArray>\n'
            )

        # z-coordinate: single 0.0 for 2-D slices
        if ndim == 2:
            z = np.zeros(1, dtype=np.float64)
            lines.append(
                f'        <DataArray type="Float64" Name="z"'
                f' format="binary">{_b64_encode(z)}</DataArray>\n'
            )

        lines.append('      </Coordinates>\n')
        return ''.join(lines)

    def _point_data_xml(self, fields: dict, ndim: int) -> str:
        """Emit the <PointData> block for all fields in the dict.

        Data ordering: each array is ravelled in Fortran order (x fastest)
        to match the VTK RectilinearGrid flat-index convention.  Velocity is
        stored as a 3-component array (z component = 0 for 2-D).
        """
        lines = ['      <PointData>\n']

        # スカラー場（psi, pressure, rho, kappa）を順に書き出す
        for name in ('psi', 'pressure', 'rho', 'kappa'):
            if name not in fields:
                continue
            arr = np.asarray(fields[name], dtype=np.float64)
            encoded = _b64_encode(_vtk_order(arr))
            lines.append(
                f'        <DataArray type="Float64" Name="{name}"'
                f' format="binary">{encoded}</DataArray>\n'
            )

        # 速度ベクトル場（VTK は常に 3 成分を要求する）
        if 'velocity' in fields:
            vel = fields['velocity']
            # 各成分を x-fastest 順にフラット化
            comps = [
                _vtk_order(np.asarray(vel[ax], dtype=np.float64))
                for ax in range(ndim)
            ]
            if ndim == 2:
                # 2-D の場合は z 成分をゼロ埋めで追加
                comps.append(np.zeros_like(comps[0]))
            # (vx₀, vy₀, vz₀, vx₁, vy₁, vz₁, …) の交互配列
            vel_flat = np.column_stack(comps).ravel()
            encoded = _b64_encode(vel_flat)
            lines.append(
                f'        <DataArray type="Float64" Name="velocity"'
                f' NumberOfComponents="3"'
                f' format="binary">{encoded}</DataArray>\n'
            )

        lines.append('      </PointData>\n')
        return ''.join(lines)
