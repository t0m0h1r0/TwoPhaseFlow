# CHK-RA-CH6-001 — Chapter 6 Strict Narrative Review

## Scope

- `paper/sections/06_scheme_per_variable.tex`
- `paper/sections/06b_advection.tex`
- `paper/sections/06c_fccd_advection.tex`
- `paper/sections/06d_viscous_3layer.tex`
- Adjacent consistency checks: §§5, 7, 8, 9, 11, 13.

## Round 1 Verdict: FAIL

- **MAJOR-1 — CLS flux is not projection-native.**  §6.1 defines the FCCD CLS flux as a Hermite face value of the nodal product `(\psi u)_i`.  The latest §11 contract transports `P_f\psi` with the canonical projected face velocity `\bu_f` from the previous projection.  Reconstructing velocity from nodal values creates a different discrete transport operator and weakens the face closure.
- **MAJOR-2 — Pressure/capillary jump narrative is stale.**  §6.0/§6.2 still presents pressure jump handling as generic GFM/IIM or CSF-baseline FCCD pressure/CSF matching.  The current standard high-density-ratio path is §9 affine-jump IPC with capillary range projection, projection-native face closure, and HFE only as one-sided Hermite data for jump-corrected face cochains.
- **MAJOR-3 — Option B/C is written as implementation migration history.**  §6.2 discusses AB2 compatibility, Stage 1/2/3 migration, product flags, and "product config".  This is not paper narrative and makes readers think all versions remain first-class standard paths.  The chapter must state the current operator roles: UCCD6 is the standard bulk momentum convection; FCCD face-flux Option B is the face-locus extension used by BF/pure-FCCD constructions; Option C is a reference/compatibility construction only.
- **MAJOR-4 — Viscous/physical-property wording leaves hidden branch logic.**  §6.3 uses masking-threshold and "drop to low order" wording that reads like an ad hoc fallback.  The intended contract is a phase-aware stress-divergence discretization: CCD is used only where smoothness assumptions hold, and interface-band one-sided/centered stencils are part of the stress law, not a fallback.
- **MINOR-1 — Stage B/F and clamp wording is inconsistent.**  §6.1 says mass correction after clamp as if it always follows every stage; §5 says Stage B is applied only when the post-transport total changes, while Stage F is the post-reinitialization `\phi`-space closure.  §6.4 says `\psi\in[\delta,1-\delta]` after clamp, while the transport clamp is `[0,1]`.
- **MINOR-2 — Research-log terms remain in the body.**  "段階移行", "製品コンフィグ", "現行実装", and legacy/comparison route notes interrupt the chapter narrative.

## Round 1 Remediation Plan

- Rewrite §6.0 as an operator-contract chapter: state current standard paths and relocate comparison/development variants to reference status.
- Rewrite §6.1 flux formulas to use projection-native face velocity `\bu_f` and `P_f\psi`, with Stage B/F responsibilities aligned to §5.
- Rewrite §6.2 as role definitions rather than migration history; align pressure/capillary statements with §8 BF principle and §9 affine-jump/range-projection.
- Clarify §6.3/§6.4 as stress-divergence and low-order property update contracts, avoiding fallback/masking language.

## Round 2 Verdict: PASS

- **MAJOR+ findings:** 0.
- §6.0 now frames the chapter as an operator-contract chapter and points pressure/capillary closure to §8 Balanced--Force plus §9 affine-jump PPE / capillary range projection.
- §6.1 now transports `P_f\psi` with the projection-native canonical face velocity `\bu_f`; it no longer defines the standard CLS flux as a nodal `(\psi u)` reconstruction.  Stage B/F responsibilities are aligned with §5.
- §6.2 now separates standard UCCD6 bulk convection from FCCD face-locus extensions; Option B/C are role definitions, not migration history or product flags.
- §6.3/§6.4 now describe the interface-band viscous treatment as a phase-aware stress-divergence law rather than a hidden low-order fallback.

## Validation

- Targeted scans for stale Chapter 6 terms: no MAJOR-relevant hits.  Remaining `GFM/IIM` is a viscosity-jump literature citation; remaining `\partial(\psi u)` appears only as the explicitly rejected nodal route.
- `git diff --check`: PASS.
- `make -C paper`: PASS, `paper/main.pdf` generated, 245 pages.
- Log scans: no fatal/error/undefined/overfull hits in `paper/main.log`.
