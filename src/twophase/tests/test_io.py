"""
VTKWriter のテスト (io/vtk_writer.py)。

検証項目:
  1. .vtr ファイルが正しい名前で生成されること
  2. VTK XML が解析可能で正しい構造（WholeExtent, Piece Extent）を持つこと
  3. スカラー場 (psi, pressure, rho, kappa) のラウンドトリップ精度 (fp64)
  4. 速度ベクトル場のラウンドトリップ（3 成分交互配列; z=0 for 2-D）
  5. 座標配列が grid.coords と一致すること
  6. write_pvd() が全ステップを正しい時刻順で列挙する .pvd を生成すること
  7. make_callback(interval=N) が N 回に 1 回だけファイルを書き出すこと
  8. write_step(sim) が TwoPhaseSimulation から正しくフィールドを収集すること

NOTE: このテストは数値精度（MMS）ではなく I/O の正確性を検証する。
"""

import base64, os, struct, tempfile
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from twophase.backend import Backend
from twophase.config import SimulationConfig, GridConfig
from twophase.core.grid import Grid
from twophase.io.vtk_writer import VTKWriter, _b64_encode, _vtk_order


# ── テスト共通フィクスチャ ─────────────────────────────────────────────────

@pytest.fixture
def setup():
    """非正方形格子 (N=8×12) でテスト — 軸の取り違えエラーを検出しやすい。"""
    backend = Backend(use_gpu=False)
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(8, 12), L=(1.0, 1.5)))
    grid = Grid(cfg.grid, backend)
    return backend, grid


def _make_fields(grid, seed: int = 42) -> dict:
    """テスト用の合成フィールドを生成する。"""
    rng = np.random.default_rng(seed)
    shape = grid.shape   # (N[0]+1, N[1]+1) = (9, 13)
    return {
        "psi":      rng.standard_normal(shape),
        "pressure": rng.standard_normal(shape) * 0.5,
        "velocity": [rng.standard_normal(shape), rng.standard_normal(shape)],
        "rho":      np.ones(shape) * 1.2,
        "kappa":    rng.standard_normal(shape) * 0.1,
    }


def _decode_b64(text: str) -> np.ndarray:
    """VTK base64 binary (UInt32 ヘッダ + float64 データ) をデコードする。"""
    raw = base64.b64decode(text.strip())
    nbytes = struct.unpack_from('<I', raw, 0)[0]
    data = np.frombuffer(raw, dtype='<f8', offset=4)
    assert len(data) * 8 == nbytes, "VTK header byte count mismatch"
    return data


# ── Test 1: ファイル生成 ────────────────────────────────────────────────────

def test_write_creates_vtr_file(setup):
    """write() が正しいファイル名の .vtr を生成すること。"""
    backend, grid = setup
    fields = _make_fields(grid)
    with tempfile.TemporaryDirectory() as d:
        writer = VTKWriter(backend, grid, directory=d)
        path = writer.write(fields, step=5, time=0.1)
        assert os.path.isfile(path), f"File not found: {path}"
        assert path.endswith("step_00000005.vtr")
        assert os.path.getsize(path) > 0


# ── Test 2: XML 構造 ────────────────────────────────────────────────────────

def test_xml_structure_and_extent(setup):
    """VTK XML が正しいルート要素・WholeExtent・Piece 構造を持つこと。"""
    backend, grid = setup
    fields = _make_fields(grid)
    Nx, Ny = grid.N
    expected_extent = f"0 {Nx} 0 {Ny} 0 0"

    with tempfile.TemporaryDirectory() as d:
        writer = VTKWriter(backend, grid, directory=d)
        path = writer.write(fields, step=0, time=0.0)

        tree = ET.parse(path)
        root = tree.getroot()

        assert root.tag == "VTKFile"
        assert root.attrib["type"] == "RectilinearGrid"

        rg = root.find("RectilinearGrid")
        assert rg is not None, "<RectilinearGrid> element missing"
        assert rg.attrib["WholeExtent"] == expected_extent, (
            f"Expected WholeExtent='{expected_extent}' "
            f"got '{rg.attrib.get('WholeExtent')}'"
        )

        piece = rg.find("Piece")
        assert piece is not None, "<Piece> element missing"
        assert piece.attrib["Extent"] == expected_extent


# ── Test 3: スカラー場ラウンドトリップ ────────────────────────────────────

def test_scalar_field_roundtrip(setup):
    """psi, pressure, rho, kappa が fp64 精度で正確に復元されること。"""
    backend, grid = setup
    fields = _make_fields(grid)

    with tempfile.TemporaryDirectory() as d:
        writer = VTKWriter(backend, grid, directory=d)
        path = writer.write(fields, step=0, time=0.0)

        tree = ET.parse(path)
        pd = tree.getroot().find(".//PointData")
        assert pd is not None, "<PointData> element missing"

        for name in ("psi", "pressure", "rho", "kappa"):
            da = next(
                (e for e in pd if e.attrib.get("Name") == name), None
            )
            assert da is not None, f"DataArray '{name}' missing in <PointData>"

            decoded = _decode_b64(da.text)
            expected = _vtk_order(fields[name])

            np.testing.assert_array_equal(
                decoded, expected,
                err_msg=f"Round-trip mismatch for field '{name}'"
            )


# ── Test 4: 速度ベクトル場ラウンドトリップ ───────────────────────────────

def test_velocity_roundtrip(setup):
    """velocity が 3 成分交互配列 (vx,vy,vz=0) で正確に復元されること。"""
    backend, grid = setup
    fields = _make_fields(grid)
    Nx, Ny = grid.N
    n_pts = (Nx + 1) * (Ny + 1)

    with tempfile.TemporaryDirectory() as d:
        writer = VTKWriter(backend, grid, directory=d)
        path = writer.write(fields, step=0, time=0.0)

        tree = ET.parse(path)
        da = tree.getroot().find(".//DataArray[@Name='velocity']")
        assert da is not None, "velocity DataArray missing"
        assert int(da.attrib["NumberOfComponents"]) == 3

        decoded = _decode_b64(da.text)
        assert decoded.size == n_pts * 3, (
            f"Expected {n_pts * 3} values, got {decoded.size}"
        )

        # 交互配列から各成分を分離: (vx0,vy0,vz0, vx1,vy1,vz1, ...)
        vx_dec = decoded[0::3]
        vy_dec = decoded[1::3]
        vz_dec = decoded[2::3]

        vx_exp = _vtk_order(fields["velocity"][0])
        vy_exp = _vtk_order(fields["velocity"][1])

        np.testing.assert_array_equal(vx_dec, vx_exp, err_msg="vx mismatch")
        np.testing.assert_array_equal(vy_dec, vy_exp, err_msg="vy mismatch")
        np.testing.assert_array_equal(vz_dec, 0.0, err_msg="vz != 0 for 2-D")


# ── Test 5: 座標配列 ────────────────────────────────────────────────────────

def test_coordinate_arrays(setup):
    """<Coordinates> が grid.coords と一致する 1-D 座標配列を持つこと。"""
    backend, grid = setup
    fields = _make_fields(grid)
    Nx, Ny = grid.N

    with tempfile.TemporaryDirectory() as d:
        writer = VTKWriter(backend, grid, directory=d)
        path = writer.write(fields, step=0, time=0.0)

        tree = ET.parse(path)
        coords_el = tree.getroot().find(".//Coordinates")
        assert coords_el is not None, "<Coordinates> element missing"

        x_da = next(e for e in coords_el if e.attrib["Name"] == "x")
        y_da = next(e for e in coords_el if e.attrib["Name"] == "y")
        z_da = next(e for e in coords_el if e.attrib["Name"] == "z")

        x_dec = _decode_b64(x_da.text)
        y_dec = _decode_b64(y_da.text)
        z_dec = _decode_b64(z_da.text)

        np.testing.assert_array_equal(
            x_dec, np.asarray(grid.coords[0], dtype=np.float64),
            err_msg="x-coordinate mismatch"
        )
        np.testing.assert_array_equal(
            y_dec, np.asarray(grid.coords[1], dtype=np.float64),
            err_msg="y-coordinate mismatch"
        )
        np.testing.assert_array_equal(z_dec, [0.0], err_msg="z != 0.0 for 2-D")

        assert len(x_dec) == Nx + 1
        assert len(y_dec) == Ny + 1


# ── Test 6: PVD コレクションファイル ─────────────────────────────────────

def test_pvd_collection_structure(setup):
    """write_pvd() が全ステップを正しい順序と timestep 属性で列挙すること。"""
    backend, grid = setup
    fields = _make_fields(grid)

    with tempfile.TemporaryDirectory() as d:
        writer = VTKWriter(backend, grid, directory=d)
        writer.write(fields, step=20, time=0.2)   # 意図的に逆順で追加
        writer.write(fields, step=0,  time=0.0)
        writer.write(fields, step=10, time=0.1)

        pvd_path = writer.write_pvd()
        assert os.path.isfile(pvd_path), f".pvd not found: {pvd_path}"

        tree = ET.parse(pvd_path)
        root = tree.getroot()
        assert root.attrib["type"] == "Collection"

        datasets = root.findall(".//DataSet")
        assert len(datasets) == 3

        # ステップ昇順でソートされていること
        timesteps = [float(ds.attrib["timestep"]) for ds in datasets]
        assert timesteps == [0.0, 0.1, 0.2]

        fnames = [ds.attrib["file"] for ds in datasets]
        assert fnames[0] == "step_00000000.vtr"
        assert fnames[1] == "step_00000010.vtr"
        assert fnames[2] == "step_00000020.vtr"


# ── Test 7: make_callback の呼び出し間隔 ────────────────────────────────────

def test_make_callback_interval(setup):
    """make_callback(interval=3) が 3 回に 1 回だけファイルを書き出すこと。"""
    backend, grid = setup
    fields = _make_fields(grid)

    # TwoPhaseSimulation の最小モック
    class _FakeSim:
        step = 0
        time = 0.0
        config = type("C", (), {
            "grid": type("G", (), {"ndim": 2})()
        })()
        psi      = type("F", (), {"data": fields["psi"]})()
        pressure = type("F", (), {"data": fields["pressure"]})()
        rho      = type("F", (), {"data": fields["rho"]})()
        kappa    = type("F", (), {"data": fields["kappa"]})()

        def __getitem_vel(self, ax):
            return fields["velocity"][ax]
        velocity = {0: fields["velocity"][0], 1: fields["velocity"][1]}

    # Backend.to_host をパススルーする最小バックエンド
    class _PassBackend:
        xp = np
        def to_host(self, arr):
            return arr

    with tempfile.TemporaryDirectory() as d:
        writer = VTKWriter(_PassBackend(), grid, directory=d)
        cb = writer.make_callback(interval=3)
        sim = _FakeSim()

        for call_n in range(7):
            sim.step = call_n   # ステップ番号を更新して別ファイル名を生成
            cb(sim)

        # 7 回呼び出し → 3 回目 (step=2), 6 回目 (step=5) = 2 エントリ
        assert len(writer._pvd_entries) == 2, (
            f"Expected 2 PVD entries for 7 calls with interval=3, "
            f"got {len(writer._pvd_entries)}"
        )
        vtr_files = sorted(f for f in os.listdir(d) if f.endswith(".vtr"))
        assert len(vtr_files) == 2


# ── Test 8: write_step による TwoPhaseSimulation 統合 ──────────────────────

def test_write_step_from_simulation(setup):
    """write_step(sim) が TwoPhaseSimulation のフィールドを正しく書き出すこと。"""
    backend, grid = setup
    from twophase.simulation.builder import SimulationBuilder
    from twophase.config import FluidConfig, NumericsConfig, SolverConfig

    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(8, 12), L=(1.0, 1.5)),
        fluid=FluidConfig(),
        numerics=NumericsConfig(t_end=0.0),
        solver=SolverConfig(),
    )
    sim = SimulationBuilder(cfg).build()

    # ランダム初期場を設定（初期値ゼロとの区別のため）
    rng = np.random.default_rng(99)
    sim.psi.data[:]      = backend.xp.asarray(rng.standard_normal(grid.shape))
    sim.pressure.data[:] = backend.xp.asarray(rng.standard_normal(grid.shape))

    with tempfile.TemporaryDirectory() as d:
        writer = VTKWriter(backend, grid, directory=d)
        path = writer.write_step(sim, step=0)

        assert os.path.isfile(path), f"File not found: {path}"

        tree = ET.parse(path)
        root = tree.getroot()
        # XML が解析可能で RectilinearGrid タグを持つこと
        assert root.find("RectilinearGrid") is not None

        # psi フィールドの値が sim.psi.data と一致すること
        pd = root.find(".//PointData")
        psi_da = next(e for e in pd if e.attrib.get("Name") == "psi")
        psi_decoded = _decode_b64(psi_da.text)
        psi_expected = _vtk_order(np.asarray(backend.xp.asnumpy(sim.psi.data)
                                             if hasattr(backend.xp, 'asnumpy')
                                             else sim.psi.data))
        np.testing.assert_array_equal(psi_decoded, psi_expected)
