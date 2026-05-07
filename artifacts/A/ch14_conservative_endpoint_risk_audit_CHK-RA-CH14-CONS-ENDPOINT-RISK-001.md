# CHK-RA-CH14-CONS-ENDPOINT-RISK-001

## Question

Before implementing the conservative face-psi endpoint capillary law, audit the
remaining risks.  The goal is not to produce comforting language; it is to make
every serious failure mode visible enough that implementation can either pass a
theorem gate or fail closed.

## Bottom Line

The implementation is feasible, but not low-risk.  The high-risk part is not
the endpoint theorem itself.  The theorem is clear:

```text
T_f(q)u_f = -D_f(P_f q u_f),
s = -M_f^{-1}T_f(q)^T d_q(sigma S_h)^T,
B_m = M_f^{-1}T_f(q)^T d_qV_m,h^T.
```

The high-risk part is preserving identity between this theorem and the actual
runtime objects:

```text
transport endpoint,
FCCD face divergence,
affine pressure_fluxes range,
face mass/reaction metric,
density/coefficient time level,
corrector face history,
GPU kernels.
```

If any of these drift apart, the code can look variational while computing a
different Hodge problem.

## Risk Register

| ID | Risk | Severity | Why It Matters | Detection | Required Mitigation |
|---|---|---:|---|---|---|
| R1 | Runtime source still calls trace-vertex cochain | Critical | `closed_interface_riesz` currently routes through `closed_interface_trace_riesz_cochain`, which is not adjoint to current `psi` transport. | Runtime seam test inspects called builder and work residual vs conservative endpoint. | Replace production call with `closed_interface_riesz_cochain`; keep trace modules diagnostic/future only. |
| R2 | Pressure range mismatch | Critical | Dense `M_f^{-1}D_f^T` projection may differ from actual `pressure_fluxes` range under phase-separated affine jump and nonuniform grid. | Manufactured pure-range cochain through `pressure_fluxes` gives `h=0`; compare dense diagnostic only as secondary. | Production projection must use `div_op.pressure_fluxes(... zero jump ...)` plus existing PPE solve. |
| R3 | Face metric mismatch | High | `cochain.face_weight_components` uses kinetic face mass, while `pressure_fluxes` range uses coefficient-weighted pressure acceleration.  If the beta metric is wrong, component reactions are not orthogonal in the correct work pairing. | Report `M_f` source and compare to `_capillary_face_hodge_weights`; component orthogonality `B^TM_fh`. | Use one declared face metric for reaction orthogonality; fail if metric/range coefficient contract is not satisfied. |
| R4 | Endpoint/material time-level mismatch | Critical | `psi_transport_endpoint` is pre-reinit, but `rho`/`mu` may be materialized from post-reinit `psi`.  Then force geometry and pressure coefficients live on different interfaces. | Store `psi_endpoint`, `psi_materialized`; report displacement/volume/surface differences before cochain build. | Either materialize capillary projection coefficients from the same endpoint, or fail if reinit/profile displacement exceeds a strict tolerance. |
| R5 | Corrector loses capillary cochain | Critical | Corrector can recompute pressure faces with `sigma=0` and without `capillary_jump_components` unless it uses stored `pressure_correction_face_components`. | Runtime test checks identical `corrected` reaches PPE RHS and corrector pressure faces. | For `closed_interface_riesz`, require stored face correction or pass capillary components through corrector kwargs explicitly; otherwise fail closed. |
| R6 | Sign convention flip | Critical | `pressure_fluxes` subtracts `capillary_jump_components`; a sign error gives anti-capillary acceleration while all norms still look finite. | Release-from-rest sign-power gate: decreasing surface energy must yield positive kinetic work. | Add a unit test with a known direction and one-step energy/velocity power check. |
| R7 | Divergence preservation broken by reaction removal | High | Subtracting full `B_m` instead of `B_m^H` changes `D_f c` and therefore changes the PPE source. | Check `D_f corrected == D_f raw` and `D_f h == 0`. | Subtract only component Hodge directions `B_m-Pi_RB_m`. |
| R8 | PPE solver mutation/caching side effects | High | External projection requires temporary zero-jump contexts and extra solves.  A stale cache silently projects with the wrong operator. | Snapshot/restore test on PPE solver graph; repeat projection after moving interface. | Centralize zero-jump projection helper with cache invalidation and restoration in `finally`. |
| R9 | GPU hot path accidentally uses host geometry | Critical | `liquid_area_gradient_2d` currently uses `array_to_numpy` and per-cell loops.  On GPU this causes sync, performance collapse, and potential CPU/GPU semantic drift. | GPU source scan and smoke with no host-loop volume gradient in production path. | Implement vectorized `xp` P1 area gradient before production; keep host graph code diagnostic only. |
| R10 | Ambiguous cells/topology changes | High | The virtual-work theorem is fixed-stratum.  Ambiguous marching-squares cells or near-threshold nodes invalidate the derivative. | GPU regularity masks, minimum crossing denominator, topology/stratum diagnostics. | Fail closed on ambiguous/near-singular strata in production strict mode. |
| R11 | Multi-component volume reactions incomplete | High | Current conservative cochain has a single sharp liquid-area covector; multiple closed components need one reaction per component. | Component count diagnostic and multi-droplet manufactured tests. | Support list-shaped `V_m` API; fail closed for multiple components until GPU component labels exist. |
| R12 | Boundary/open-interface misuse | High | Closed-interface Riesz does not automatically apply to wall-contact/open traces, rising bubbles, or Rayleigh-Taylor topology. | Trace/level-set boundary intersection check. | Restrict production source to closed regular components; fail closed on wall-contact/open topology unless a theorem exists. |
| R13 | Reinit/remap contamination | High | Grid rebuild and reinit can move or clip `psi_transport_endpoint`, invalidating work identities. | Endpoint ledger before/after remap/reinit with `Delta S`, `Delta V`, Linf displacement. | Disable or fail strict capillary cochain when remap/reinit displacement exceeds tolerance; never count this work as capillary. |
| R14 | Profile/gauge dependence | Medium/High | The conservative endpoint depends on `psi` values via `P_f q`; a different SDF/profile can change force for the same zero set. | Profile sensitivity probe: same trace, changed gauge. | Report fail-close sensitivity; if unacceptable, redesign as trace-primary, not a patch. |
| R15 | Alias/UX semantic trap | Medium | `trace_riesz` is currently an alias to `closed_interface_riesz`; after endpoint decision this name is misleading. | Config parse test for alias. | Retire/reject `trace_riesz` production alias or require an experimental trace endpoint flag. |
| R16 | Old trace documents confuse retrieval | Medium | Existing wiki/SP sections still describe trace-Riesz implementation slices. | Retrieval scan surfaces old "Trace VJP" sections before current endpoint section. | Keep current endpoint/risk sections at top-level active reading; mark trace route as future/diagnostic. |
| R17 | Static validation oracle missing | High | Sampled analytic circles are not exact finite-grid critical states, so they cannot prove static correctness. | Static gate distinguishes constructed critical state vs convergence probe. | Build manufactured/discrete-critical references before claiming static equilibrium. |
| R18 | Performance cost of extra PPE solves | Medium/High | Projecting raw plus each component reaction needs multiple PPE solves per step.  This is expensive on GPU. | GPU timing counters: capillary projection solves per step and wall time. | Cache zero-jump operator safely; keep component count small; make diagnostics opt-in.  Do not replace with a wrong dense shortcut. |
| R19 | Diagnostic host sync overhead | Medium | Scalar diagnostics via `backend.asnumpy` every step can serialize GPU execution. | GPU profiler or timing with diagnostics on/off. | Only transfer scalar gates needed for strict mode; large face fields opt-in. |
| R20 | Near-singular pressure projection | High | Cut-face coefficients and pressure gauge can make normal equations nearly singular. | Residual-verified solve and rank/condition diagnostics. | Same-equation least-squares is allowed only with residual verification; otherwise fail closed, not fallback physics. |
| R21 | Units/dt mismatch | High | Capillary cochains are accelerations, while PPE RHS and corrector scaling depend on projection `dt`. | One-step dimensional/sign test with known `dt` variation. | Keep `rhs += D_f(c)` as acceleration divergence and corrector `dt*c`; test invariance under smaller `dt`. |
| R22 | Density ratio conditioning | Medium/High | High density ratio amplifies coefficient and metric mistakes; a low-ratio test may pass. | Repeat manufactured/range/component gates at density ratio 833. | Include density-ratio gates before ch14 claims. |
| R23 | Silent non-GPU fallback | Critical | Any hidden CPU fallback violates GPU-first and can mask production infeasibility. | Static source scan and GPU smoke with CuPy arrays preserved. | No production CPU fallback for geometry/projection; diagnostics must be explicitly labelled. |
| R24 | Corrected cochain field storage cost | Medium | Optional face-field outputs can be large on GPU and NPZ/PDF workflow. | Output size check. | Default to scalar diagnostics; face cochain fields opt-in. |
| R25 | Existing trace-based results become stale | Medium | Prior N32/T10 trace-Riesz results are useful evidence against zero drive, but not validation of the chosen conservative endpoint. | Artifact labels mention trace vs conservative endpoint. | Re-run N32 static/oscillating after implementation; do not reuse trace-Riesz figures as final proof. |

## Critical Path Before Code Changes

The first implementation pass should not try to solve every risk.  It should
turn the critical risks into hard gates:

```text
Gate 1: source closed_interface_riesz no longer calls trace cochain.
Gate 2: production projection of external cochain uses pressure_fluxes range.
Gate 3: same corrected cochain reaches PPE RHS and corrector.
Gate 4: sign-power check passes.
Gate 5: GPU hot path has no host-loop volume gradient.
Gate 6: endpoint/material/reinit mismatch is measured and fails closed.
```

Only after these pass should N32 static/oscillating results be interpreted.

## Implementation Consequences

### Source Naming

Keeping `closed_interface_riesz` is acceptable only if it means
`endpoint=conservative_psi` by default.  The alias `trace_riesz` should be
removed from production aliases.  Otherwise the YAML says one endpoint while
the code computes another.

### Projection Helper

The safest implementation unit is an external-cochain projection helper:

```text
project_external_capillary_cochain(raw, B, pressure_fluxes, PPE, D_f, M_f)
```

This helper is the place to snapshot/restore solver state, zero the jump
context, validate divergence preservation, compute beta, and emit scalar
diagnostics.  Duplicating this logic in the pressure stage is too risky.

### Area Gradient

A vectorized area-gradient kernel is not an optimization nicety; it is a
correctness requirement for GPU-first production.  If it is not available, the
source should remain diagnostic or fail closed on GPU rather than secretly
using host loops.

### Endpoint Chronology

The implementation must make a deliberate choice:

```text
Option A: materialize capillary rho/coefficients from psi_transport_endpoint.
Option B: require reinit/profile displacement to be below tolerance so post-
          reinit rho is equivalent for the capillary step.
```

Using endpoint geometry with post-reinit coefficients without a gate is the
largest remaining theory/runtime mismatch.

## Risk Verdict

The route is implementable, but it needs a strict staged implementation.  The
main remaining risks are:

```text
1. endpoint/material time-level mismatch,
2. pressure range/metric mismatch,
3. corrector losing the capillary cochain,
4. GPU hot path falling back to host-loop geometry,
5. using analytic-circle static results as proof.
```

None of these should be solved with damping, CFL tuning, smoothing, curvature
caps, fallback pressure schemes, or blanket projections.  They are solved by
operator identity checks, endpoint ledgers, GPU-native kernels, and
fail-close validation.

[SOLID-X] Risk artifact only.  No production solver/config/result behavior is
changed, no tested implementation is deleted, and no FD/WENO/PPE fallback,
damping/CFL workaround, curvature cap, smoothing, benchmark branch, blanket
projection, or QP-as-physics route is introduced.
