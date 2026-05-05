"""Checkpoint persistence for config-driven ch14 simulations.

Symbol mapping
--------------
``q^n``:
    ``psi``, ``u``, ``v``, and pressure history arrays at the saved step.
``G^n``:
    ``grid.coords`` and ``grid.h`` retained with the state so a non-uniform
    interface-fitted run resumes on the same mesh.
``M``:
    manifest containing configuration and code fingerprints.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import tempfile
from typing import Any

import numpy as np

SCHEMA_VERSION = 1
MAGIC = "twophase.ch14.restart"
RESTART_ALLOWED_CONFIG_PATHS = (
    ("run", "T_final"),
    ("run", "time", "final"),
    ("run", "snap_times"),
    ("run", "snapshots", "times"),
    ("run", "snap_interval"),
    ("run", "snapshots", "interval"),
    ("run", "print_every"),
    ("run", "time", "print_every"),
    ("run", "debug_diagnostics"),
    ("run", "debug", "step_diagnostics"),
    ("output",),
)
CODE_FINGERPRINT_ROOTS = (
    "src/twophase",
    "experiment/runner",
    "experiment/run.py",
)
WALL_SIDE_CODES = {"lo": 0, "hi": 1}
WALL_SIDE_VALUES = {value: key for key, value in WALL_SIDE_CODES.items()}
CONTACT_MODE_CODES = {"pinned_no_slip": 0}
CONTACT_MODE_VALUES = {value: key for key, value in CONTACT_MODE_CODES.items()}
ANGLE_MODE_CODES = {"initial": 0, "mirror_neutral": 1, "unspecified": 2}
ANGLE_MODE_VALUES = {value: key for key, value in ANGLE_MODE_CODES.items()}


class CheckpointError(RuntimeError):
    """Raised when a restart checkpoint fails safety validation."""


def default_checkpoint_path(outdir: pathlib.Path) -> pathlib.Path:
    """Return the default final-state checkpoint path for an output directory."""
    return pathlib.Path(outdir) / "checkpoint_final.npz"


def load_manifest(path: str | pathlib.Path) -> dict[str, Any]:
    """Load only the JSON manifest from a checkpoint file."""
    with np.load(path, allow_pickle=False) as data:
        return _decode_manifest(data["__manifest_json__"])


def save_checkpoint(
    path: str | pathlib.Path,
    *,
    solver,
    psi,
    u,
    v,
    p,
    t: float,
    step: int,
    config_path: str | pathlib.Path,
    results: dict[str, Any] | None = None,
    snapshots: list[dict[str, Any]] | None = None,
    debug_history: list[dict[str, Any]] | None = None,
) -> None:
    """Persist the full restart state with an atomic replace.

    Arrays are copied through the solver backend's explicit host boundary, so
    CUDA-backed runs write ordinary NumPy arrays without leaking device objects
    into the on-disk format.
    """
    path = pathlib.Path(path)
    config_path = pathlib.Path(config_path).resolve()
    arrays: dict[str, np.ndarray] = {}
    _put(arrays, "state/psi", psi, solver)
    _put(arrays, "state/u", u, solver)
    _put(arrays, "state/v", v, solver)
    _put(arrays, "state/p", p, solver)
    _capture_solver_state(arrays, solver)
    _capture_results(arrays, results or {}, snapshots or [], debug_history or [])
    manifest = _build_manifest(
        solver,
        arrays=arrays,
        config_path=config_path,
        t=t,
        step=step,
    )
    arrays["__manifest_json__"] = _encode_manifest(manifest)
    _atomic_savez(path, arrays)


def load_checkpoint(
    path: str | pathlib.Path,
    *,
    solver,
    config_path: str | pathlib.Path,
) -> dict[str, Any]:
    """Validate and materialize a restart checkpoint for ``solver``."""
    path = pathlib.Path(path)
    config_path = pathlib.Path(config_path).resolve()
    with np.load(path, allow_pickle=False) as loaded:
        arrays = {key: loaded[key] for key in loaded.files if key != "__manifest_json__"}
        manifest = _decode_manifest(loaded["__manifest_json__"])
    _validate_manifest(manifest, arrays=arrays, config_path=config_path, solver=solver)
    _restore_solver_state(solver, arrays)
    return {
        "t": float(manifest["time"]),
        "step": int(manifest["step"]),
        "psi": solver._backend.xp.asarray(arrays["state/psi"]),
        "u": solver._backend.xp.asarray(arrays["state/u"]),
        "v": solver._backend.xp.asarray(arrays["state/v"]),
        "p": solver._backend.xp.asarray(arrays["state/p"]),
        "results": _restore_results(arrays),
        "snapshots": _restore_snapshots(arrays),
        "debug_history": _restore_debug_history(arrays),
    }


def _build_manifest(
    solver,
    *,
    arrays: dict[str, np.ndarray],
    config_path: pathlib.Path,
    t: float,
    step: int,
) -> dict[str, Any]:
    payload_hash = hashlib.sha256()
    for key in sorted(arrays):
        payload_hash.update(key.encode("utf-8"))
        payload_hash.update(str(arrays[key].shape).encode("ascii"))
        payload_hash.update(str(arrays[key].dtype).encode("ascii"))
        payload_hash.update(np.ascontiguousarray(arrays[key]).tobytes())
    return {
        "magic": MAGIC,
        "schema_version": SCHEMA_VERSION,
        "time": float(t),
        "step": int(step),
        "backend_device": getattr(solver._backend, "device", "unknown"),
        "grid_shape": list(getattr(solver._grid, "shape", ())),
        "config_path": str(config_path),
        "config_hash_excluding_restart_allowed_paths": config_fingerprint(config_path),
        "code_fingerprint": code_fingerprint(_repo_root(config_path)),
        "payload_hash": payload_hash.hexdigest(),
    }


def _validate_manifest(
    manifest: dict[str, Any],
    *,
    arrays: dict[str, np.ndarray],
    config_path: pathlib.Path,
    solver,
) -> None:
    if manifest.get("magic") != MAGIC:
        raise CheckpointError("checkpoint magic does not match ch14 restart format")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise CheckpointError(
            f"unsupported checkpoint schema {manifest.get('schema_version')}"
        )
    expected_config = config_fingerprint(config_path)
    stored_config = manifest.get(
        "config_hash_excluding_restart_allowed_paths",
        manifest.get("config_hash_excluding_final_time"),
    )
    if stored_config != expected_config:
        raise CheckpointError(
            "checkpoint config fingerprint differs; only final time and "
            "visualization/output paths may change"
        )
    expected_code = code_fingerprint(_repo_root(config_path))
    if manifest.get("code_fingerprint") != expected_code:
        raise CheckpointError("checkpoint code fingerprint differs; refusing restart")
    if tuple(manifest.get("grid_shape", ())) != tuple(getattr(solver._grid, "shape", ())):
        raise CheckpointError("checkpoint grid shape differs from current config")
    for key in ("state/psi", "state/u", "state/v", "state/p"):
        if key not in arrays:
            raise CheckpointError(f"checkpoint missing required array {key}")
        if tuple(arrays[key].shape) != tuple(getattr(solver._grid, "shape", ())):
            raise CheckpointError(f"checkpoint array {key} shape mismatch")
    payload_hash = hashlib.sha256()
    for key in sorted(arrays):
        payload_hash.update(key.encode("utf-8"))
        payload_hash.update(str(arrays[key].shape).encode("ascii"))
        payload_hash.update(str(arrays[key].dtype).encode("ascii"))
        payload_hash.update(np.ascontiguousarray(arrays[key]).tobytes())
    if manifest.get("payload_hash") != payload_hash.hexdigest():
        raise CheckpointError("checkpoint payload hash mismatch")


def config_fingerprint(config_path: str | pathlib.Path) -> str:
    """Hash YAML after removing restart-safe time/output fields."""
    import yaml

    with open(config_path) as fh:
        raw = yaml.safe_load(fh) or {}
    canonical = _drop_nested(raw, RESTART_ALLOWED_CONFIG_PATHS)
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def code_fingerprint(repo_root: str | pathlib.Path) -> str:
    """Hash source files that can affect ch14 config-driven execution."""
    root = pathlib.Path(repo_root)
    files: list[pathlib.Path] = []
    for rel in CODE_FINGERPRINT_ROOTS:
        path = root / rel
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob("*.py") if p.is_file()))
        elif path.exists():
            files.append(path)
    digest = hashlib.sha256()
    for path in sorted(set(files)):
        rel = path.relative_to(root).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(path.read_bytes())
    git_head = _git_head(root)
    if git_head:
        digest.update(git_head.encode("ascii"))
    return digest.hexdigest()


def _capture_solver_state(arrays: dict[str, np.ndarray], solver) -> None:
    for axis, coord in enumerate(solver._grid.coords):
        arrays[f"grid/coords/{axis}"] = np.asarray(coord)
    for axis, widths in enumerate(solver._grid.h):
        arrays[f"grid/h/{axis}"] = np.asarray(widths)
    _put_optional(arrays, "solver/p_prev_dev", getattr(solver, "_p_prev_dev", None), solver)
    _put_optional(
        arrays, "solver/p_base_prev_dev", getattr(solver, "_p_base_prev_dev", None), solver
    )
    _put_list(
        arrays,
        "solver/p_prev_accel_face_components",
        getattr(solver, "_p_prev_accel_face_components", None),
        solver,
    )
    _put_list(arrays, "solver/conv_prev", getattr(solver, "_conv_prev", None), solver)
    _put_list(
        arrays, "solver/velocity_prev", getattr(solver, "_velocity_prev", None), solver
    )
    _put_list(
        arrays,
        "solver/projected_face_components",
        getattr(solver, "_projected_face_components", None),
        solver,
    )
    arrays["solver/flags"] = np.asarray(
        [
            bool(getattr(solver, "_conv_ab2_ready", False)),
            bool(getattr(solver, "_velocity_bdf2_ready", False)),
        ],
        dtype=bool,
    )
    _capture_wall_contacts(arrays, solver)


def _restore_solver_state(solver, arrays: dict[str, np.ndarray]) -> None:
    xp = solver._backend.xp
    for axis in range(solver._grid.ndim):
        solver._grid.coords[axis] = np.asarray(arrays[f"grid/coords/{axis}"])
        solver._grid.h[axis] = np.asarray(arrays[f"grid/h/{axis}"])
    solver._grid._build_metrics(ccd=solver._ccd)
    solver.X, solver.Y = solver._grid.meshgrid()
    solver._runtime_setup_ctx = None
    solver._runtime_timestep_ctx = None
    if hasattr(solver._reinit, "update_grid"):
        solver._reinit.update_grid(solver._grid)
    if hasattr(solver._ppe_solver, "update_grid"):
        solver._ppe_solver.update_grid(solver._grid)
    if hasattr(solver._ppe_solver, "invalidate_cache"):
        solver._ppe_solver.invalidate_cache()
    if getattr(solver, "_fccd_div_op", None) is not None:
        solver._fccd_div_op.update_weights()
    solver._p_prev_dev = _optional_device(arrays, "solver/p_prev_dev", xp)
    solver._p_prev = (
        None
        if solver._p_prev_dev is None
        else np.asarray(solver._backend.to_host(solver._p_prev_dev))
    )
    solver._p_base_prev_dev = _optional_device(arrays, "solver/p_base_prev_dev", xp)
    solver._p_prev_accel_face_components = _list_device(
        arrays, "solver/p_prev_accel_face_components", xp
    )
    solver._conv_prev = _list_device(arrays, "solver/conv_prev", xp)
    solver._velocity_prev = _list_device(arrays, "solver/velocity_prev", xp)
    solver._projected_face_components = _list_device(
        arrays, "solver/projected_face_components", xp
    )
    flags = arrays.get("solver/flags", np.asarray([False, False], dtype=bool))
    solver._conv_ab2_ready = bool(flags[0])
    solver._velocity_bdf2_ready = bool(flags[1])
    contacts = _restore_wall_contacts(arrays)
    solver.set_wall_contacts(contacts)


def _capture_results(
    arrays: dict[str, np.ndarray],
    results: dict[str, Any],
    snapshots: list[dict[str, Any]],
    debug_history: list[dict[str, Any]],
) -> None:
    for key, value in results.items():
        if isinstance(value, np.ndarray):
            arrays[f"results/{key}"] = np.asarray(value)
    if debug_history:
        keys = sorted(debug_history[0])
        arrays["debug/keys_json"] = _encode_json(keys)
        for key in keys:
            arrays[f"debug/{key}"] = np.asarray([entry[key] for entry in debug_history])
    if snapshots:
        arrays["snapshots/times"] = np.asarray([snap["t"] for snap in snapshots], dtype=float)
        for field in ("psi", "u", "v", "p", "rho"):
            if field in snapshots[0]:
                arrays[f"snapshots/{field}"] = np.stack(
                    [np.asarray(snap[field]) for snap in snapshots], axis=0
                )
        if "grid_coords" in snapshots[0]:
            for axis, coord in enumerate(snapshots[0]["grid_coords"]):
                arrays[f"snapshots/grid_coords/{axis}"] = np.asarray(coord)


def _restore_results(arrays: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {
        key[len("results/"):]: value
        for key, value in arrays.items()
        if key.startswith("results/")
    }


def _restore_snapshots(arrays: dict[str, np.ndarray]) -> list[dict[str, Any]]:
    if "snapshots/times" not in arrays:
        return []
    grid_coords = []
    axis = 0
    while f"snapshots/grid_coords/{axis}" in arrays:
        grid_coords.append(arrays[f"snapshots/grid_coords/{axis}"])
        axis += 1
    snapshots = []
    for idx, time in enumerate(arrays["snapshots/times"]):
        snap: dict[str, Any] = {"t": float(time)}
        for field in ("psi", "u", "v", "p", "rho"):
            key = f"snapshots/{field}"
            if key in arrays:
                snap[field] = arrays[key][idx]
        if grid_coords:
            snap["grid_coords"] = [coord.copy() for coord in grid_coords]
        snapshots.append(snap)
    return snapshots


def _restore_debug_history(arrays: dict[str, np.ndarray]) -> list[dict[str, Any]]:
    if "debug/keys_json" not in arrays:
        return []
    keys = _decode_json(arrays["debug/keys_json"])
    count = len(arrays[f"debug/{keys[0]}"]) if keys else 0
    return [
        {key: arrays[f"debug/{key}"][idx].item() for key in keys}
        for idx in range(count)
    ]


def _put(arrays: dict[str, np.ndarray], key: str, value, solver) -> None:
    arrays[key] = np.asarray(solver._backend.to_host(value))


def _put_optional(arrays: dict[str, np.ndarray], key: str, value, solver) -> None:
    if value is not None:
        _put(arrays, key, value, solver)


def _put_list(arrays: dict[str, np.ndarray], prefix: str, values, solver) -> None:
    if values is None:
        arrays[f"{prefix}/count"] = np.asarray(0, dtype=np.int64)
        return
    arrays[f"{prefix}/count"] = np.asarray(len(values), dtype=np.int64)
    for index, value in enumerate(values):
        _put(arrays, f"{prefix}/{index}", value, solver)


def _optional_device(arrays: dict[str, np.ndarray], key: str, xp):
    if key not in arrays:
        return None
    return xp.asarray(arrays[key])


def _list_device(arrays: dict[str, np.ndarray], prefix: str, xp):
    count_key = f"{prefix}/count"
    count = int(arrays[count_key]) if count_key in arrays else 0
    if count == 0:
        return None
    return [xp.asarray(arrays[f"{prefix}/{index}"]) for index in range(count)]


def _capture_wall_contacts(arrays: dict[str, np.ndarray], solver) -> None:
    """Store wall-contact constraints as numeric arrays, not JSON floats."""
    contacts = getattr(solver, "_wall_contacts", None)
    if contacts is None:
        contacts = _empty_wall_contacts()
    contact_rows = []
    for contact in contacts.contacts:
        contact_rows.append(
            [
                int(contact.wall_axis),
                WALL_SIDE_CODES[contact.wall_side],
                int(contact.tangent_axis),
                float(contact.coordinate),
                float(contact.orientation),
                CONTACT_MODE_CODES[contact.mode],
                ANGLE_MODE_CODES[contact.angle_mode],
                float(contact.level),
            ]
        )
    arrays["solver/wall_contacts/contacts"] = np.asarray(contact_rows, dtype=np.float64)
    arrays["solver/wall_contacts/trace_count"] = np.asarray(len(contacts.traces), dtype=np.int64)
    for index, trace in enumerate(contacts.traces):
        arrays[f"solver/wall_contacts/traces/{index}/meta"] = np.asarray(
            [
                int(trace.wall_axis),
                WALL_SIDE_CODES[trace.wall_side],
                int(trace.tangent_axis),
                float(trace.level),
            ],
            dtype=np.float64,
        )
        arrays[f"solver/wall_contacts/traces/{index}/tangent_coordinates"] = np.asarray(
            trace.tangent_coordinates,
            dtype=np.float64,
        )
        arrays[f"solver/wall_contacts/traces/{index}/values"] = np.asarray(
            trace.values,
            dtype=np.float64,
        )


def _restore_wall_contacts(arrays: dict[str, np.ndarray]):
    from ..levelset.wall_contact import WallContact, WallContactSet, WallTrace

    contact_rows = np.asarray(
        arrays.get("solver/wall_contacts/contacts", np.empty((0, 8), dtype=np.float64))
    )
    contacts = []
    for row in contact_rows:
        contacts.append(
            WallContact(
                wall_axis=int(row[0]),
                wall_side=WALL_SIDE_VALUES[int(row[1])],
                tangent_axis=int(row[2]),
                coordinate=float(row[3]),
                orientation=float(row[4]),
                mode=CONTACT_MODE_VALUES[int(row[5])],
                angle_mode=ANGLE_MODE_VALUES[int(row[6])],
                level=float(row[7]),
            )
        )
    trace_count = int(arrays.get("solver/wall_contacts/trace_count", np.asarray(0)))
    traces = []
    for index in range(trace_count):
        meta = arrays[f"solver/wall_contacts/traces/{index}/meta"]
        tangent_coordinates = arrays[
            f"solver/wall_contacts/traces/{index}/tangent_coordinates"
        ]
        values = arrays[f"solver/wall_contacts/traces/{index}/values"]
        traces.append(
            WallTrace(
                wall_axis=int(meta[0]),
                wall_side=WALL_SIDE_VALUES[int(meta[1])],
                tangent_axis=int(meta[2]),
                tangent_coordinates=tuple(float(v) for v in tangent_coordinates),
                values=tuple(float(v) for v in values),
                level=float(meta[3]),
            )
        )
    return WallContactSet(
        contacts=tuple(contacts),
        traces=tuple(traces),
    )


def _empty_wall_contacts():
    from ..levelset.wall_contact import WallContactSet

    return WallContactSet.empty()


def _drop_nested(raw: Any, paths: tuple[tuple[str, ...], ...]) -> Any:
    data = json.loads(json.dumps(raw, default=str))
    for path in paths:
        cursor = data
        for key in path[:-1]:
            if not isinstance(cursor, dict) or key not in cursor:
                cursor = None
                break
            cursor = cursor[key]
        if isinstance(cursor, dict):
            cursor.pop(path[-1], None)
    return data


def _repo_root(anchor: pathlib.Path) -> pathlib.Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=anchor.parent if anchor.is_file() else anchor,
            check=True,
            capture_output=True,
            text=True,
        )
        return pathlib.Path(result.stdout.strip())
    except Exception:
        cursor = anchor.resolve()
        if cursor.is_file():
            cursor = cursor.parent
        for parent in (cursor, *cursor.parents):
            if (parent / "src" / "twophase").exists():
                return parent
        return cursor


def _git_head(root: pathlib.Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _atomic_savez(path: pathlib.Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
    ) as fh:
        tmp = pathlib.Path(fh.name)
    try:
        np.savez_compressed(tmp, **arrays)
        generated = tmp.with_suffix(tmp.suffix + ".npz")
        if generated.exists():
            tmp.unlink(missing_ok=True)
            tmp = generated
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def _encode_manifest(manifest: dict[str, Any]) -> np.ndarray:
    return _encode_json(manifest)


def _decode_manifest(value: np.ndarray) -> dict[str, Any]:
    return _decode_json(value)


def _encode_json(payload: Any) -> np.ndarray:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return np.frombuffer(raw, dtype=np.uint8)


def _decode_json(value: np.ndarray) -> Any:
    return json.loads(np.asarray(value, dtype=np.uint8).tobytes().decode("utf-8"))
