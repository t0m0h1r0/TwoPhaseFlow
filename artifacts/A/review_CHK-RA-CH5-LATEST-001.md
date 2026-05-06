# CHK-RA-CH5-LATEST-001 — Chapter 5 Latest-Narrative Strict Review

## Scope

- Target: `paper/sections/05_reinitialization.tex`, `paper/sections/05b_cls_stages.tex`
- Adjacent consistency checks: `paper/sections/03b_cls_transport.tex`, `paper/sections/03d_ridge_eikonal.tex`, `paper/sections/11_full_algorithm.tex`
- Reviewer stance: narrative coherence, notation consistency, section structure, logical consistency, and removal of research-history/version-change prose from the paper body.

## Round 1 Verdict: FAIL

### MAJOR-1 — Standard path and comparison path were still mixed

Chapter 5 still centered a long DGR / compression--diffusion story in the middle of the standard reinitialization chapter. This made DGR look like a hidden production closure rather than a comparison/diagnostic path, and it also preserved trial-history details that are not appropriate for the final paper narrative.

Fix: rewrote the DGR section as a bounded comparison-path definition only. The standard path is now explicitly Stage D Ridge--Eikonal distance reconstruction from the zero set plus Stage F `\phi`-space volume closure.

### MAJOR-2 — Mass conservation was assigned to the wrong responsibility

The original text argued through CCD/DCCD zero-sum properties inside a chapter whose latest standard path is FCCD transport plus Ridge--Eikonal projection. This blurred physical transport, geometric projection, and volume closure.

Fix: replaced the old mass-conservation subsection with a mass-budget split:
`transport + projection + closure`. Stage A owns conservative FCCD face transport, Stage D is geometric projection, and Stage F closes liquid volume with `\phi`-space correction.

### MAJOR-3 — Reinitialization frequency was written as hidden tuning history

The adaptive trigger subsection framed fixed-frequency reinitialization as a failed numerical experiment and kept the paper focused on versions and trial outcomes rather than the latest algorithm contract.

Fix: rewrote the section as execution-condition and quality-monitoring policy. `Q_\Gamma` is now a gate/diagnostic for stated benchmark conditions, not an implicit tuning rule.

### MAJOR-4 — Adjacent chapters contradicted Chapter 5's latest route

§3 still described Dissipative CCD as the main CLS transport and used "fallback" wording for Ridge--Eikonal. §11 still said profile repair inserts DGR-like `\phi_raw -> \phi_sdf` correction. These would reintroduce the obsolete Chapter 5 reading even after the local rewrite.

Fix: updated adjacent text to FCCD face-flux standard transport, "auxiliary reconstruction" wording, and Ridge--Eikonal + Stage F closure for profile repair.

### MINOR-1 — Paper prose still contained implementation-history tone

Several phrases such as "implementation mistake", "implementation guide", fixed iteration counts, and old-label/version-like comments weakened the final-paper voice.

Fix: replaced them with responsibility-confusion, acceptance criteria, discrete contracts, and reference-preservation comments.

## Round 2 Verdict: PASS

Targeted rescans found no MAJOR+ issues in Chapter 5 after remediation:

- Standard path is consistently FCCD Stage A + Ridge--Eikonal Stage D + `\phi`-space Stage F closure.
- DGR remains only as an explicitly named comparison path.
- "fallback" wording is absent from the Chapter 5 path and adjacent §3 Ridge--Eikonal references.
- Fixed-frequency/iteration-count research-history prose is removed from Chapter 5.
- Chapter 11 no longer routes profile repair through DGR.

## Validation

- Targeted terminology scans: PASS. Stale fallback/history wording is absent; DGR remains only in the explicitly marked comparison-path subsection.
- `git diff --check`: PASS.
- `make -C paper`: PASS. Generated `paper/main.pdf` with 243 pages.
- Build-log scans: PASS for fatal errors, LaTeX errors, undefined references/citations, and overfull hboxes.

## SOLID-X

Paper/docs only. No `src/twophase/`, experiment scripts, configs, or result artifacts were changed. No tested implementation was deleted. No FD/WENO/PPE fallback, hidden width regularization, or alternate pressure route was introduced.
