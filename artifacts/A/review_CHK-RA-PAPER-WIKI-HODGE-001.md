# CHK-RA-PAPER-WIKI-HODGE-001

## Trigger

User requested that the knowledge gained through the recent trial sequence be
summarized in a short paper and wiki, while also reflecting the adopted findings
in the thesis manuscript.

## Scope

This is documentation/paper integration only.  No solver source, YAML runtime
route, or experiment result was changed in this CHK.

## Added Short Paper

- `docs/memo/short_paper/SP-AE_pressure_hodge_static_droplet_lessons.md`
- Registered in `docs/memo/short_paper/SP_INDEX.md`.

Main claims:

- Ridge--Eikonal is a geometric/profile projection, not a physical transport
  RHS.
- Static capillary balance is a face-wise condition, not just `D_f a_f = 0`.
- Pressure images must show a Hodge representative reconstructed from saved
  face cochains, not hide the interface band.
- Missing `pressure_accel_faces` is a data-contract failure requiring
  regeneration, not a reason to fall back to raw or masked pressure.

## Added Wiki Cards

- `WIKI-T-158`: Pressure-Hodge visualization is fail-closed, not
  interface-band masking.
- `WIKI-E-062`: Static droplet pressure images must use Hodge representatives.
- `WIKI-X-047`: Static-droplet RCA consolidates projection, geometry, and
  output contracts.

Updated:

- `WIKI-T-154` now rejects masked-band pressure output explicitly.
- `WIKI-X-041` active retrieval map now routes pressure output through
  `WIKI-T-158` and `WIKI-E-062`.
- `docs/wiki/INDEX.md` counts updated from 352 to 355 entries.

## Paper Reflection

Updated:

- `paper/sections/09b_split_ppe.tex`
  - Adds pressure-output contract after the capillary range/Hodge closure:
    visualize the Hodge representative from `a_{p,f}`, and fail closed if the
    cochain is absent.
- `paper/sections/09f_pressure_summary.tex`
  - Replaces the older "phase or Hodge representative" wording with the
    stricter Hodge representative contract and forbids hidden masked-band
    substitutes.
- `paper/sections/13b_twophase_static.tex`
  - Adds static-droplet visualization verification: N64/T1 and N32/T4 cached
    data can be redrawn as Hodge `pressure_t*.pdf` images, while
    `pressure_bulk` is not accepted.

## Validation

- `git diff --check`: PASS.
- KL-12 title/caption scan:
  - returned existing math-caption entries, but no new section/subsection/
    caption line was introduced by this CHK.
- `make -C paper`: PASS.
  - `paper/main.pdf`, 245 pages.
  - Existing overfull hbox remains in `paper/sections/09f_pressure_summary.tex:71`.
- `rg -n "LaTeX Error|Fatal error|Undefined control sequence|undefined references|Citation.*undefined" paper/main.log`:
  - no matches.

## SOLID-X

Not applicable to production source: docs/paper/wiki only.  The integrated
claim preserves the existing numerical contracts and explicitly rejects
masked-output fallback, damping, smoothing, curvature caps, blind CFL reduction,
and alternate pressure schemes.
