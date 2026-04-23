# SP-O: Paper §2–§10 SP-Core Rewrite — Design Specification and Executable Plan

- **Status**: ACTIVE — drives CHK-182..190
- **Compiled by**: ResearchArchitect
- **Compiled at**: 2026-04-23
- **Branch**: `worktree-ra-paper-rewrite-sp-core`
- **Dashboard**: [WIKI-P-013](../../wiki/paper/WIKI-P-013.md)
- **Index**: [SP_INDEX.md](SP_INDEX.md)
- **Related**: SP-A..SP-N (all), WIKI-T-046..069, WIKI-X-018..033,
  WIKI-E-030 (H-01), WIKI-L-015..031, CHK-152 (H-01 resolution),
  CHK-166/180/181 (ch13 FCCD+HFE+UCCD6 validation)

---

## Abstract

Between 2026-04-20 and 2026-04-23, the project's short-paper series
grew from three scattered design notes to a fourteen-paper theory
stack (SP-A..SP-N) that closes the H-01 metric-inconsistency problem
raised in CHK-152 and extends through the complete two-phase NS
pipeline — from geometric reinitialisation (Ridge–Eikonal) through
operator design (FCCD / UCCD6) through time integration
(Level-1/2/3) through the balanced-force projection to a pure-FCCD
DNS architecture (SP-M). The present paper manuscript
(`paper/main.tex`, §2–§10, ≈ 5,700 lines) was frozen earlier and
therefore references **none** of this work; it still presents the
old DCCD-centred narrative as if H-01 had not been diagnosed.

SP-O is the **executable specification** for bringing the manuscript
up to the current theory state. It (1) fixes the SP → chapter
mapping, (2) enumerates per-chapter revision plans as a Phase
sequence (CHK-182..190), (3) pins the cross-cutting decisions
(notation, ξ disambiguation, citation policy, A3 traceability), and
(4) acts as the source-of-truth input for every subsequent paper
chapter CHK. [WIKI-P-013](../../wiki/paper/WIKI-P-013.md) is the
companion dashboard: it tracks Phase completion status and acts as
the landing page for reviewers who need a one-screen summary.

The rewrite philosophy is **hybrid Level-1/Level-2/Level-3**: the
paper presents a continuous spectrum from SSPRK3+fully-explicit
validation runs (Level-1), through the AB2+CN+BF-projection
production path (Level-2, SP-I), to the pure-FCCD DNS configuration
(Level-3, SP-M). Each chapter anchors its operator choices in this
spectrum so that a reader can navigate from "what we actually ran
for ch13" (Level-2) to "what the architecture is capable of"
(Level-3) without the two narratives contradicting each other.

Chapter numbers §2–§10 are preserved; subsection restructuring is
free. §1 introduction, §11–§14 verification/benchmarks, and
appendices A–G receive cross-reference updates only, not rewrites.

---

## 1. Why rewrite now

### 1.1 Theory stock vs. manuscript state

The short-paper series accumulated fourteen entries in four days:

- **SP-A** (2026-04-20) — FCCD face-centred upwind: the H-01 remedy.
- **SP-B** (2026-04-20) — Ridge–Eikonal hybrid: topology/metric split
  for φ-reinitialisation.
- **SP-C** (2026-04-20) — FCCD matrix formulation: block-form,
  periodic DFT, non-uniform extension.
- **SP-D** (2026-04-21) — FCCD advection: Option B (flux-divergence)
  and Option C (Hermite face→node), BF compatibility theorem, wall
  BC Option IV.
- **SP-E** (2026-04-21) — Ridge–Eikonal on non-uniform grids: D1–D4
  extensions.
- **SP-F** (2026-04-21) — GPU-native FVM PPE: variable-batched PCR,
  matrix-free preconditioner.
- **SP-G** (2026-04-21) — Pedagogical derivation of DCCD via the
  modified-equation route.
- **SP-H** (2026-04-23, face jet) — Face-jet primitive
  $\mathcal{J}_f(u)=(u_f,u'_f,u''_f)$ as the FVM/HFE unifier.
- **SP-I** (2026-04-22) — Level-1/2/3 time integration for two-phase
  UCCD6-NS.
- **SP-J** (2026-04-22) — Balanced-force design: seven principles
  P-1..P-7, five failure modes F-1..F-5.
- **SP-K** (2026-04-22) — Viscous-term 3-layer stress-divergence with
  defect correction.
- **SP-L** (2026-04-22) — Per-variable advection policy, CLS A–F
  stages, 8-phase time step.
- **SP-M** (2026-04-23) — Pure FCCD two-phase DNS (no FVM,
  phase-separated PPE, GFM).
- **SP-N** (2026-04-21; renumbered 2026-04-23) — UCCD6 sixth-order
  upwind CCD with hyperviscosity.

The current manuscript §2–§10 cites **none** of them. `grep -c
"SP-[A-N]" paper/sections/*.tex` returns zero. The structural
mismatch is worse than a reference gap: chapters that should be
SP-B/E (ridge-eikonal) present only legacy CLS+reinitialisation;
§4 treats CCD as a finished topic and never introduces FCCD or
UCCD6; §5 time integration is written as a single scheme, not a
level hierarchy; §8 pressure/velocity coupling predates the BF
seven principles; §9 PPE predates the phase-separated FCCD PPE of
SP-M; §10 algorithm predates the 8-phase SP-L pipeline.

### 1.2 Consequences of not rewriting

- CHK-152 (H-01 resolution) and CHK-160/166/180/181 (ch13
  FCCD+HFE+UCCD6 validation) already measured FCCD and UCCD6 in
  regimes where the paper does not admit they exist. Reviewers would
  see "the paper says DCCD, the experiments run FCCD".
- The A3-traceability chain (equation → discretisation → code) breaks
  at every §4..§10 sub-section: code has moved on, equations have
  not.
- Future chapters (§13 benchmarks, §14 outlook) cannot be written
  coherently on top of a §2..§10 that omits the operator stack
  they benchmark.

### 1.3 Rewrite philosophy

1. **SP-central**: every §2..§10 subsection maps to one or more SPs
   in §3 below, and vice versa (each SP lands in at least one
   subsection).
2. **Chapter numbering preserved**, subsection reorg free. The paper
   remains §2 Governing → §3 Level-Set → §4 CCD → … → §10 Full
   Algorithm, which is the ordering reviewers already know.
3. **Hybrid Level-1/2/3 spectrum**: do not pick one configuration and
   hide the others. The paper shows the same pipeline at three
   stiffness levels and lets the reader choose.
4. **Additive where possible, replacement where necessary**. §2
   receives a tcolorbox insertion; §4 and §7–§10 receive substantial
   or full rewrites. No legacy content is deleted until its
   replacement is verified to compile.
5. **Commit granularity tracks CHK granularity**: each Phase (CHK-183
   ..190) is one reviewable commit that compiles cleanly.

---

## 2. Design thesis

### 2.1 Level spectrum as the organising axis

Every operator choice in §5..§10 is tagged with the minimum Level at
which it becomes mandatory.

| Level | Role | Integrator | Advection | Viscous | Surface tension | Projection |
|---|---|---|---|---|---|---|
| **L1** | Validation, unit tests, smooth convergence | SSPRK3 or RK4 | UCCD6 / DCCD explicit | explicit | explicit CSF | variable-ρ projection |
| **L2** | Production (ch13 default) | **AB2** + **CN** | UCCD6+AB2 | CN semi-implicit | semi-implicit linearised (Aland–Voigt) | **BF-FCCD** (SP-J matched pair) |
| **L3** | Stiff regimes / DNS | Radau IIA or fully coupled (Denner 2024) | UCCD6 inside IRK | inside IRK | fully implicit (Li 2022) | pure-FCCD phase-separated PPE (SP-M) |

Chapters §5..§10 must each answer: *which entries in this table am I
defining, and what changes at each Level?*

### 2.2 Preserved chapter scaffold

| § | Title | Rewrite type | Primary SPs |
|---|---|---|---|
| §2 | Governing equations | minor | SP-J §1 |
| §3 | Level-set / CLS | major addition | SP-B, SP-E |
| §4 | CCD / FCCD / UCCD6 | substantial rewrite | SP-G, SP-A, SP-C, SP-N, SP-H |
| §5 | Time integration | reorganised | SP-I, SP-N |
| §6 | Non-uniform grids | major addition | SP-C §5, SP-E |
| §7 | Advection / reinit | full rewrite | SP-D, SP-L, SP-K, SP-H |
| §8 | Pressure/velocity coupling | substantial rewrite | SP-J, SP-A, SP-H |
| §9 | PPE | substantial rewrite | SP-M, SP-F, SP-J §4, SP-H |
| §10 | Complete algorithm | full rewrite | SP-L, SP-I, SP-M, SP-H |

Sections §1, §11..§14, and appendices A..G remain structurally intact;
their cross-references will be retargeted in-place during the
per-phase commits.

---

## 3. SP → chapter mapping

### 3.1 Canonical table

| Chapter | Primary SPs | Secondary SPs | Equations / objects lifted |
|---|---|---|---|
| §2 | — | SP-J §1 | BF failure modes F-1..F-5 (new tcolorbox) |
| §3 | SP-B, SP-E | SP-L §3 | ξ_ridge Gaussian field, FMM reinit, D1–D4 non-uniform |
| §4 | SP-G, SP-A, SP-C, SP-N | SP-H | DCCD derivation (mod-eq), FCCD block $\mathbf{M}^\text{FCCD}$, UCCD6, face jet |
| §5 | SP-I | SP-N | L1/L2/L3 table, AB2+CN+semi-implicit ST, Denner capillary Δt |
| §6 | SP-C §5, SP-E | — | Non-uniform FCCD coefficients, D1 σ_eff / D2 Hessian / D3 non-uniform FMM |
| §7 | SP-D, SP-L, SP-K | SP-H | Options B/C, per-variable policy, 3-layer stress-divergence |
| §8 | SP-J, SP-A | SP-H | P-1..P-7, F-1..F-5, FCCD BF residual, face-jet $(1/\rho)_f p'_f$ |
| §9 | SP-M, SP-F, SP-J §4 | SP-H | Pure FCCD PPE, adjoint $D_h^\text{bf}=-(G_h^\text{bf})^*$, GPU-native PCR |
| §10 | SP-L, SP-I, SP-M | SP-H | 8-phase time step A..H, Level-selection logic, pure-FCCD DNS path |

### 3.2 SP coverage audit

Every SP must appear in at least one §2..§10 chapter. The audit
target:

- SP-A → §4.5, §8.5
- SP-B → §3.4
- SP-C → §4.5 (matrix form), §6.4 (non-uniform)
- SP-D → §7.3
- SP-E → §3.4.5, §6.5
- SP-F → §9.6
- SP-G → §4.3
- SP-H → §4.7 (intro), §7.3 (HFE reconstruction), §8.5 (FVM flux), §9.3 (HFE), §10 (pipeline)
- SP-I → §5.3–§5.5
- SP-J → §2.4 (tcolorbox), §8.3–§8.5
- SP-K → §7.6
- SP-L → §7.1, §7.5, §10.2
- SP-M → §9.2, §10.5
- SP-N → §4.6, §5.5

Audit is automated by a `grep` over `paper/sections/*.tex` at the
end of Phase 4 (§G.2 below).

---

## 4. Cross-cutting decisions

### 4.1 Notation dictionary and preamble macros

Add to `paper/preamble.tex` (Phase 0):

```latex
% --- SP-O notation macros (rewrite 2026-04-23) ---
\newcommand{\FCCD}{\mathrm{FCCD}}
\newcommand{\UCCD}[1][]{\mathrm{UCCD}#1}
\newcommand{\DCCD}{\mathrm{DCCD}}
\newcommand{\Ridge}{\text{Ridge}}
\newcommand{\EikSolve}{\mathrm{Eik}}
\newcommand{\HFE}{\mathrm{HFE}}
\newcommand{\GFM}{\mathrm{GFM}}
\newcommand{\FaceJet}[1]{\mathcal{J}_{f}\!\left(#1\right)}
\newcommand{\BF}{\mathrm{BF}}
\newcommand{\DC}{\mathrm{DC}}
% --- ξ disambiguation ---
\newcommand{\xiidx}{\xi_{\text{idx}}}     % index coordinate (§6 ALE)
\newcommand{\xiridge}{\xi_{\Ridge}}       % Gaussian-ridge auxiliary (§3.4, SP-B)
\newcommand{\omegagrid}{\omega_{\text{grid}}}  % grid-density (§6)
% --- FCCD face coefficient shorthand ---
\newcommand{\betaf}{\beta_f}              % (1/ρ)_f ≡ β_f ; fixed §8.4 P-4
```

### 4.2 ξ collision resolution

The symbol $\xi$ appears in three independent senses:

1. **Index coordinate** (§6 ALE, existing): $\xi$ is the uniform index
   coordinate mapped to non-uniform physical space by $x(\xi)$.
   Macro: `\xiidx`.
2. **Ridge auxiliary** (§3.4, SP-B new): $\xi_\text{ridge} =
   G_\varepsilon * \mathbb{1}_\text{near-interface}$, a Gaussian
   convolution used for topology-rigid reinitialisation. Macro:
   `\xiridge`.
3. **Grid-density factor** (§6.2, existing): $\omega(\xi)$ local
   grid-density; in some legacy passages written as $\xi$ factor.
   Macro: `\omegagrid`.

**Rule**: at every first use in §2..§10, the symbol is introduced
via its macro. `grep -Pzo '\\xi(?![_a-zA-Z])' paper/sections/*.tex`
must return zero hits after Phase 4.

### 4.3 β_f fixing

SP-J's P-4 "matched pair" principle makes $(1/\rho)_f$ a named
primitive. We canonicalise `\betaf` = $\beta_f \equiv (1/\rho)_f$
harmonic-averaged across interface-crossing faces
(Francois et al. 2006). Introduced in §8.4, reused in §9.2 and §10.2.

### 4.4 A3 traceability

Each equation environment in the new §2..§10 subsections is tagged:

```latex
\begin{equation}\label{eq:fccd-block}
  \mathbf{M}^\text{FCCD} \begin{pmatrix} u'_f \\ u''_f \end{pmatrix}
  = \mathbf{r}^\text{FCCD}(u)
\end{equation}
\Athree{eq:fccd-block}{SP-C §3}{src/twophase/ccd/fccd\_solver.py:L42}{test\_fccd\_convergence.py}
```

Phase 0 adds a `\Athree` macro to `preamble.tex` that emits a margin
note (suppressed in the final PDF; enabled by setting the
`\Athreedebug` flag to `1`). LaTeX does not permit digits inside
macro names, so the macro uses the spelled-out `Athree`. The full
traceability matrix becomes the new Appendix H (outside Phase 0–4;
queued as a future CHK).

### 4.5 Citation policy

Add fifteen `@techreport{sp_X_2026, ...}` entries to
`paper/bibliography.bib` (one per SP-A..SP-O). Body text cites
SPs as `\cite{sp_a_fccd_2026}`; WIKI-T/X/L entries cite as
footnotes (`\footnote{See WIKI-T-046 \url{docs/wiki/theory/WIKI-T-046.md}}`).

### 4.6 Level-tag convention

Each new subsection opens with a one-line Level tag:

> **Level coverage.** L1: explicit form (§X.Y.A); L2: semi-implicit
> form (§X.Y.B, recommended); L3: fully-coupled form (§X.Y.C).

This is the mechanism that enforces §2.1's hybrid philosophy at
reading time.

---

## 5. Phase 0 — Housekeeping (CHK-182)

### 5.1 Deliverables (this commit)

| Deliverable | Path | Size |
|---|---|---|
| SP rename | `docs/memo/short_paper/SP-N_uccd6_hyperviscosity.md` (from SP-H) | — |
| SP index | `docs/memo/short_paper/SP_INDEX.md` | ≈ 140 lines |
| **SP-O (this)** | `docs/memo/short_paper/SP-O_paper_rewrite_sp_core.md` | ≈ 800 lines |
| Wiki dashboard | `docs/wiki/paper/WIKI-P-013.md` | ≈ 150 lines |
| Preamble macros | edit `paper/preamble.tex` | +30 lines |
| Back-reference audit | SP-I, WIKI-T-062, WIKI-X-023, `src/.../uccd6.py` | 7 edits |
| Ledger entry | `docs/02_ACTIVE_LEDGER.md` | +CHK-182 |

Phase 0 does not touch `paper/sections/*.tex` (beyond `preamble.tex`).
Subsequent Phases do.

### 5.2 Phase-0 acceptance criteria

- `grep -rn "SP-H_uccd6" docs/ paper/ src/` returns zero.
- `xelatex paper/main.tex` still compiles (macro additions only).
- `docs/02_ACTIVE_LEDGER.md` `last_CHK` = `CHK-182`.

---

## 6. Per-chapter revision plans

### 6.1 §2 Governing equations (Phase 1a, CHK-183)

**Current state.** `02_governing.tex` (222) + `02b_surface_tension.tex` (48) +
`02c_nondim_curvature.tex` (235).

**Edits.**

- §2.1 (ψ, φ variable definitions): add a tcolorbox quoting SP-B §2
  "Eikonal = topology rigidity" — preview that §3.4 will replace
  traditional reinitialisation with Ridge–Eikonal.
- §2.4 (surface tension): insert new tcolorbox quoting SP-J §1
  failure modes F-1..F-5. Each mode gets one line + one-sentence
  diagnostic.
- §2.3 (non-dimensional numbers): add a subsubsection "SP index"
  listing all SP-A..SP-N (cite only, no equation content).

**Size estimate**: +80 lines total, no new .tex files.

### 6.2 §3 CLS + Ridge–Eikonal (Phase 1b, CHK-184)

**Current state.** `03_levelset.tex` + `03b_cls_transport.tex` +
`03c_levelset_mapping.tex` (701 combined). All preserved.

**Edits.**

- §3.1–§3.3: untouched except a trailing paragraph in §3.3 announcing
  the §3.4 Ridge–Eikonal replacement for the "linear advection
  reinit" of §3.3.
- **New §3.4** `03d_ridge_eikonal.tex` (≈ 150 lines, SP-B + SP-E
  combined):
  - §3.4.1 Gaussian auxiliary field $\xi_\text{ridge}$ (SP-B §3).
  - §3.4.2 Ridge set and interface definition (SP-B §4).
  - §3.4.3 Topology-change continuation (SP-B §5).
  - §3.4.4 FMM/FSM reconstruction of φ + uniqueness sketch (SP-B §6).
  - §3.4.5 Non-uniform extension D1–D4 (SP-E §3–§6).
  - §3.4.6 ε-widening and consistency with CHK-138/139 (SP-B §7).

**New file**: `paper/sections/03d_ridge_eikonal.tex`.

**main.tex edit**: append `\input{sections/03d_ridge_eikonal}`.

### 6.3 §4 CCD + FCCD + UCCD6 (Phase 1c, CHK-185)

**Current state.** `04_ccd.tex` (248) + `04b_ccd_bc.tex` (297) +
`04d_dissipative_ccd.tex` (314) = 859 lines.

**Edits.**

- §4.1, §4.2 (Chu–Fan CCD basics): preserve; add explicit
  $\omega_1, \omega_2$ symbol table (SP-N §2).
- **New §4.3** `04c_dccd_derivation.tex` (SP-G lift, ≈ 110 lines):
  first-order upwind → modified equation → DCCD embedding →
  semi-discrete eigenvalues → six-question rebuttal. The existing
  `04d_dissipative_ccd.tex` is absorbed here (its unique content
  moves into §4.3, the file itself is retired).
- §4.4 boundary conditions (existing `04b_ccd_bc.tex`): add Option
  III (SP-C §6) explicit treatment and Option IV Dirichlet (SP-D
  §8).
- **New §4.5** `04e_fccd.tex` (SP-A + SP-C combined, ≈ 180 lines):
  four FCCD design principles → fourth-order derivation → matrix
  form $\mathbf{M}^\text{FCCD}$ → periodic DFT analysis → H-01
  remedy statement.
- **New §4.6** `04f_uccd6.tex` (SP-N lift, ≈ 120 lines):
  $(-D_2^\text{CCD})^4$ hyperviscosity, exact Fourier symbols,
  discrete energy identity, CN unconditional stability, boundary
  closures.
- **New §4.7** `04g_face_jet.tex` (SP-H §2 introduction, ≈ 50 lines):
  face-jet primitive $\mathcal{J}_f(u)$ — full deployment deferred
  to §7.3, §8.5, §9.3, §10.2.
- §4.8 role table (DCCD / FCCD / UCCD6 / face-jet) replaces the
  ad-hoc comparison paragraph at the end of `04d_dissipative_ccd.tex`.

**New files**: `04c_dccd_derivation.tex`, `04e_fccd.tex`,
`04f_uccd6.tex`, `04g_face_jet.tex`.

**Retired**: `04d_dissipative_ccd.tex` (content absorbed into §4.3).

**Size delta**: +500 lines, +4 .tex files, -1 .tex file.

### 6.4 §5 Time integration (Phase 2a, CHK-186)

**Current state.** `05_time_integration.tex` (305).

**Edits.** Restructure (no new .tex file):

- §5.1 accuracy consistency (preserve).
- §5.2 operator-wise stiffness analysis (SP-I §2 lift).
- §5.3 **Level 1** — SSPRK3 fully explicit (SP-I §3.1).
- §5.4 **Level 2** — AB2 + CN + semi-implicit ST + BF projection
  (SP-I §3.2, recommended default).
- §5.5 **Level 3** — Radau IIA or Denner fully coupled (SP-I §3.3;
  stiffness-regime only).
- §5.6 capillary Δt as wave-resolution bound (SP-I §1,
  Denner–van Wachem 2015/2022).
- §5.7 CN cross-term trap (preserve + WIKI-T-003 footnote).

**Size estimate**: +250 lines, 0 new files.

### 6.5 §6 Non-uniform grids (Phase 2b, CHK-187)

**Current state.** `06_grid.tex` (288) + `06b_ccd_extensions.tex` (61).

**Edits.**

- §6.1–§6.3 (density function + coordinate transform + CCD
  non-uniform): preserve.
- **New §6.4** `06c_fccd_nonuniform.tex` (SP-C §5 lift, ≈ 90 lines):
  FCCD coefficients for $x(\xi)$ mesh, $\mathcal{O}(H^3)$ truncation,
  cached non-uniform divergence weights (cf. recent commit
  `add16d0`).
- **New §6.5** `06d_ridge_eikonal_nonuniform.tex` (SP-E §3–§7 lift,
  ≈ 120 lines): D1 σ_eff, D2 physical-space Hessian, D3 non-uniform
  FMM, D4 ε(x) spatial-dependent widening.
- §6.6 ALE overview (preserve).

**New files**: `06c_fccd_nonuniform.tex`, `06d_ridge_eikonal_nonuniform.tex`.

### 6.6 §7 Advection / reinitialisation (Phase 3a, CHK-188)

**Current state.** `07_advection.tex` (332) + `07b_reinitialization.tex` (581).

**Edits.**

- **New §7.1** `07_0_scheme_per_variable.tex` (SP-L §3 lift; opens the
  chapter, ≈ 60 lines): the per-variable advection policy — ψ →
  WENO5/DCCD; $u,v$ bulk → CCD; $u,v$ interface band → WENO;
  φ → WENO-HJ; $p$ → face-flux + GFM; $\rho, \mu$ → low-order.
- §7.2 CLS advection via DCCD (preserve + SP-D forward reference).
- **New §7.3** `07c_fccd_advection.tex` (SP-D full lift, ≈ 220 lines):
  common primitives $\mathbf{P}_f, \mathcal{J}_f$; Option C 4th-order
  Hermite face→node; Option B conservative face-flux divergence; BF
  compatibility theorem (SP-D §7.2); wall BC Option IV.
- §7.4 CLS reinitialisation (preserve + cross-ref to §3.4).
- **New §7.5** `07d_cls_stages.tex` (SP-L §5, ≈ 80 lines): CLS A–F
  six stages.
- **New §7.6** `07e_viscous_3layer.tex` (SP-K §3–§5, ≈ 140 lines):
  3-layer stress-divergence, $\mu \nabla^2 u$ prohibition across
  μ-jumps, defect-correction split.

**New files**: 4 new .tex, 0 retired.

### 6.7 §8 Pressure/velocity coupling (Phase 3b-α, CHK-189a)

**Current state.** `08_collocate.tex` (427) + `08b_pressure.tex` (144) +
`08c_pressure_filter.tex` (3, stub).

**Edits.**

- §8.1, §8.2 (collocated + variable-density projection): preserve.
- **New §8.3** `08_0_bf_failure.tex` (SP-J §1, ≈ 45 lines): F-1..F-5
  with CHK-172 rising-bubble application.
- **New §8.4** `08_1_bf_seven_principles.tex` (SP-J §2 full lift,
  ≈ 160 lines): P-1..P-7. Principle P-4 introduces $\betaf$.
- **New §8.5** `08_2_fccd_bf.tex` (SP-A + SP-H §3 + SP-J §3 combined,
  ≈ 130 lines): H-01 diagnosis → FCCD BF construction → face-jet
  realisation of $\beta_f p'_f$ → hydrostatic-test forward reference.
- §8.6 pressure-filter prohibition: promote the 3-line stub
  `08c_pressure_filter.tex` to an explicit P-5 instantiation (SP-J §2.5).

**New files**: 3 new .tex, `08c_pressure_filter.tex` expanded in-place.

### 6.8 §9 Pressure Poisson equation (Phase 3b-β, CHK-189b)

**Current state.** `09_ccd_poisson.tex` (207) + `09b_split_ppe.tex` (110) +
`09c_hfe.tex` (227) + `09d_defect_correction.tex` (123) +
`09e_ppe_bc.tex` (91) + `09f_pressure_summary.tex` (107) = 865.

**Edits.**

- §9.1 CCD Poisson matrix (preserve).
- §9.2 phase-separated FCCD PPE: expand existing `09b_split_ppe.tex`
  by ≈ 160 lines (SP-M §5–§8 lift) — pure FCCD PPE + adjoint
  $D_h^\text{bf} = -(G_h^\text{bf})^*$.
- §9.3 HFE: augment existing `09c_hfe.tex` with face-jet-based
  left/right state reconstruction (SP-H §4, ≈ 30 lines).
- §9.4 defect correction: augment with SP-M §9 "DC resolves the outer
  stiffness of pure FCCD" (≈ 20 lines).
- §9.5 boundary conditions: SP-C §6 Option III and SP-D §8 Option IV
  explicit.
- **New §9.6** `09_6_gpu_native_fvm.tex` (SP-F full lift, ≈ 130 lines):
  face-local operator calculus, variable-batched PCR, matrix-free
  multigrid preconditioner.
- §9.7 summary: pure FCCD vs GPU-native FVM two-path decision table.

**New files**: 1 new .tex (§9.6); 3 existing files expanded.

### 6.9 §10 Complete algorithm (Phase 4, CHK-190)

**Current state.** `10_full_algorithm.tex` (459) + `10b_dccd_bootstrap.tex` (160).

**Edits.**

- §10.1 operator mapping: preserve + add FCCD / UCCD6 / HFE / GFM
  role table.
- §10.2 **8-phase time step** (SP-L §6 full lift, ≈ 220 lines):
  expand the existing 7-step listing to A CLS advection → B
  reinit → C geometry → D hydrostatic separation → E predictor →
  F BF-FCCD projection → G velocity correction → H diagnostics.
- **New §10.3** `10_3_level_selection.tex` (SP-I §3, ≈ 80 lines):
  Level-switch triggers + cost/accuracy trade-off.
- §10.4 DCCD parameters (preserve `10b_dccd_bootstrap.tex` + SP-J
  P-5 annotation that the filter is applied *after* the projection).
- **New §10.5** `10_5_pure_fccd_dns.tex` (SP-M full lift, ≈ 150 lines):
  Phase 1–4 pure FCCD architecture + Level-3 operating envelope.
- §10.6 bootstrap: preserve + Appendix G cross-ref.

**New files**: 2 new .tex.

---

## 7. Implementation phases and commit granularity

### 7.1 Phase table

| Phase | CHK | Scope | New .tex | Edited .tex | LOC (approx) |
|---|---|---|---|---|---|
| 0 | CHK-182 | SP rename, SP_INDEX, SP-O, WIKI-P-013, preamble macros, ledger | 0 | 1 (preamble) | +1,200 md / +30 tex |
| 1a | CHK-183 | §2 minor + §1.5 SP index | 0 | 3 | +80 |
| 1b | CHK-184 | §3.4 Ridge–Eikonal | 1 | 1 (main.tex) | +150 |
| 1c | CHK-185 | §4 rewrite (FCCD / UCCD6 / face-jet) | 4 | 3 | +500, −314 |
| 2a | CHK-186 | §5 L1/L2/L3 restructure | 0 | 1 | +250 |
| 2b | CHK-187 | §6 non-uniform FCCD + ridge | 2 | 1 | +210 |
| 3a | CHK-188 | §7 per-variable + FCCD advection + viscous 3-layer | 4 | 2 | +600 |
| 3b | CHK-189 | §8 BF + §9 FCCD PPE + GPU-native | 5 | 5 | +700 |
| 4 | CHK-190 | §10 8-phase + Level + pure-FCCD DNS | 2 | 2 | +500 |

Running totals: **18 new .tex files**, **~3,200 new LOC** on top of
the existing ≈ 5,700-line §2..§10 stack, plus ≈ 1,200 lines of
short-paper/wiki metadata in Phase 0.

### 7.2 Per-phase commit discipline

Each Phase:

1. `xelatex paper/main.tex && xelatex paper/main.tex` must both
   succeed with zero `Reference ... undefined` warnings.
2. `grep -c '\\label' paper/sections/*.tex | awk -F: '{s+=$2}END{print s}'`
   must be monotone non-decreasing across phases (no label deletions
   without replacement).
3. `docs/02_ACTIVE_LEDGER.md` appended with a `CHK-18N` entry
   pointing at the commit hash.
4. One `git commit` per Phase; force-push forbidden. Merge into
   `main` only after Phase 4 + PaperReviewer sign-off.

### 7.3 Branch and worktree

- Branch: `worktree-ra-paper-rewrite-sp-core`
- Worktree: `.claude/worktrees/ra-paper-rewrite-sp-core/`
- Cloned from `main` at Phase 0 start (HEAD = `e0f990e` at this
  writing).

---

## 8. Verification plan

### 8.1 LaTeX build

```bash
cd paper && latexmk -xelatex -interaction=nonstopmode main.tex
```

- Warning-free compile.
- `grep 'Reference.*undefined' main.log` returns empty.
- Page count monotone-increasing across Phases (sanity check; not
  a hard gate).

### 8.2 SP coverage audit

```bash
for sp in A B C D E F G H I J K L M N; do
  hits=$(grep -rc "sp_${sp,,}_" paper/sections/ 2>/dev/null | \
         awk -F: '{s+=$2}END{print s+0}')
  echo "SP-${sp}: ${hits}"
done
```

Every SP returns `≥ 1`. SP-O is not cited (it is the plan, not an
output).

### 8.3 Existing §11/§12 impact audit

- Numerical-result tables in §11/§12 must not change values (we are
  not re-running experiments). Diff against pre-rewrite tags:
  `git diff main -- paper/sections/11_*.tex paper/sections/12_*.tex`
  should be empty or cross-reference-only.
- `make test` on remote returns green (pipeline not touched).

### 8.4 Notation collision audit

```bash
grep -Pzo '\\xi(?![_a-zA-Z])' paper/sections/*.tex
```

Zero hits after Phase 4 (all uses go through `\xiidx`, `\xiridge`, or
`\omegagrid`).

### 8.5 Ledger append

`docs/02_ACTIVE_LEDGER.md` receives one entry per Phase
(CHK-182..190) + a terminal `Rewrite complete` line with commit
hash.

### 8.6 Pre-PR review

Before the final merge, run the PaperReviewer agent (per `PR-6` in
`docs/03_PROJECT_RULES.md`). Address any `[CRITICAL]` or `[MAJOR]`
findings before merge.

---

## 9. Out of scope and queued follow-ups

**Out of scope for CHK-182..190**:

- §1 introduction prose (minor cross-ref updates only).
- §11 numerical verification (new SP-derived convergence tables are
  queued as CHK-191).
- §12 physical verification (existing results retained verbatim).
- §13 benchmarks, §14 outlook.
- Appendices A–G (structural).
- `src/twophase/**` implementation changes (no code rewrites; the
  rewrite is documentation-only).

**Queued follow-up CHKs**:

- CHK-191 — §11 SP-derived convergence tables (FCCD $\mathcal{O}(H^3/H^4)$,
  Ridge–Eikonal p99, GPU-native FVM speed-up).
- CHK-192 — Appendix H A3-traceability matrix (equation →
  discretisation → code → test, full coverage).
- CHK-193 — §13 additional benchmarks for pure-FCCD DNS (SP-M).
- CHK-194 — `bibliography.bib` normalisation (SP entries + existing
  citation audit).

---

## 10. Execution checklist (Phase 0, this commit)

- [x] Worktree `ra-paper-rewrite-sp-core` created from `main`.
- [x] `SP-H_uccd6_hyperviscosity.md` → `SP-N_uccd6_hyperviscosity.md`
      (git mv).
- [x] SP-N header updated with rename note.
- [x] SP-I back-references updated (6 edits).
- [x] WIKI-T-062 back-references updated (4 edits).
- [x] WIKI-X-023 back-reference updated (1 edit).
- [x] `src/twophase/ccd/uccd6.py` docstring back-reference updated.
- [x] `SP_INDEX.md` created.
- [x] `SP-O_paper_rewrite_sp_core.md` (this file) created.
- [ ] `WIKI-P-013.md` created.
- [ ] `paper/preamble.tex` macros added.
- [ ] `docs/02_ACTIVE_LEDGER.md` CHK-182 appended.
- [ ] Phase-0 commit created.

Subsequent Phases inherit this template: one checklist per CHK, one
commit per checklist.
