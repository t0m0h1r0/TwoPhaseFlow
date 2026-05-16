# CHK-RA-CODE-GPU-003 — Ch14 capillary-wave paper revision theory policy

Date: 2026-05-16
Branch: `codex/ra-code-paper-gpu-review-20260516`
Mode: paper-revision planning only. No production source code edits and no paper text edits yet.

## Purpose

Current code verifies the Ch14 capillary-wave route at the level needed for a physical benchmark: one reference period completes, the signed mode has the restoring phase, kinetic energy stays bounded, and q-volume drift remains at roundoff scale. The paper should now be revised so that the text is supported by the actual current run and by a clean theory chain, instead of by overly precise stale numbers or ambiguous stack wording.

The revision should be theory-first. The paper must not read as "the code happened to run"; it should read as "this is the mathematical object being tested, these equations define the reference and the discrete route, and the run verifies exactly those claims."

## Pillar Theory

The capillary-wave subsection should stand on seven pillars.

| Pillar | Role in the paper | Main equations / locations |
|---|---|---|
| Continuum reference | Defines the time scale and phase landmarks, not an exact viscous/discrete waveform target. | `eq:capillary_wave_initial`, `eq:flat_capillary_dispersion` |
| q-owned interface state | The transported physical variable is cell liquid volume `q_C`; `phi/psi` are reconstructed gauges/views. | `eq:ao_geometric_compatibility`, `eq:ao_conservative_q_update`, `eq:ao_projection_problem` |
| Graph surface energy | For the capillary wave, the endpoint is the column-height graph owned by q, not a generic P1 cut-cell surface. | `eq:ao_graph_surface_energy`, `eq:ao_graph_surface_variation` |
| Graph HFE jump | The pressure jump is reconstructed from the current q-owned graph and current grid face law. | `eq:ao_graph_hfe_jump`, `eq:ao_graph_hfe_cut`, `eq:ao_graph_hfe_face_law` |
| Pressure reaction split | Only the pressure-compatible reaction space `R_p` is removed; full pressure-image overprojection is rejected. | `eq:capillary_face_covector`, `eq:pressure_reaction_subspace`, `eq:capillary_pressure_reaction_projection`, `eq:ao_full_pressure_cancellation` |
| Face-Hodge bridge | Capillary covector is mapped once to face acceleration/cochain and then interpolated to projection faces without unit duplication. | `eq:ao_hodge_divided_face_increment`, `eq:ao_projection_face_bridge` |
| Moving-grid/history separation | Projected face cochains survive grid rebuilds; pressure history stores only smooth pressure coordinates, not current jumps. | `eq:ao_face_cochain_regrid`, `eq:ao_pressure_coordinate_split` |

The Ch14 capillary section should explicitly say that the benchmark exercises all seven together. If a sentence names only "pressure jump" or only "FCCD", it should be checked against this chain.

## Derivation Policy

### 1. Continuum dispersion

Derive the reference period as an inviscid, finite-depth, two-layer small-amplitude reference:

1. Set the flat interface at `y=y0` and perturb it by `eta(x,t)=A(t) cos(kx)`.
2. In each phase, introduce a velocity potential satisfying Laplace's equation.
3. Apply impermeable wall conditions at the top and bottom, producing vertical profiles with `coth(k h_l)` and `coth(k h_g)`.
4. Linearized kinematic conditions connect `partial_t eta` to normal potential gradients.
5. Linearized Bernoulli pressure plus the Young--Laplace jump gives
   `p_g-p_l=-sigma kappa_lg`.
6. Combining them yields
   `omega^2 = sigma k^3 / (rho_l coth(k h_l) + rho_g coth(k h_g))`.

Explanation stance:

- This is the phase/time reference for the plotted landmarks `0, T/4, T/2, 3T/4, T`.
- It is not an assertion that the N=32 viscous, discrete, active-geometry run must return to exactly the initial amplitude after one period.
- Viscosity, finite resolution, discrete Hodge/PPE work, and active grid fitting can change amplitude; the acceptance claim is bounded restoring motion with correct sign and conservation, not exact analytic amplitude.

### 2. q-owned graph energy and jump

Derive graph surface energy from the transported volume:

1. Column volume is `V_i(q)=sum_j q_ij`.
2. Column height is `H_i(q)=y_min + V_i(q)/Delta x_i`.
3. Graph surface length is
   `S_G(q)=sum_i sqrt(Delta s_i^2 + (H_{i+1}-H_i)^2)`.
4. First variation gives `partial S_G / partial H_i`.
5. Pulling that variation back to the cut cell in the column gives `partial S_G / partial q_ij`.
6. The face covector is `r_sigma,G=-D_f^T d_q(sigma S_G)` under the same finite-volume sign convention as `dot q=-D_f Phi`.
7. The HFE pressure jump is the graph covector per column height,
   `j_gl,i^G = p_g-p_l = -sigma (1/Delta x_i) partial S_G / partial H_i`.

Explanation stance:

- The graph endpoint is not an implementation trick. It is what makes q, the transported volume, own the capillary surface.
- Do not describe the active capillary route as "curvature from psi" or as a regular pressure field.
- When explaining sign, use the physical statement: the crest must accelerate in the restoring direction under `j_gl=p_g-p_l=-sigma kappa_lg`.

### 3. Pressure reaction split

The paper should keep `R_p` central:

- `R_p(q_T)` is the pressure-compatible face-reaction subspace defined by the same PPE, boundary constraints, pressure representative, and metric used by the current solve.
- The physical velocity-changing capillary acceleration is
  `M_f^{-1}(r_sigma - Pi_Rp r_sigma)`.
- U12/V11 should remain the negative control: projecting onto the full pressure image can erase the non-static wave drive and must not be counted as success.

Explanation stance:

- Static cases demand near-zero residual after the pressure reaction split.
- Capillary waves demand a nonzero restoring residual after removing only the admissible pressure reaction.
- This is the conceptual reason the benchmark is meaningful: it proves the route did not "balance away" the physical capillary motion.

### 4. Face bridge, moving grid, and history

The paper should present these as unit/commutation conditions:

- `A_sigma,G=M_G^{-1} r_sigma,bal` is a face cochain/volume-flux acceleration, not a point velocity.
- Convert cochain to point face velocity exactly once before interpolation.
- Grid rebuild must transport the already projected face cochain and reproject in the new face metric.
- Pressure history extrapolates only the smooth pressure coordinate; graph HFE jump and capillary pressure reaction are current-stage objects.

Explanation stance:

- These are not performance details. They are the difference between the current valid capillary wave and earlier false routes.
- Avoid mentioning GPU packetization, parser internals, or implementation history in the paper narrative.

## Concrete Paper Revision Scope

### Chapter 14 common stack paragraph

Current issue:

- `paper/sections/14_benchmarks.tex:39` says `FCCD 保存形界面輸送 + TVD--RK3`.
- In the active-geometry capillary YAML, q transport is `geometric_swept_volume + TVD-RK3`; FCCD is the pressure/PPE/gradient side.

Revision direction:

- Replace the common wording with a split statement:
  - standard CLS route: FCCD conservative face-flux interface transport;
  - active-geometry capillary route: q-owned geometric swept-volume transport with TVD--RK3, plus FCCD pressure/PPE.
- This avoids making Ch14 capillary sound like it transports q with FCCD.

### Chapter 14 capillary-wave subsection

Keep:

- finite-depth dispersion formula and computed `T_sigma`;
- active-geometry graph-HFE route description;
- pressure Hodge representative explanation;
- qualitative conclusion: restoring sign, bounded motion, roundoff-scale volume preservation.

Update:

- terminal grid-width numbers;
- table values from the fresh current-code run;
- max/final kinetic energy;
- final/max volume drift;
- final amplitude ratio;
- any prose that says exact values rather than rounded verification facts.

Fresh values from the current run:

| Metric | Fresh run |
|---|---:|
| samples | `2585` |
| final time | `0.046742983863` |
| final `dx_min` | `6.250000000000e-04` |
| final `dy_min` | `3.919682870436e-04` |
| initial signed amplitude | `2.002821033748e-04` |
| final signed amplitude | `1.587037990392e-04` |
| final amplitude ratio | `0.792401299792` |
| max kinetic energy | `8.338458554712e-06` |
| final kinetic energy | `1.148291590869e-06` |
| final volume drift | `9.622294280809e-14` |
| max volume drift | `9.961107459711e-14` |

Recommended paper precision:

- Use 3 significant digits for diagnostic summary values unless the number is a defined input/reference time.
- Example: final ratio `0.792`, max KE `8.34e-6`, final/max volume drift `9.62e-14 / 9.96e-14`.
- Keep `T_sigma=0.046742983863 s` precise because it is a derived reference from stated physical parameters.

### V11 table and summaries

Update the row that currently repeats the old values:

- volume drift max `4.66e-14` -> `9.96e-14`;
- max KE `8.32e-6` -> `8.34e-6`;
- terminal amplitude ratio `0.794` -> `0.792`.

Do not expand V11 into a full benchmark table. V11 should remain a gate summary, while Chapter 14 owns the benchmark details.

## Claims To Avoid

Avoid these claims in the revision:

- "The N=32 result matches the continuum capillary-wave solution quantitatively over one period."
- "The analytic period proves the discrete numerical period is exact."
- "FCCD interface transport" for the active-geometry q transport route.
- "Pressure is the absolute physical pressure field" for the HFE/Hodge representative figures.
- "Full pressure-image projection succeeds" or any wording that makes U12's negative control sound admitted.
- "Roundoff-level volume drift" with too many stale exact digits; say the fresh value and/or `O(1e-13)`.

## Final Narrative Shape

Recommended sequence for the revised capillary subsection:

1. State the physical question: does a small flat-interface crest receive restoring capillary acceleration with the correct pressure-jump sign?
2. Define the continuum phase clock with the finite-depth dispersion relation.
3. Define the discrete route as q-owned graph energy, graph HFE jump, pressure reaction split, face bridge, regrid cochain, and smooth pressure history separation.
4. State the acceptance criteria before the numbers:
   - one `T_sigma` run completes without blowup;
   - signed amplitude crosses through flat/negative/positive phases;
   - KE remains bounded;
   - volume drift remains roundoff-scale;
   - snapshots are HFE/Hodge representatives, not absolute pressure fields.
5. Present rounded fresh values and figures.
6. Close by saying this validates the capillary-wave sign/route for the subsequent benchmarks, while not admitting full pressure-image overprojection or proving high-resolution convergence.

## SOLID / Scope

[SOLID-X] Paper-revision policy artifact and ledger only. No `src/twophase/`, experiment YAML, paper text, physical parameter, CFL, damping, smoothing, tolerance, production algorithm, hidden fallback, main merge, branch deletion, or worktree removal was changed.
