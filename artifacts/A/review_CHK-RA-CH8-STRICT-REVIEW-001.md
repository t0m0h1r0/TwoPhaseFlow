# Review CHK-RA-CH8-STRICT-REVIEW-001

Date: 2026-05-02
Scope: Chapter 8 (`paper/sections/08*.tex`)
Branch: `ra-ch8-strict-review-20260502`

## Verdict

PASS after fixes. Open FATAL: 0. Open MAJOR: 0. Open MINOR: 0.

## Findings and Fixes

### MAJOR-1: Chapter roadmap did not match the actual chapter arc

The opening roadmap stopped at the Balanced--Force condition, while the chapter actually continues through failure modes, seven principles, and the FCCD face-flux subsystem. This made the second half read like appended material rather than the necessary resolution of the chapter question.

Fix: expanded the roadmap and final chapter summary so the narrative now runs as: collocated-grid problem -> equal/variable-density projection -> checkerboard/BF split -> BF failure modes -> P-1--P-7 principles -> FCCD face-flux closure.

### MAJOR-2: FCCD subsystem naming competed with the internal `FaceJet` representation

Chapter-level prose used `FCCD 面フラックス部分系`, but the decisive subsection and several local explanations used `FCCD 面ジェット`. That made the reader-facing mathematical subsystem and the internal face representation look like two different concepts.

Fix: normalized the reader-facing name to `FCCD 面フラックス部分系`; retained `\FaceJet{p}` only as the mathematical face-flux representation inside that subsystem.

### MAJOR-3: Truncation-order notation mixed `H`, `h`, and `\Delta x` without a contract

The FCCD/BF residual discussion used `\Ord{H^4}` and `\Ord{H^2}` beside `\Delta x` checkerboard notation, even though `H_f` is already used locally as a physical face distance. This overloaded `H` and blurred whether the order claim was grid-spacing or local-distance based.

Fix: normalized the FCCD/BF residual-order statements to `\Ord{\Delta x^4}` / `\Ord{\Delta x^2}` where the text discusses grid-convergence rates.

### MINOR-1: Reader-visible implementation/solver wording leaked into the theory chapter

The chapter used `CG` applicability and `求解方針` wording in places where the point is mathematical operator structure, not solver choice.

Fix: recast those passages in terms of SPD/energy identity and PPE discretization structure.

### MINOR-2: Visible notation and terminology were not fully unified

`Projection 法` / `射影法`, `BC` / `境界条件`, `bulk` / `バルク`, and `設計戦略` / mathematical closure wording were mixed in reader-visible text.

Fix: normalized visible prose to `射影法`, `境界条件`, `バルク`, and `面演算子閉包`.

## Validation

- `git diff --check HEAD~1..HEAD`: PASS
- Chapter 8 prose/notation grep for obsolete terms: PASS
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`: PASS (`paper/main.pdf`, 241 pp)
- `main.log` undefined/citation/multiply-defined/rerun grep: clean

## SOLID-X

Paper/review/ledger only. No production code boundary changed.
