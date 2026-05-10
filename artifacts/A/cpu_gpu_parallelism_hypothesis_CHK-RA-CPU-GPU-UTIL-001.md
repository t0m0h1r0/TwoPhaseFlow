# CHK-RA-CPU-GPU-UTIL-001 - CPU parallelism hypothesis for GPU utilization

Date: 2026-05-10
Branch: `codex/ra-cpu-gpu-util-hypothesis-20260510`
Worktree: `.claude/worktrees/codex-ra-cpu-gpu-util-hypothesis-20260510`

## Question

Hypothesis: GPU utilization stays below the desired level because the run is a
single Python process with one CPU core saturated.  If CPU-side work is
distributed over multiple CPU cores, per-core CPU load may drop and GPU
utilization may improve.

## Evidence

### Passive live-run observation

Remote ch14 capillary run:

```text
PID 3132120: python3 experiment/run.py --config ch14_capillary
thread sample: one main Python thread at 99.7% CPU; other process threads 0.0%
5 s /proc sample: user 4.93 s, sys 0.05 s, total 4.98 s => 1.00 core equivalent
GPU dmon 10 samples: SM = 68, 81, 68, 57, 67, 43, 62, 70, 67, 56%
GPU pmon 5 samples for the PID: SM = 62, 62, 62, 62, 60%
```

This supports the observation that the run can pin one CPU core while still
issuing GPU work.  It does not, by itself, prove that independent CPU numerics
are starving the GPU.

### Stack samples

`py-spy dump --native` against the live capillary run repeatedly found the
active main thread inside GPU/CuPy/CUDA-library orchestration, not a
parallelizable pure-CPU numerical loop:

- `cupyx.scipy.sparse.linalg._solve.spsm` ->
  `twophase/ppe/fd_direct.py:112` ->
  `twophase/ppe/defect_correction.py:260` ->
  `twophase/simulation/velocity_reprojector_basic.py:123` ->
  grid rebuild/reprojection.
- `cusparseSpSM_analysis`, `cuMemcpyDtoHAsync_v2`, and `coosort`/`tocsc` under
  CuPy/cuSPARSE sparse solve setup.
- small CuPy operations in
  `twophase/ppe/fccd_matrixfree.py:_sync_periodic_images` and
  `PPESolverFCCDMatrixFree.apply`.
- occasional checkpoint manifest work:
  `twophase/simulation/checkpoint.py:code_fingerprint`.

Supplemental oscillating-droplet samples showed the same shape: one active
main thread with the GIL, stacks in `cupy.roll`/`face_divergence`/FCCD apply
and cuSPARSE `spSM_analysis`.  Later oscillating samples were taken while two
external oscillating runs were concurrently present, so they are supportive
but not used for elapsed-time comparison.

### CPU parallelization micro-check

The checkpoint code fingerprint path is a real host-side serial task.  An
equivalent threaded implementation was slower on the remote machine for the
current source tree:

```text
305 Python files
serial    best 8.69 ms, avg  8.81 ms
threads4  best 17.98 ms, avg 19.70 ms
threads16 best 22.31 ms, avg 23.86 ms
```

This falsifies CPU thread fan-out as a useful treatment for that observed
host-side path.  If it matters, the correct optimization is to avoid repeating
the invariant fingerprint every timestep, or only build checkpoint frames when
they can be written or needed for pre-blowup recovery.

## Verdict

The first half of the hypothesis is supported: current ch14 GPU runs can show
one saturated CPU core while other CPU cores are idle.

The second half is not supported for the current route.  The sampled hot path
is dominated by GPU-library orchestration and many small device operations
from a single CUDA/CuPy command stream, plus small checkpoint/diagnostic host
work.  Multiprocessing or CPU thread fan-out would either:

- not apply, because the active work is a stateful GPU sparse solve or kernel
  launch sequence;
- serialize on the same CUDA stream and step dependency;
- require device-to-host copies and pickling of CuPy arrays;
- create multiple CUDA contexts without a valid way to advance one coupled
  timestep state; or
- add overhead, as seen in the fingerprint micro-check.

Therefore, distributing current CPU-side work across multiple CPU cores may
make `top` look less single-core-bound, but it is unlikely to raise GPU
utilization or reduce wall time in a paper-faithful way.

## Better next targets

1. Cache or gate invariant checkpoint manifest pieces, especially
   `code_fingerprint`, and avoid full checkpoint-frame construction when no
   checkpoint/pre-blowup artifact can be written.
2. Reduce repeated cuSPARSE analysis/conversion in `PPESolverFDDirect` and the
   defect-correction base solves; preserve the same low-order `L_L` equation.
3. Fuse small FCCD matrix-free operations such as periodic sync, roll/index
   updates, and face-divergence accumulation to reduce Python->GPU launch
   granularity.
4. Continue the already-recorded WIKI-T-060/WIKI-L-026 direction: GPU-resident
   matrix-free projection and line-preconditioned Krylov, not CPU
   multiprocessing.

## SOLID

[SOLID-X] Diagnostic/docs-only verification.  No solver source, experiment
contract, pressure route, capillary force, DCCD/FCCD/UCCD kernel, reinit
physics, damping/CFL workaround, smoothing, curvature cap, benchmark branch,
fallback, or tested implementation was changed.
