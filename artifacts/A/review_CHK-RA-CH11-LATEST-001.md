# CHK-RA-CH11-LATEST-001 — Chapter 11 Latest Narrative Review

Scope: `paper/sections/11_full_algorithm.tex`, `paper/sections/11c_dccd_bootstrap.tex`,
`paper/sections/11d_pure_fccd_dns.tex`, with adjacent consistency checks against §5, §9,
§12, and §13.

Policy: review/remediate until no MAJOR+ findings remain or round count exceeds 20.
This is paper/docs scope only. [SOLID-X]

## Round 1 Verdict: FAIL

MAJOR-1 — §11 made one-fluid / smoothed-Heaviside PPE look like a parallel standard path.

Evidence: §9 and §12 define the two-phase pressure standard as phase-separated PPE + HFE + DC
+ gauge/reprojection separation. Chapter 11 instead described low/mid density as a standard
monolithic branch and high density as a switch to split PPE. That weakens the narrative and
contradicts the latest pressure-closure story.

Remediation: §11 now states that the two-phase standard pressure closure is split PPE + HFE + DC
+ face-cochain correction. Monolithic PPE and CSF are retained only as single-phase / low-density
reduced or contrast paths, not as a two-phase pressure-jump closure.

MAJOR-2 — Stage 2 conflated interface-band quality with volume.

Evidence: `\int\psi(1-\psi)\,dV` was called a volume monitor. In §5 this quantity is
`Q_\Gamma`, an interface thickness / profile-quality diagnostic. The actual liquid volume
contract is `\sum_i \psi_i V_i` and is closed through Stage B/F, with Stage F in `\phi` space
after Ridge--Eikonal reconstruction.

Remediation: Stage 2 now separates declared reinitialization cadence, `Q_\Gamma` quality
monitoring, liquid-volume residual, and Stage F `\phi`-space closure.

MAJOR-3 — The predictor formula reintroduced CCD-centered momentum advection as if it were the
standard momentum operator.

Evidence: §6 assigns UCCD6 to bulk momentum and FCCD Option B/C to face-aligned BF reductions,
while raw CCD advection is only a smooth manufactured-solution / comparison notation. §11 used
`\mathcal{C}_{\text{CCD}}` directly inside the production predictor.

Remediation: §11 now defines `\mathcal{A}_{\bu}` as the momentum-advection operator, with UCCD6
as standard bulk and FCCD Option B/C for BF-aligned reduced stacks. CCD-centered nonconservative
notation is restricted to smooth single-phase comparisons.

MAJOR-4 — HFE pressure history was written as a nodal extended pressure gradient path.

Evidence: Latest §9 says affine-jump IPC carries prior pressure as a canonical face acceleration
cochain; raw nodal pressure and nodal extension are not the physical pressure representative.
The previous §11 wording first built `p^n_{\mathrm{ext}}` and then replaced the nodal gradient,
which invites exactly the old pressure-history bug.

Remediation: §11 now makes HFE a one-sided Hermite reconstruction layer for the saved affine
pressure-history face cochain. The standard saved quantity is the face acceleration, not a raw
nodal `p^n_{\mathrm{ext}}` field.

MAJOR-5 — The pure FCCD DNS section overclaimed an unverified future-facing architecture.

Evidence: The section described expected parasitic-current reduction and high-density robustness
in a way that read like a verified paper result. §13 only supports finite-time reduced stacks and
static / reduced BF tests.

Remediation: The section now frames pure FCCD DNS as an advanced closure boundary: verified
primitive contracts are listed separately from unverified simultaneous layer usage.

MINOR-1 — §11c opened with DCCD post-filter design rather than the actual bootstrap/timestep role.

Remediation: §11c now begins with initial geometry / pressure / metric consistency and states the
non-role of DCCD in CLS transport or pressure face closure.

## Round 2 Verdict: PASS

MAJOR+ findings: 0.

Validation:

- Targeted stale-standard scans PASS: no remaining hits for `低・中密度比`, `標準経路は一括`,
  `体積モニタ`, `M/M_`, `固定頻度`, `期待される利点`, `高密度比でのロバスト性`,
  `寄生流れ抑制を検証`, or `DCCD ブートストラップ` in Chapter 11 files.
- Role scans PASS: remaining `一括 smoothed-Heaviside PPE` / `CSF 体積力` mentions are explicitly
  reduced or contrast paths; remaining `p^n_{\mathrm{ext}}` mention states it is not the saved
  standard quantity.
- `git diff --check` PASS.
- `make -C paper` PASS; generated `paper/main.pdf` with 243 pages.
- `paper/main.log` fatal/error/undefined-reference/undefined-citation/overfull scans PASS.

Stop condition reached at Round 2: no MAJOR+ findings remain.
