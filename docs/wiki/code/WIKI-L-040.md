---
ref_id: WIKI-L-040
title: "Remote GPU Runs Must Prove the GPU Route Is Active"
domain: code
status: ACTIVE
tags: [gpu, remote_run, environment, ch14]
sources:
  - path: docs/02_ACTIVE_LEDGER.md
  - path: AGENTS.md
---

# Remote GPU Runs Must Prove the GPU Route Is Active

## Claim

Background remote experiments must verify the GPU environment and process state,
not merely start `python`.

## Effective Knowledge

- `TWOPHASE_USE_GPU=1` must be present in the remote process environment.
- `nvidia-smi` must show the experiment PID when a GPU route is expected.
- `ps`, log path, PID, and snapshot cadence should be reported when starting a
  long background job.

## Negative Knowledge

A direct background launch can silently lose the GPU route if it bypasses the
remote/make environment.  That wastes long N64 runs and makes GPU-utilization
RCA ambiguous.

## Implication

Remote-first execution remains correct, but every long background run needs a
GPU proof: process PID, environment check, `nvidia-smi`, and bounded log tail.
