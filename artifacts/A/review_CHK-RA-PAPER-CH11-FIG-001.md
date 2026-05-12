# CHK-RA-PAPER-CH11-FIG-001 — Figure 2 / Figure 7 Consistency Review

Date: 2026-05-12
Branch: `codex/ra-paper-review-ch11-20260512`
Scope: Figure 2 (`fig:algo_flow`) and Figure 7 (`fig:ns_operator_map`) with their caption notes.

## Review Units

| Unit | File | Rounds | Result |
|---|---|---:|---|
| Figure 2: one-timestep flow | `paper/sections/01b_classification_roadmap.tex` | 6 | No MAJOR+ remains |
| Figure 7: NS term/operator map | `paper/sections/11_full_algorithm.tex` | 4 | No MAJOR+ remains |

No unit reached the 20-round cap.

## Findings And Fixes

### Figure 2

- MAJOR: The old layout did not match the paper narrative. It drew only a standard interface/fluid split and omitted the active-geometry route, even though Figure 2 is the reader's first map of how interface computation feeds capillarity.
  - Fix: Redrew the figure from the ground up as two rows: a solid standard path and a dotted developmental active-geometry path.
- MAJOR: Placing the active-geometry method only after capillary closure lost the fact that, in the AO-derived theory, `phi`/`psi` are reconstructed from the geometric state. This made the branch look like a late pressure-jump alternative rather than a reinitialization-like interface-state reconstruction.
  - Fix: Repositioned the developmental path as `q_C` transport -> compatible geometry reconstruction `q_C -> Gamma_h -> phi, psi` -> geometric capillary decomposition -> fluid update only after adoption. The prose before the figure and the caption now state that this path starts by rebuilding derived gauges `phi, psi`.
- MAJOR: The earlier "capillary closure -> next" relation was visually broken, so the developmental branch did not clearly reconnect to downstream physics.
  - Fix: Added an explicit adoption-gated connection to the fluid update and clarified that it is allowed only after the U12/V11 boundary.
- MAJOR: Box sizes and abstraction levels were inconsistent across the standard and developmental paths.
  - Fix: Made all figure boxes share one `flowbox` geometry and rewrote labels as stage-level roles plus state/output, e.g. `CLS 移流 (psi)`, `標準再初期化 (phi, psi)`, `幾何互換再構成 (q_C -> Gamma_h -> phi, psi)`, and `幾何毛管分解 (r_sigma, R_p)`.
- MINOR: The initial four-column redraw exceeded the text width.
  - Fix: Kept the four logical columns but reduced the uniform box width and inter-column spacing; the build now has no overfull/underfull warning matches in the checked pattern.

### Figure 7

- MAJOR: The old operator map mixed detailed implementation phrases with high-level NS terms and did not reflect the revised Chapter 11 standard/developmental distinction.
  - Fix: Redrew the map as `NS term -> closure/discretization` pairs with uniform box sizes: advection, pressure, viscosity, gravity, and surface tension.
- MAJOR: The surface-tension column made the active-geometry method look like a second standard capillary operator.
  - Fix: Kept `標準毛管閉包（圧力ジャンプ）` as the standard operator and added a dotted developmental box `幾何毛管分解（q_C -> phi/psi）`; the caption states that the route first reconstructs compatible geometry and derived gauges before it can become a capillary-force candidate.
- MINOR: Earlier labels mixed method names, residual policies, and implementation details at different abstraction levels.
  - Fix: Standardized each box to a role plus a short parenthetical mechanism, moving detailed conditions to the caption.

## Final Review Result

Figure 2 now presents active geometry as a reinitialization-like interface-state reconstruction path: `q_C` owns transported volume, compatible geometry reconstructs `Gamma_h`, and `phi, psi` are derived from that geometry before capillary decomposition is considered. Figure 7 now keeps the standard pressure-jump surface-tension operator separate from the developmental geometric capillary decomposition and makes the adoption boundary explicit in the caption. MAJOR or BLOCKER findings remaining: none.

## Verification Executed

- `git diff --check` — PASS.
- `make -B -C paper` — PASS; `paper/main.pdf` rebuilt.
- `paper/main.log` warning/error/undefined-reference scan — PASS; no matches in the checked warning/error pattern.
- Rendered and visually checked the PDF pages containing Figure 2 and Figure 7.
