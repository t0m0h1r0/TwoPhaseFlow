---
id: WIKI-M-009
title: "Chapter Re-Run Methodology and Filename Normalization Convention"
status: ACTIVE
created: 2026-04-15
depends_on: []
---

# Chapter Re-Run Methodology and Filename Normalization Convention

Two procedural standards established during the ch11/ch12 full re-run
(2026-04-13 ~ 2026-04-15). Both are reusable for ch13+.

---

## Section 1 — Full Re-Run Methodology

### Trigger Condition

Re-run an entire chapter when any of the following occur:

- GPU backend migration or CuPy version change
- Major library refactoring (`src/twophase/` restructure)
- Bug fix that affects shared infrastructure (e.g., `Grid`, `Backend`, solver)
- Formal review reveals systematic measurement discrepancies

Do **not** re-run for single-experiment fixes — fix and re-run that experiment
only.

### Step 0 — Discard All Results

```bash
git rm -r experiment/chNN/results/
```

Delete every result directory (active + orphan). Partial re-runs are unreliable
because experiments share infrastructure (grid, solver, backend) and stale
cached results can contaminate comparisons.

Ch11 case: 37 directories deleted (31 active + 6 orphan) — commit `70b85d8`.
Ch12 case: 18 directories deleted — commit `728aefc`.

### Step 1 — Group by Pipeline Stage (A–E)

| Group | Pipeline Stage | Ch11 Example | Ch12 Example |
|-------|---------------|-------------|-------------|
| A | Spatial / geometry | CCD convergence, GCL, grid metrics (7/29) | Force balance (2/18) |
| B | Interface pipeline | CLS, reinitialization, remapping (15/29) | Conservation + accuracy (6/18) |
| C | Field extension + integration | HFE, Young-Laplace, NS rebuild (18/29) | Two-phase coupling (8/18) |
| D | Pressure solver | PPE variants, defect correction (26/29) | Density limit, HFE, RT, CFL (14/18) |
| E | Time integration + NS consistency | AB2/CN, CFL, full NS (29/29) | Nonuniform grid, capillary, parasitic (18/18) |

**Rationale:** Each group depends only on groups above it. A failure in Group B
isolates to interface code (spatial code already verified in Group A).
Incremental verification enables early termination and failure isolation.

### GPU Interop Bugs Surfaced During Re-Run

Three recurring patterns discovered:

1. **Sparse matrix CPU assembly** — CuPy rejects mixed host/device COO data.
   Build with `scipy.sparse.csr_matrix()` on CPU, then convert via
   `backend.sparse.csr_matrix(mat)`. See [[WIKI-L-017]] Pattern 1.

2. **Grid.meshgrid() returns N+1 points** — Cell corner coordinates, not cell
   centers. Experiment visualization code using `np.linspace(0, L, N)` causes
   dimension mismatches. Fix: use `N+1` points. See commit `b51bc6d`.

3. **CuPy array slicing** — Must call `.get()` before Python-level indexing on
   CuPy arrays. Fix: commit `8cfb02a`.

### Paper Sync Timing

Sync paper figures and tables **only after all 5 groups complete**. Do not
update paper mid-run — intermediate results may change when later groups
reveal infrastructure bugs that require re-running earlier groups.

Ch11 paper sync: commit `5daab29` (after 29/29 complete).
Ch12 paper sync: commit `752b9f3` (after 18/18 complete).

### Expected Result Changes

Re-runs are not neutral. Significant numerical changes are expected and
correct — the clean-state run is authoritative. See [[WIKI-E-021]] for
ch12 deltas (parasitic ratio 11x to 69x, capillary CFL 1.505 to 1.82,
nonuniform-grid finding reversed).

---

## Section 2 — Filename Normalization Convention

Established in commits `abd64d8` (ch11 paper) and `97be590` (ch11/ch12
scripts). Apply at chapter creation time — retroactive normalization required
updating 33 files for ch11/ch12.

### Paper Section Files

Pattern: `{NN}{letter}_{descriptive_name}.tex`

| File | Content |
|------|---------|
| `11_component_verification.tex` | Chapter-level file (no letter suffix) |
| `11a_spatial_discretization.tex` | Sub-section a |
| `11b_spatial_geometry.tex` | Sub-section b |
| `11g_summary.tex` | Sub-section g (summary) |

### Experiment Scripts

Pattern: `exp{NN}_{02d}_{topic}.py` (zero-padded to 2 digits)

| File | Content |
|------|---------|
| `exp11_01_ccd_convergence.py` | Experiment 1 |
| `exp12_16_parasitic_ccd_vs_fd.py` | Experiment 16 |

Zero-padding ensures shell glob ordering matches logical experiment order.

### Wiki Citation Updates

When experiment scripts are renamed, all wiki entries citing `sources.path`
must be updated. The ch11/ch12 normalization (commit `97be590`) updated 16
wiki files. Before renaming:

```bash
grep -r 'exp11_[0-9]' docs/wiki/    # find all citation sites
```

---

## Cross-References

- [[WIKI-L-017]] — GPU experiment patterns codified in `gpu.py`
- [[WIKI-E-021]] — Ch12 re-run result deltas
