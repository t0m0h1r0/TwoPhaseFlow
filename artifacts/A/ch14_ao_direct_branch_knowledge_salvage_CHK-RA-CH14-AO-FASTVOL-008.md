# CHK-RA-CH14-AO-FASTVOL-008 - Direct AO branch knowledge salvage

Date: 2026-05-12
Branch: `codex/ra-ch14-ao-fast-volume-20260511`
Retirement candidate branch: `codex/ra-ch14-osc-sharp-volume-20260510`
Reference tip inspected: `3ead1e6a`
Worktree: `.claude/worktrees/codex-ra-ch14-ao-fast-volume-20260511`

## Scope

User direction: when importing from the direct-AO branch, preserve important
knowledge as well as code, because the direct branch is expected to be
discarded after this work.

This checkpoint is the branch-retirement knowledge packet.  No solver source is
changed, no branch is deleted, and no chapter-14 YAML is activated.

## Retirement Rule

`codex/ra-ch14-osc-sharp-volume-20260510` may be deleted only after AO-Fast no
longer depends on it for facts.  The minimum facts to preserve are:

```text
exact dense oracle formulas and tests,
fail-close gates discovered during direct implementation,
runtime/checkpoint handoff invariants,
GPU/D2H performance lessons,
negative knowledge from failed sharp-volume runs,
chapter-14 activation caveats and diagnostic/plotting gates.
```

This artifact is the stable index for those facts.  The direct branch may still
be a code source until actual migration is complete, but it is no longer a
knowledge SSoT.

## Salvaged Knowledge

### Parser and state-space gates

```text
interface.state_space.kind must be explicit,
diffuse_cls rejects geometric keys,
diffuse/default stacks reject q/theta transport variables,
geometric projection residual tolerance must be positive finite,
local derivative scatter requires exact (Nx,Ny,4) shape,
non-2D grids fail before geometry construction.
```

AO-Fast implication: the parser must reject ambiguous declarations before any
runtime route can fall through to legacy `psi` transport.

### Geometry oracle facts

The dense branch established exact P1/Q1 formulas for:

```text
Q_h(phi), theta=Q_h/|C|, S_h(phi), J_q=dQ_h/dphi, dS_h/dphi.
```

Critical fixes:

```text
cut-cell complement volume must be preserved,
degenerate sign strata are rejected, not regularized,
nonuniform cells use physical coordinates,
periodic-style duplicated edge storage is not two physical degrees of freedom.
```

AO-Fast implication: active kernels must match this dense oracle on regular
manufactured strata and must not smooth, clip, or infer derivatives at
zero-valued nodal signs.

### Compatibility projection facts

The dense Stage 2 projection used:

```text
S_q lambda = J_q J_q^T lambda = target_q - Q_h(phi),
delta_phi = J_q^T lambda.
```

Accepted facts:

```text
project in physical q units,
line-search against sign/case margin,
fail close if target q changes full/empty cells outside the fixed stratum,
record iterations, residuals, sign margin, Delta S_Pi, and minimum step,
large stratum-crossing targets are not repaired.
```

AO-Fast implication: keep the mathematical contract but replace dense arrays,
dense line search, and scalar-host CG control with active cached rows and
device-resident reductions.

### Swept flux and common-flux facts

```text
wall closure requires zero boundary phase flux,
periodic closure requires matching lower/upper boundary fluxes,
final q must satisfy 0 <= q <= |C| without clipping,
global q conservation is checked after declared boundary closure,
common mass flux Phi_m uses the exact same Phi_l and Phi_V arrays,
nonfinite inputs/outputs fail closed,
nonaffine swept donor strips and stale phase transport states fail closed,
capacity-neutral swept throughput is allowed only when the q-capacity ledger
certifies it.
```

AO-Fast implication: dirty active rows must include flux-capacity and closure
certificates, not just cut-geometry rows.

### Capillary Hodge/Riesz facts

```text
c = -sigma dS_h,
J_q J_q^T lambda = J_q c,
r_sigma = T_q^T lambda,
a_sigma = M_f^{-1} r_sigma.
```

Important review fixes:

```text
periodic seam face-Hodge weights are split over duplicated storage endpoints,
periodic boundary calls require periodic phi endpoints,
periodic incidence adjoints split seam covectors consistently,
pressure_hodge may fail closed when a face cochain is not scalar-pressure
integrable,
component-volume reaction directions are removed by a small Hodge least-squares
system and must be orthogonal in the M_f metric.
```

AO-Fast implication: capillary runtime may consume active geometry, but it must
preserve face-Hodge identities and periodic quotient rules.  Scalar pressure
plots are diagnostics; `pressure_hodge` is a stricter representation gate.

### Runtime and checkpoint facts

```text
build_ic attaches the typed GeometricPhaseState,
step_request without a runtime geometric state must fail closed,
geometric_swept_volume cannot silently enter legacy common-flux psi transport,
stale AO transport diagnostics must be cleared,
runtime material, face-Hodge, capillary-Hodge, capillary-range, nodal-drive,
and capillary-application packets must validate state identity,
checkpoint restart validates q/phi and pressure-history face arrays on the
actual projection face lattice before the next step consumes them.
```

AO-Fast implication: active caches are restart state.  Their identity, topology,
and face-history shape must be validated at load time.

### Chapter-14 activation caveats

```text
regular P1 strata cannot start with exact zero-valued grid nodes,
radius/phase nudges were used only to avoid degenerate initial geometry,
one-step ch14 smoke tests showed zero q-volume drift,
production-length chapter-14 AO success was not established,
canonical pressure snapshots should use scalar gauge pressure,
pressure_hodge remains an explicit fail-close diagnostic,
dense direct AO is too expensive to become the production route.
```

AO-Fast implication: chapter-14 YAML activation should wait for active-vs-dense
equality, dirty-refresh, no-inner-D2H, restart, and runtime gate tests.

### GPU lessons

```text
MetricCellComplex cache keeps backend-resident edge and cell-measure arrays,
coordinate cache invalidation handles replacement and in-place edits,
P1 geometry, derivatives, swept flux, total flux, and face Hodge weights reuse
cached metric arrays,
projection carries current/accepted Q_h geometry through Newton and line search
to avoid duplicate cuts,
remote CUDA geometry suite passed after cache optimization,
short remote capillary GPU computation saved AO q/phi/density with zero q drift.
```

AO-Fast implication: these optimizations are mandatory baseline knowledge, not
the final fast design if scalar host residual checks or dense cell-shaped
vectors remain.

### Negative knowledge

The oscillating-droplet sharp-volume rerun failed closed during Ridge-Eikonal
profile correction:

```text
failed to bracket diffuse-mass profile correction without moving the sharp
interface.
```

Interpretation:

```text
P1 sharp area and nodal diffuse mass are different discrete measures,
their exact intersection can be empty under a fixed sharp interface,
this is not a pressure, capillary, or time-step instability,
do not hide it with damping, CFL reduction, curvature smoothing/capping,
profile-scale sampling, or a benchmark-specific branch.
```

AO-Fast implication: the q/phi AO state-space is the correct long-term route;
Ridge-Eikonal sharp-volume repair is not a fallback for AO compatibility.

## Required Follow-Up Before Branch Deletion

Before deleting the reference branch, confirm:

```text
1. dense oracle formulas/tests are imported or explicitly retired with reason,
2. GPU import checklist exists for every imported symbol,
3. active-vs-dense manufactured tests cover Q/S/J/dS,
4. runtime fail-close and checkpoint state-identity tests are replicated,
5. pressure_hodge/scalar-pressure plotting distinction is represented,
6. ch14 activation caveats are in the AO-Fast YAML gate,
7. negative sharp/diffuse two-measure knowledge is searchable from WIKI-T-169.
```

## SOLID-X

Design/specification/knowledge-salvage artifact only.  No solver source,
experiment result, tested implementation deletion, branch deletion,
FD/WENO/PPE fallback, damping/CFL workaround, smoothing, curvature cap,
benchmark branch, blanket projection, QP-as-physics path, implicit dense
fallback, implicit PCG fallback, CPU-first AO production path, or hidden
DCCD/UCCD damper introduced.
