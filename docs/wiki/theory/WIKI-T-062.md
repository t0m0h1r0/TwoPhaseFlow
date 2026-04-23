---
ref_id: WIKI-T-062
title: "UCCD6: Sixth-Order Upwind CCD with Order-Preserving Hyperviscosity"
domain: theory
status: PROPOSED  # Research memo only; no code; PoC pending
superseded_by: null
sources:
  - path: docs/memo/short_paper/SP-N_uccd6_hyperviscosity.md
    description: Full short paper — UCCD6 definition, Fourier analysis, energy identity, CN stability, boundary closures (formerly SP-H; renumbered 2026-04-23 to avoid collision with SP-H_fccd_face_jet_fvm_hfe)
depends_on:
  - "[[WIKI-T-001]]: CCD Method: Design Rationale and O(h^6) Compactness (baseline Chu & Fan operator)"
  - "[[WIKI-T-002]]: Dissipative CCD (DCCD) Spectral Filter (post-filter baseline)"
  - "[[WIKI-T-013]]: Upwind vs. Central Difference: Phase-Error and Amplification Trade-offs"
  - "[[WIKI-T-046]]: FCCD Face-Centered Upwind CCD (orthogonal face-locus remedy)"
  - "[[WIKI-T-061]]: Upwind⊕CCD Pedagogical Foundation (PDE-level derivation)"
consumers:
  - domain: theory
    description: Candidate node-centred dissipation channel for future NS pipelines
  - domain: cross-domain
    description: Comparison axis for DCCD / FCCD / UCCD6 trade-off matrix
tags: [ccd, compact_difference, upwind, hyperviscosity, crank_nicolson, energy_stability, research_proposal]
compiled_by: ResearchArchitect
compiled_at: "2026-04-21"
---

# UCCD6: Sixth-Order Upwind CCD with Order-Preserving Hyperviscosity

## Overview

UCCD6 is a **node-centred, sixth-order upwind combined compact difference scheme** for the linear advection equation $\partial_t u + a \partial_x u = 0$. It augments the Chu & Fan (1998) operator with an eighth-order hyperviscosity built from the CCD second-derivative operator:

$$
\partial_t U_j + a \, (D_1^{\text{CCD}} U)_j + \sigma |a| h^7 \, ((-D_2^{\text{CCD}})^4 U)_j = 0, \qquad \sigma > 0.
$$

The full derivation and stability analysis are in [SP-N](../../memo/short_paper/SP-N_uccd6_hyperviscosity.md) (formerly SP-H; renumbered 2026-04-23). This entry summarises the key results and positions UCCD6 within the project's dispersion/dissipation stack.

## Key equations

### Fourier symbols (exact, Chu & Fan)

$$
\omega_1(\theta) = \frac{9 \sin\theta \, (4 + \cos\theta)}{24 + 20 \cos\theta + \cos 2\theta}, \qquad
\omega_2(\theta)^2 = \frac{81 - 48 \cos\theta - 33 \cos 2\theta}{48 + 40 \cos\theta + 2 \cos 2\theta}.
$$

Taylor expansions at $\theta \to 0$:
$$
\omega_1(\theta) = \theta - \tfrac{1}{9450}\theta^7 + O(\theta^9), \qquad \omega_2(\theta)^2 = \theta^2 + \tfrac{19}{75600}\theta^8 + O(\theta^{10}).
$$

### UCCD6 Fourier symbol

$$
\lambda(\theta) = -i \frac{a \omega_1(\theta)}{h} - \sigma |a| \frac{\omega_2(\theta)^8}{h}, \qquad \Re \lambda(\theta) = -\sigma |a| \frac{\omega_2^8}{h} \le 0.
$$

### Discrete energy identity

$$
\tfrac{1}{2} \frac{\mathrm{d}}{\mathrm{d} t} \|U\|_h^2 = -\sigma |a| h^7 \|(-D_2^{\text{CCD}})^2 U\|_h^2 \le 0.
$$

## Stability summary

| Property | Result |
|---|---|
| Semi-discrete $L^2$ (periodic) | $\Re \lambda \le 0$ for all $\theta \in [-\pi, \pi]$ |
| Discrete energy | strict monotone decrease |
| Crank–Nicolson | unconditionally stable ($|G(\theta)| \le 1$ for all $\tau, h$) |
| Main truncation | $O(h^6)$ (from $D_1^{\text{CCD}}$) |
| Hyperviscosity truncation | $-\sigma \|a\| h^7 \partial_x^8 u$ (subdominant) |
| Boundary closure (Chu & Fan) | $O(h^4)$, GKS-compatible |

## Comparison with existing dissipation channels

| Scheme | Locus | Order | Dissipation mechanism |
|---|---|---|---|
| Chu & Fan CCD ([WIKI-T-001](WIKI-T-001.md)) | node | $O(h^6)$ | none (pure dispersion) |
| DCCD post-filter ([WIKI-T-002](WIKI-T-002.md)) | node | $O(h^6)$ | separate filter pass, coefficient $\varepsilon_d$ |
| FCCD ([WIKI-T-046](WIKI-T-046.md)) | face | $O(h^4)$ | structural upwind (strict causality) |
| **UCCD6 (this entry)** | node | $O(h^6)$ | embedded hyperviscosity $\sigma \|a\| h^7 (-D_2^{\text{CCD}})^4$ |

UCCD6 is complementary to FCCD: FCCD targets the balanced-force residual H-01 ([WIKI-E-030](../experiment/WIKI-E-030.md)) via face-locus alignment; UCCD6 is neutral to H-01 and targets Gibbs control in the node-centred operator.

## Design rationale for the eighth-order hyperviscosity

Let the hyperviscosity have the form $\sigma |a| h^{2p-1} (-D_2^{\text{CCD}})^p$. Its Fourier symbol is $\sigma |a| \omega_2^{2p} / h$, which expands as $\sigma |a| h^{2p-1} k^{2p} + O(h^{4p-1})$. For the hyperviscosity to be **subdominant to the $O(h^6)$ main truncation**, we need $2p - 1 \ge 7$, i.e. $p \ge 4$. The minimal choice $p = 4$ gives the $h^7 (-D_2^{\text{CCD}})^4$ design. Higher $p$ underdamps the $\pi$-mode (since $\omega_2^{2p} \to 0$ faster at low $\theta$ but saturates at fixed $\omega_2(\pi)^2 = \text{const}$ at the Nyquist).

## Relation to the pedagogical operator-level dual ([WIKI-T-061](WIKI-T-061.md))

[SP-G §4.2](../../memo/short_paper/SP-G_upwind_ccd_pedagogical.md) introduces the operator-level upwind-biased CCD $+\,\text{sign}(a) (\alpha/h) \delta^4$ as a pedagogical analogue of PDE-level upwind. UCCD6 is the **rigorous realisation** of that dual, with two refinements:

1. The bias operator is $\sigma |a| h^7 (-D_2^{\text{CCD}})^4$, not $\delta^4 / h$ — preserving the Chu & Fan sixth-order budget rather than degrading to $O(h)$.
2. The coupling with Crank–Nicolson gives unconditional stability, avoiding the explicit-scheme CFL constraint of the pedagogical variant.

## Open questions for PoC

1. **Choice of $\sigma$.** The theoretical stability holds for any $\sigma > 0$; empirical studies (Exp-H1–H3 in SP-N §8) are needed to identify the range that balances Gibbs control against accuracy loss on smooth regions.
2. **2D tensor-product extension.** Apply $D_1^{\text{CCD}}$ and $(-D_2^{\text{CCD}})^4$ dimension-by-dimension; verify anisotropy-free behaviour.
3. **Nonlinear advection.** UCCD6 as derived applies to linear $a \partial_x u$; for $u \partial_x u$ the hyperviscosity coefficient becomes state-dependent and the energy identity must be re-examined.
4. **GKS rigorous proof.** §6 of SP-N gives the GKS context; the full boundary matrix proof with Chu & Fan closures is deferred.

## References

- Chu, P. C., & Fan, C. (1998). A three-point combined compact difference scheme. *J. Comp. Phys.*, 140(2), 370–399.
- [SP-N full draft](../../memo/short_paper/SP-N_uccd6_hyperviscosity.md) (formerly SP-H)
- [SP-G pedagogical foundation](../../memo/short_paper/SP-G_upwind_ccd_pedagogical.md)
- [WIKI-T-001](WIKI-T-001.md), [WIKI-T-002](WIKI-T-002.md), [WIKI-T-013](WIKI-T-013.md), [WIKI-T-046](WIKI-T-046.md), [WIKI-T-061](WIKI-T-061.md)
