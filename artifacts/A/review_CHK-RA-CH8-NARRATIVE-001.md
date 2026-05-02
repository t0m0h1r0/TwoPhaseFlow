# Review CHK-RA-CH8-NARRATIVE-001

Date: 2026-05-02  
Scope: `paper/sections/08_collocate.tex`, `paper/sections/08b_pressure.tex`, `paper/sections/08c_bf_failure.tex`, `paper/sections/08d_bf_seven_principles.tex`, `paper/sections/08e_fccd_bf.tex`, and required cross-reference edits.

## Verdict

PASS after fixes. Open FATAL: 0. Open MAJOR: 0. Open MINOR: 0.

## Reviewer Findings And Fixes

### MAJOR-1: Chapter order contradicted the promised narrative

Finding: Chapter 8 promised the order "Helmholtz -> variable-density projection -> checkerboard/BF -> FCCD", but `paper/main.tex` input the variable-density derivation and BF principles after the conclusion embedded in `08_collocate.tex`. The reader would encounter a chapter-ending paragraph before the failure modes, seven principles, and FCCD construction.

Fix: `paper/main.tex:63` now inputs only `08_collocate`; `paper/sections/08_collocate.tex:108` includes `08b_pressure`, `paper/sections/08_collocate.tex:227`--`229` include `08c`--`08e`, and the chapter conclusion remains after those inclusions at `paper/sections/08_collocate.tex:232`.

### MAJOR-2: Standard PPE wording implied an operator path not used by the BF construction

Finding: The BF root-cause paragraph could be read as saying the paper's standard PPE always evaluates the pressure gradient with the nodal CCD operator while surface tension uses another derivative. That conflicts with the later BF face-adjoint construction.

Fix: The paragraph now states this as a deliberately non-conforming counterexample at `paper/sections/08_collocate.tex:166`, then returns to the adopted CSF + Balanced--Force + FCCD face-flux construction at `paper/sections/08_collocate.tex:185`.

### MAJOR-3: Reader-external history and implementation vocabulary leaked into the paper

Finding: Chapter 8 contained terms whose meaning depends on old internal work or implementation routes: old design wording, PoC wording, `affine_jump`, H-01 diagnosis wording, `sub-system`, and solver/cache-like phrasing.

Fix: These were replaced by paper-facing terms: "BF 部分系", "FCCD 面フラックス部分系", "pressure-jump 条件", "標準 pressure-jump 閉包", "高次 pressure-jump 閉包", and "PPE 線形系". Targeted grep over chapter 8 has no remaining hits for the reviewed implementation/history terms.

### MINOR-1: Terminology around closure levels was inconsistent

Finding: GFM/IIM were variously described as practical/research closures, anti-pattern remedies, and strategy labels, weakening the narrative.

Fix: GFM is consistently the standard pressure-jump closure and IIM the high-order pressure-jump closure at `paper/sections/08d_bf_seven_principles.tex:154`, `paper/sections/08d_bf_seven_principles.tex:162`, `paper/sections/08e_fccd_bf.tex:68`, and `paper/sections/08e_fccd_bf.tex:86`.

### MINOR-2: Cross-reference label carried obsolete diagnostic naming

Finding: A chapter 10 cross-reference pointed to `sec:h01_diagnosis_fccd_remedy`, exposing an internal diagnostic name in source-level structure.

Fix: The label is now `sec:fccd_face_residual_order`; chapter 10 references the neutral label at `paper/sections/10c_fccd_nonuniform.tex:150`.

## Final Checks

- Narrative sequence: continuous projection -> variable-density PPE -> collocated-grid failure modes -> BF principles -> FCCD face-flux construction.
- Reader-facing exclusions: no old-version narrative, no implementation/class/cache/API terminology, no internal PoC/diagnostic wording in chapter 8 prose.
- Notation focus: `BF 部分系`, `FCCD 面フラックス部分系`, `face-average 条件`, `標準 pressure-jump 閉包`, and `高次 pressure-jump 閉包` are used consistently.
- SOLID audit: [SOLID-X] paper/review documentation only; no production code or module boundary changed.
