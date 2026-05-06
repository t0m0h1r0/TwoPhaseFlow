# CHK-RA-CH8-001 — Chapter 8 Strict Narrative Review

Date: 2026-05-06

Scope: `paper/sections/08_collocate.tex`, `08b_pressure.tex`, `08c_bf_failure.tex`, `08d_bf_seven_principles.tex`, `08e_fccd_bf.tex`, adjacent structure map.

## Round 1 Verdict: FAIL

- MAJOR-1: Chapter 8 still framed CSF body force + Balanced--Force as the standard route. This contradicted the current paper headline: pressure-jump split FCCD-PPE with affine face cochain, HFE/GFM data, DC `k=3`, and range projection.
- MAJOR-2: P-4 described `\betaf` as a factor added to CSF surface tension, which blurred the actual invariant: the same face coefficient `A_f` must be shared by PPE, corrector, and `c_f(j_{gl})=A_f B_f(j_{gl})`.
- MAJOR-3: The FCCD BF subsystem retained IIM/high-order-upgrade language, predicted-number tables, and pressure-filter-era structure, making old explorations look like the current method.
- MINOR-1: `docs/01_PROJECT_MAP.md` still referenced nonexistent `08f_pressure_filter.tex`.
- MINOR-2: Notation and reference style drift remained: `\kappa` vs `\kappa_{lg}`, `\S\ref` vs `§~\ref`, and cramped products such as `A_fG_fp`.

## Remediation

- Re-centered the chapter around `A_f G_f p - c_f(j_{gl})` and the shared `D_f A_f G_f` face complex.
- Split CSF/BF into a reduced one-fluid diagnostic path, while making pressure-jump affine face cochain + range projection the standard path.
- Rewrote P-4 as face-coefficient consistency for PPE, velocity correction, and capillary jump cochain.
- Replaced IIM/predicted-value narrative with GFM/affine-jump + HFE + DC `k=3` + range projection.
- Removed the stale `08f_pressure_filter.tex` structure-map reference.
- Normalized notation and fixed the 8章 table underfull.

## Round 2 Verdict: PASS

MAJOR+ findings: 0.

Residual risk: Chapter 2 still introduces CSF broadly as the surface-tension model, but Chapter 8 now explicitly scopes CSF to the reduced one-fluid path and points the standard route to Chapter 9's pressure-jump closure. Broader front-matter harmonization is outside this chapter-8 task.

## Validation

- Targeted terminology scans: PASS.
- `git diff --check`: PASS.
- `make -C paper`: PASS, `paper/main.pdf`, 245 pages.
- Build-log scan for fatal/error/undefined/overfull/underfull: PASS.
