# CHK-RA-CH14-COMMON-FLUX-XBENCH-001: cross-benchmark theory check

## Question

Does the conservative common-flux momentum route studied for the rising-bubble
failure remain valid for static droplets, oscillating droplets, capillary
waves, and related Chapter 14 interface benchmarks?

The answer must not depend on recognizing a circle, an ellipse, or a sine wave.
The only admissible discriminator is the discrete constrained variational
structure:

```text
is the interface state a constrained critical point of the discrete energy,
or does it contain an admissible noncritical mode?
```

## General theorem to be preserved

Let

```text
M_i(q) = V_i (rho_g + (rho_l - rho_g) q_i),
P_i    = M_i u_i,
K(M,P) = sum_i 1/2 |P_i|^2 / M_i,
E_h(q,M,P) = K(M,P) + sigma S_h(q) + Phi_g(q).
```

The proposed route is valid for any benchmark only if every step can be
written as this chain:

```text
1. common-flux transport of (q,M,P)
2. certified reinitialization/remap of (q,M,P), or fail-close
3. capillary/body/viscous impulse in the current mass metric
4. pressure projection as an M_f-orthogonal constrained minimization
```

The theorem-bearing objects are:

```text
F_M = rho_g F_V + (rho_l - rho_g) F_q
P-transport uses the same F_M stage by stage
c_sigma = M_f^{-1} T_q^T d(sigma S_h)
pressure projection = argmin_{D u = 0, BC} 1/2 ||u-u*||^2_Mf
```

For pure transport,

```text
K(M^T,P^T) <= K(M^n,P^n) + eps_T.
```

For the pressure step,

```text
K(M,u^{n+1}) <= K(M,u*) + eps_P.
```

For capillary work,

```text
K_after - K_before + sigma (S_after - S_before) <= eps_sigma
```

after removing pressure and constraint reactions in the same face metric.

This theorem does not mention droplets, waves, bubbles, circles, ellipses, or
graphs.  Those are only test families for the same finite-dimensional
energy/constraint system.

## Static droplet

### Continuous target

For a static droplet with no gravity and zero velocity, equilibrium means that
surface energy is stationary under volume constraints:

```text
dS(q)[delta q] + lambda dV(q)[delta q] = 0
```

for all admissible variations.  Equivalently, the Young-Laplace pressure jump
is representable as a pressure/constraint reaction:

```text
G_A p_YL - c_sigma + B lambda = 0.
```

The accepted residual is therefore not "the shape is visually circular"; it is

```text
h_sigma = P_adm (c_sigma - B lambda) = 0,
```

where `P_adm` is the projection onto divergence-free, boundary-admissible face
velocities after pressure and component-volume reactions are removed.

### Interaction with common-flux transport

If `u=0`, the transport ledger is zero:

```text
F_V = 0, F_q = 0, F_M = 0.
```

Then `(q,M,P)` is unchanged by the common-flux transport.  Since `P=0`, the
transport energy inequality is an equality.  The common-flux route cannot
create a static-droplet velocity ring by itself.

The static-droplet risk remains exactly the old one: the capillary cochain must
be the discrete surface-energy Riesz representative in the pressure face
metric.  If the residual ring exists, the scheme must either reduce it by
improving the variational cochain/criticality construction or fail-close.  It
must not hide it with damping, smoothing, curvature caps, or a static-droplet
branch.

### Verdict

The common-flux route is theoretically safe for the static droplet.  In fact it
is neutral for zero velocity.  The required acceptance gate is:

```text
||P_adm(c_sigma - B lambda)||_Mf <= eps_static
max |F_M| = 0
reinitialization not applied, or certified as zero-work remap
```

The current static YAML is consistent with this direction because
`ch14_static_droplet.yaml` disables reinitialization.  The route still must
fail-close if a nonzero Hodge/ring residual is detected.

## Oscillating droplet

### Continuous target

An oscillating droplet is not identified by being an ellipse.  It is an
interface state with a nonzero admissible component of the surface-energy
gradient:

```text
h_sigma = P_adm(c_sigma - B lambda) != 0.
```

At zero initial velocity, the first physical response is acceleration:

```text
P_t = -h_sigma,
K(t) = 1/2 t^2 ||h_sigma||^2_Mf + O(t^3).
```

For the Rayleigh-Lamb `n=2` small-amplitude case this linearizes to the usual
oscillator, but the discrete gate is not "looks elliptical."  Any noncritical
closed-interface mode should produce the corresponding constrained capillary
drive.

### Interaction with common-flux transport

At the first step with zero velocity, transport is again initially zero, so the
common-flux route does not suppress the capillary impulse.  The pressure stage
removes only pressure/constraint reactions; it must not replace `c_sigma` by a
full range projection in the production corrector.  Therefore the old
zero-drive failure remains forbidden:

```text
c_sigma -> Pi_R c_sigma
```

as a production-force substitution is invalid because it can algebraically set
the admissible drive to zero.

After motion begins, the common-flux route is beneficial: density and momentum
are transported by the same map, so the kinetic energy measured in the changing
mass metric has a sign theorem.  This prevents a density-metric mismatch from
contaminating the physical capillary oscillation.

### Reinitialization caveat

The canonical oscillating-droplet YAML reinitializes every step.  That is
admissible only after reinitialization becomes a conservative remap of
`(q,M,P)` or returns a fail-close certificate.  A `q`-only reinitialization can
change density without moving momentum and would reintroduce the same
mass-momentum mismatch that the common-flux route is designed to remove.

### Verdict

The common-flux route is theoretically compatible with oscillating droplets and
should not remove the physical mode, provided that:

```text
||h_sigma||_Mf > eps_dynamic
initial energy production follows the capillary work identity
range projection is diagnostic/static-gate only
reinitialization has a conservative remap certificate
```

Without the reinitialization remap certificate, the oscillating-droplet run
should fail-close rather than be accepted as theorem-grade.

## Capillary wave

### Continuous target

A capillary wave is the open/graph analogue of the same noncritical-interface
test.  For a small graph perturbation `eta(x)`,

```text
kappa(x) ~= -eta_xx(x),
j(x) = sigma kappa(x).
```

The constant part of `j` is a pressure reaction.  The nonconstant part is not
representable by a piecewise constant pressure and produces an admissible
velocity:

```text
h_sigma = P_adm(c_sigma - B lambda) != 0.
eta_tt + omega^2 eta = lower-order viscous/boundary terms.
```

In an infinite-depth inviscid reference,

```text
omega^2 = sigma k^3 / (rho_l + rho_g).
```

In the actual channel benchmark, walls, viscosity, finite depth, and no-slip or
free-slip choices modify the reference response, but they do not change the
operator theorem.  They enter through the boundary constraints and the energy
budget.

### Boundary interaction

The canonical capillary-wave YAML uses periodic `x` and wall `y` boundaries.
The common-flux ledger must therefore satisfy:

```text
periodic x faces cancel pairwise
wall-normal F_V = 0
wall-normal F_q = 0
wall-normal F_M = 0
```

The finite-volume mass and momentum balances must be written in the actual
nonuniform cell volumes.  If a wall/contact-line remap is present, it must be
part of the same remap certificate.  A wall-specific correction that changes
`q` without updating `M` and `P` is not admissible.

### Current capillary-wave YAML risk

`ch14_capillary.yaml` currently uses the same pressure-jump/FCCD projection
family, but its capillary settings differ from the oscillating-droplet closed
interface route: it relies on `capillary_range_projection:
component_hodge_augmented` rather than the closed-interface Riesz source block.

That is not automatically wrong.  For graph waves, the correct projection
should remove only pressure and constraint reactions, including constant or
zero-mode components, while preserving the nonconstant capillary mode.  But it
must be verified by the same work identity, not by visual oscillation alone.

The required one-step gate is:

```text
A_tt / (-omega_eff^2 A_0) = 1 + O(h^p, dt^p, viscous/boundary corrections)
```

or, in fully discrete energy form,

```text
K_after - K_before + sigma (S_after - S_before)
  = physical viscous/boundary work + certified truncation error.
```

If `component_hodge_augmented` removes the nonconstant mode, the wave freezes.
If it leaves a pressure-reaction component, the wave receives nonphysical
impulse.  Either failure should be caught by the gate.

### Verdict

The common-flux route is theoretically compatible with capillary waves, but it
has two extra obligations relative to the closed droplet:

```text
wall/periodic boundary flux ledger must be exact in the nonuniform metric
the graph-interface capillary projection must preserve nonconstant modes while
removing only pressure/constraint reactions
```

Until those are proved for the capillary YAML's exact capillary source
contract, the wave should be considered "compatible by theorem, not yet
automatically validated by current settings."

## Cross-benchmark comparison

| Benchmark | Criticality status | What must vanish | What must remain | Main risk |
|---|---|---|---|---|
| Static droplet | constrained critical point | admissible capillary residual | none | nonzero Hodge/ring residual |
| Oscillating droplet | noncritical closed-interface mode | pressure/volume reactions | closed-interface capillary drive | q-only reinit and over-projection |
| Capillary wave | noncritical graph-interface mode | constant pressure/constraint reactions | nonconstant wave drive | wall ledger and projection over/under-removal |
| Rising bubble | noncritical body-force/interface state | pressure reactions | buoyancy plus capillary residual | density-metric mismatch and pressure-face history |

The same state equation handles all four:

```text
h = P_adm(dE_h) .
```

Equilibrium tests require `h ~= 0`; moving-interface tests require the
physically predicted nonzero `h` and the corresponding energy exchange.

## Implementation consequences

1. Do not make a static-droplet branch.  Implement a general constrained
   criticality gate.

2. Do not make an oscillating-droplet or capillary-wave branch.  Implement a
   general admissible-mode drive gate:

   ```text
   ||h||_Mf > eps_dynamic
   sign and work match dE_h
   ```

3. The transport ledger must support all boundary topologies used here:
   periodic/periodic closed droplets, periodic/wall capillary waves, and
   wall/wall or mixed rising-bubble tanks.

4. Reinitialization must be a certified remap for every moving-interface
   benchmark that uses it.  Otherwise those runs must fail-close in
   `conservative_common_flux` mode.

5. Pressure face acceleration history must remain disabled or work-certified
   in the conservative route for all benchmarks, not only rising bubbles.

6. The capillary source UX should converge to one contract:

   ```text
   capillary source = surface-energy Riesz cochain in the pressure face metric
   reactions removed = pressure and declared constraints only
   production corrector consumes full accepted cochain, not Pi_R c_sigma
   ```

   Closed-interface and graph-interface implementations may use different
   trace constructors, but they must return the same kind of work-certified
   face cochain.

## Final judgement

The conservative common-flux momentum route is not a rising-bubble-specific
fix.  It is a general mass-metric correction and is theoretically compatible
with static droplets, oscillating droplets, capillary waves, and other
interface benchmarks.

The compatibility is conditional, not automatic:

```text
static droplet: pass constrained criticality, no q-only reinit
oscillating droplet: preserve noncritical capillary drive, remap reinit
capillary wave: exact wall/periodic ledger, preserve nonconstant graph mode
all cases: pressure projection and capillary work use the same face metric
```

Under those conditions the scheme is more consistent than the current
velocity-history route.  If any condition is missing, the correct behavior is
fail-close, not fallback, damping, smoothing, CFL-only adjustment, or
benchmark-name branching.
