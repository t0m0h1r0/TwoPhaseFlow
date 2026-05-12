# CHK-RA-CH14-AO-FASTVOL-014 - AO-Fast C1 implementation

Date: 2026-05-12
Branch: `codex/ra-ch14-ao-fast-volume-20260511`

## Scope

User direction: implement according to the approved AO-Fast design policy.

Implemented only C1 from the validation ladder:

```text
dense oracle,
closed import manifest,
parser negative skeleton,
project-map governance.
```

No runtime AO-Fast projection path is connected, no chapter-14 YAML is
activated, no dense projection fallback is added, no main merge is performed,
and the direct dense-AO branch is not deleted.

## Implemented Files

```text
src/twophase/geometry/dense_reference.py
src/twophase/geometry/import_manifest.py
src/twophase/geometry/__init__.py
src/twophase/simulation/config_state_space.py
src/twophase/simulation/config_loader.py
src/twophase/simulation/config_models.py
src/twophase/tests/test_geometry_dense_reference.py
src/twophase/tests/test_geometry_import_manifest.py
src/twophase/tests/test_config_state_space.py
docs/01_PROJECT_MAP.md
```

## Contracts Fixed By C1

Dense oracle:

```text
cut_geometry_2d(grid, phi) -> dense P1 Q_h/S_h oracle,
MetricCellComplex.from_grid(grid) -> dense physical cell measures,
oracle/test-only; not exported as a runtime construction path.
```

Import manifest:

```text
ImportClassification = oracle_only | gpu_production | reject,
MigrationStatus is separate from classification,
default rows forbid dense compatibility projection as runtime fallback.
```

Parser skeleton:

```text
legacy diffuse CLS remains backward-compatible,
q/theta transport without geometric_cell_fraction is rejected,
geometric_cell_fraction validates active_cached/test_only/GPU/fallback gates,
valid geometric_cell_fraction still fails closed at parse_raw with C8-disabled
runtime message.
```

## Validation

Targeted local validation used the parent workspace venv because this worktree
has no `.venv` directory:

```text
../../../.venv/bin/python3 -m py_compile \
  src/twophase/geometry/dense_reference.py \
  src/twophase/geometry/import_manifest.py \
  src/twophase/simulation/config_state_space.py \
  src/twophase/simulation/config_loader.py \
  src/twophase/simulation/config_models.py

../../../.venv/bin/python3 -m pytest -q \
  src/twophase/tests/test_geometry_dense_reference.py \
  src/twophase/tests/test_geometry_import_manifest.py \
  src/twophase/tests/test_config_state_space.py
```

Result:

```text
py_compile PASS,
17 passed.
```

Broader regression:

```text
../../../.venv/bin/python3 -m pytest -q \
  src/twophase/tests/test_config_io_fccd.py \
  src/twophase/tests/test_config_state_space.py

../../../.venv/bin/python3 -m pytest -q \
  src/twophase/tests/test_closed_interface_geometry.py \
  src/twophase/tests/test_geometry_dense_reference.py \
  src/twophase/tests/test_geometry_import_manifest.py

../../../.venv/bin/python3 -m pytest -q src/twophase/tests
```

Result:

```text
85 passed,
16 passed,
685 passed, 33 skipped.
```

Standard remote validation was re-run after binding the available SSH agent
socket:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock ssh -o BatchMode=yes \
  python 'hostname && pwd && command -v python3 && nvidia-smi --query-gpu=name --format=csv,noheader | head -1'

SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test
```

Result:

```text
remote host python reachable,
NVIDIA GeForce RTX 3080 Ti visible,
886 passed, 3 skipped in 59.28s.
```

The earlier standard `make test` failure was due to an empty `SSH_AUTH_SOCK`;
once the socket above was supplied, the Makefile took the remote path and did
not need the local fallback.

## SOLID / Policy Notes

```text
[SOLID-S] dense oracle, import manifest, and YAML parser gates are separate
responsibilities.
[SOLID-D] config_loader depends on the parser gate, not geometry implementation.
[SOLID-X] no solver equation, pressure/PPE route, capillary route, FD/WENO/PPE
fallback, smoothing, clipping, global correction, implicit dense fallback,
implicit PCG fallback, CPU-first AO runtime path, hidden D2H control, or
chapter-14 YAML activation introduced.
```
