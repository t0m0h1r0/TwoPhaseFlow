---
ref_id: WIKI-L-042
title: "Single-Core CPU Saturation Does Not Imply CPU-Parallel GPU Relief"
domain: code
status: ACTIVE
superseded_by: null
tags: [gpu, cpu, profiling, cupy, cusparse, parallelism]
sources:
  - path: artifacts/A/cpu_gpu_parallelism_hypothesis_CHK-RA-CPU-GPU-UTIL-001.md
    description: "Live-run CPU/GPU observation and py-spy stack evidence"
depends_on:
  - "[[WIKI-L-038]]"
  - "[[WIKI-L-039]]"
  - "[[WIKI-L-040]]"
  - "[[WIKI-T-060]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-10
---

# Single-Core CPU Saturation and GPU Relief

## Knowledge Card

A ch14 GPU run may pin one CPU core while the GPU is active, but this does not
mean that multiprocessing the CPU side will improve GPU utilization.  The
observed active thread was usually inside CuPy/CUDA/cuSPARSE orchestration
(`spSM_analysis`, sparse triangular solve, sparse conversion, small FCCD
matrix-free kernels), not a host-only numerical loop with independent chunks.

## Consequences

- First prove the active stack before proposing CPU parallelism.
- If the stack is in CuPy/cuSPARSE/kernel-launch orchestration, target
  algebra-preserving GPU work reduction: operator reuse, analysis reuse, kernel
  fusion, or device-resident Krylov/preconditioners.
- Host-only work should be removed, cached, or cadence-gated before it is
  parallelized.  For the current checkpoint code-fingerprint path, equivalent
  threaded hashing was slower than serial hashing.
- Process pools are especially suspect around CuPy arrays: they imply
  device-to-host copies, pickling, separate CUDA contexts, or invalid sharing
  of a coupled timestep state.

## Negative Knowledge

Do not treat `top` showing one Python core at 100% as proof that CPU
multiprocessing is the right GPU-utilization fix.  It is only a symptom.  The
fix depends on whether the sampled stack is a host-only computation, a CUDA
library call, a synchronization boundary, or many small GPU launches.

## Rule

For GPU-utilization work, stack-sample the live PID first.  CPU parallelization
is admissible only for a bounded, host-only, independent workload whose
parallel version is faster and does not introduce extra host/device transfer.
