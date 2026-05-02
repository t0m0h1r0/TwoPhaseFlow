# CHK-RA-CH10-NARRATIVE-005 — Chapter 10 strict review

- Date: 2026-05-02
- Context: after no-ff merge `c1cffed6` into `main`, the retained worktree `ra-ch10-narrative-20260502` was reviewed again without merging the new work back to `main`.
- Scope: `paper/sections/10_grid.tex`, `paper/sections/10d_ridge_eikonal_nonuniform.tex`

## Reviewer Findings and Fixes

### MAJOR-1 — epsilon notation mixed three roles

The chapter still allowed a reader to read bare `\varepsilon` as all of:

- CLS/CSF interface thickness,
- grid-density smoothing width,
- Ridge--Eikonal reconstruction width.

This was a root narrative defect because Chapter 10 argues that the standard path is fixed-width CLS/CSF on non-uniform grids. If the symbols are not separated, the later constrained spatial-variable-width discussion appears to weaken the standard path rather than delimit a different assumption.

Fix:

- CLS/CSF interface thickness is now consistently written as `\varepsilon_\Gamma`.
- Grid-density smoothing uses `\varepsilon_g`, and its monitor delta is renamed from `\delta_\varepsilon^*` to `\delta_g^*`.
- Ridge--Eikonal reconstruction width uses `\varepsilon_\text{local}` with the dimensionless scaling `\varepsilon_{\mathrm{RE},\xi}` and base width `\varepsilon_{\mathrm{RE}}`.
- The D4 text explicitly states that `\varepsilon_\text{local}` is distinct from the CLS/CSF thickness `\varepsilon_\Gamma` and does not license spatially variable `\delta_{\varepsilon_\Gamma}` in the standard path.

### MAJOR-2 — Ridge--Eikonal closure title under-described the section

The section title named only D1--D4 even though wall closure `W` is part of the logical closure. This weakened the reader's map: the section was not merely a list of four correctors but a closure of discrete geometry on non-uniform grids.

Fix:

- The title now frames the section as D1--D4 plus wall closure.
- The opening paragraph identifies D1--D4 and W as one coherent closure set.

### MINOR-1 — fixed-width standard path needed local notation cleanup

The multi-interface diagnostic and spatial-variable-width subsection still used unqualified epsilon notation. That left visible friction between the chapter map and the later constraints.

Fix:

- The multi-interface proximity scale now uses `\varepsilon_\Gamma`.
- Spatial-variable cell-count notation is now `N_{\Gamma,\text{cells}}`.
- The CSF delta in that subsection is written as `\delta_{\varepsilon_\Gamma}`.

## Verification

- `git diff --check`: PASS
- Prohibited visible implementation/old-version term guard for Chapter 10: PASS
- Bare-epsilon and obsolete-token guard: PASS
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`: PASS (`paper/main.pdf`, 240 pages)
- `main.log` undefined/multiply-defined/rerun grep: clean
- [SOLID-X] Paper/review documentation only; no production code boundary changed.
