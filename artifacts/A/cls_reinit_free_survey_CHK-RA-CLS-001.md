# CHK-RA-CLS-001 - Survey: Reinitialization-Free or Reinitialization-Minimized LS/CLS for Two-Phase Flow

Date: 2026-05-07
Branch: `codex/ra-cls-reinit-free-survey-20260507`
Route: ResearchArchitect / RESEARCH_BREADTH

## Question

二相流体の Level Set / Conservative Level Set (CLS) で、移流後の
再初期化が計算不安定化を起こす。CLS で体積保存は改善できるが、界面
profile と曲率が崩れるので再初期化は必要になる。この再初期化を不要に
する研究・設計候補をサーベイする。

## Executive Verdict

「再初期化を完全に消す」研究は存在するが、古典 LS/CLS のまま単に
`reinit_every=0` にする話ではない。成功している系統は、再初期化の役割を
次のどこかへ吸収している。

| 系統 | 何を置き換えるか | 二相流 CLS への適合 |
|---|---|---|
| Monolithic conservative anti-diffusion CLS | pseudo-time reinit を、物理時間更新の中の entropy/artificial anti-diffusion flux に吸収 | 最も近い。`psi` 保存場を保ったまま profile-control を輸送 flux に内蔵できる可能性がある。 |
| Modified / variational LS | signed-distance gauge を保つ source/penalty term を LS advection PDE に内蔵 | `phi` 幾何場の候補。体積保存は別に `psi`/mass carrier が要る。 |
| Conservative phase-field / Allen-Cahn-like sharp tracking | tanh profile 維持を連続的な保存 phase-field 方程式に吸収 | reinit は不要になるが、mobility/regularization と capillary work の扱いが変わる。 |
| THINC / THINC-LS | volume fraction の algebraic tanh reconstruction で profile と mass carrier を更新 | 質量保存・鋭さは強い。LS は幾何補助へ下げる設計になる。 |
| Gradient/jet augmented LS | 高次 local derivative transport で距離性劣化を遅らせる | 再初期化頻度低減には有効だが、二相流では完全削除までは届いていない。 |

本プロジェクトの直近の問題設定では、第一候補は
**monolithic conservative anti-diffusion CLS**、第二候補は
**THINC/CSLS 型の volume carrier + LS geometry 分離**である。どちらも
`WIKI-T-159/160` の reinit-aware capillary Hodge gate を通さない限り
採用してはいけない。profile repair が界面 trace や surface energy を変えるなら、
それは再初期化を消したのではなく、名前を変えた projection defect である。

## Problem Restatement for This Codebase

Current CLS has three useful properties:

1. `psi` の保存形移流は体積を守りやすい。
2. `phi = H_epsilon^{-1}(psi)` は normal/curvature/capillary data の幾何場になる。
3. Ridge-Eikonal/profile repair は profile collapse を防ぐ。

しかし再初期化が次を変えると、毛管仕事の入力が物理移流と混ざる。

```text
q^n -- T_h(u_f) --> q_T      physical transport
q_T -- Pi_h    --> q^{n+1}  representation/profile repair
```

Fixed-topology capillary validation では `Pi_h` が
`Gamma(q_T)` と `S_h(Gamma(q_T))` を保存しない限り、`Pi_h` は無害な
再初期化ではない。したがって「再初期化不要化」の候補も、次の二条件を
満たす必要がある。

- profile-control が物理時間の保存 flux と同じ conservation ledger に入る。
- capillary cochain は `T_h` endpoint に対して構成され、profile-control の
  defect は別診断として測る。

## Literature Map

### 1. Baseline CLS: mass is solved, profile is not

Olsson, Kreiss, and Zahedi の CLS は、regularized characteristic function
`Phi` を保存形に移流し、別段の reinitialization step で transition layer の
profile/thickness を維持する。この設計は体積保存に強いが、ユーザの問題そのもの、
つまり reinit step が二相流 coupling に入る問題を残す。

Sources:

- Olsson, Kreiss, Zahedi (2005), *A conservative level set method for two phase flow*, JCP. DOI: https://doi.org/10.1016/j.jcp.2005.04.007
- Olsson, Kreiss, Zahedi (2007), *A conservative level set method for two phase flow II*, JCP. DOI: https://doi.org/10.1016/j.jcp.2006.12.027

Use in this project:

- 現行 `psi` 保存場の根拠として維持。
- ただし pseudo-time reinit は capillary Hodge contract の外に置けない。

### 2. Conservative anti-diffusion CLS: reinit subproblemを物理更新に吸収

Guermond, Quezada de Luna, Thompson (2017) は、conservative level set に
entropy production に基づく artificial diffusion / anti-diffusion を入れ、
長時間計算で level set reinitialization も interface reconstruction も不要とする。
有限要素・有限体積、1D/2D/3Dで提示され、maximum-principle-preserving,
self-tuning, unstructured mesh 対応を主張する。

Source:

- Guermond, Quezada de Luna, Thompson (2017), *An conservative anti-diffusion technique for the level set method*, J. Comput. Appl. Math. DOI: https://doi.org/10.1016/j.cam.2017.02.016

Mechanism:

```text
psi_t + div(psi u) = div(D_entropy grad psi) - div(A_entropy anti-diffusive flux)
```

where compression is no longer a pseudo-time event; it is part of the same
transport step.

Why it matters:

- これは「CLS のまま reinit を不要にする」文献として最も近い。
- `psi` が主変数なので、体積保存・boundedness・profile control を同一
  update に押し込める。
- pseudo-time step count や reinit stop criterion の不安定化経路を消せる。

Risks for this project:

- Existing FCCD face-flux transport is a strict conservation contract
  (`WIKI-T-156`). Anti-diffusion flux を足すなら、face-space conservation,
  monotonicity, GPU/CPU bit behavior, density jump mapping を再検証する必要がある。
- Curvature を diffuse `psi` から直接読むと capillary Hodge gate を壊しやすい。
  `phi`/geometry path は別に theorem-grade に閉じるべき。

Research action:

- Implement as an experimental `profile_control_flux` layer, not as a
  reinitialization module.
- Measure `mass`, `interface thickness`, `Delta S_profile`, `capillary_hodge_residual`.

### 3. Modified level-set equations: eikonal preservationをsource termに入れる

Sabelnikov, Ovsyannikov, Gorokhovski (2014) は、level-set advection equation に
source term を入れ、zero level set では term が消える一方で、eikonal property を
自動的に保つ定式化を提示した。厳密 source では reinitialization は理論上不要。
局所近似では reinit frequency を大きく減らす方向になる。

Source:

- Sabelnikov, Ovsyannikov, Gorokhovski (2014), *Modified level set equation and its numerical assessment*, JCP. DOI: https://doi.org/10.1016/j.jcp.2014.08.018

Bothe, Fricke, Soga (2024) は、この modified level-set equation の数学解析を与え、
zero level set が元の transport と同一に保たれること、局所的に gradient norm を
制御できることを Hamilton-Jacobi framework で正当化している。

Source:

- Bothe, Fricke, Soga (2024), *Mathematical analysis of modified level-set equations*, Mathematische Annalen. DOI: https://doi.org/10.1007/s00208-024-02868-y

Related variational / stabilized LS:

- Li, Xu, Gui, Fox (2005) は image segmentation 由来の variational LS で、SDF からの逸脱を罰する internal energy により reinitialization を不要化した。DOI: https://doi.org/10.1109/CVPR.2005.213
- Li, Xu, Gui, Fox (2010) の DRLSE は distance regularization を整理した。DOI: https://doi.org/10.1109/TIP.2010.2069690
- Touré and Soulaïmani (2016) は SUPG variational LS に eikonal residual perturbation を加えて、moving interface flow を reinit なしで解く stabilized FEM を提案した。DOI: https://doi.org/10.1016/j.camwa.2016.02.028
- Shao, Yuan, Chai, Jin, Luo (2023) は gas-liquid flows 向け generalized variational LS を提示し、penalty term により every-step reinit を不要にする。DOI: https://doi.org/10.1016/j.jcp.2023.112558

Fit to this project:

- `phi` を geometry gauge として持つなら有力。
- ただし `phi` non-conservative transport だけでは CLS の体積保存契約を失う。
- Best use is not `psi` replacement but a two-field design:

```text
psi: conservative mass carrier
phi: modified-LS gauge / geometry carrier
constraint: Gamma(phi) == {psi=0.5}, with defect ledger
```

Main risk:

- Source/penalty term is zero on the interface in continuum theory, but discrete
  face/cochain coupling may still inject surface-energy defect.
- Penalty tuning can become another hidden reinit knob.

### 4. Conservative phase-field: reinitを連続的regularizationに置換

Sun and Beckermann (2007) は hyperbolic tangent phase-field profile を使い、
zero phase-field contour を sharp interface として追跡する。Separate
reinitialization scheme や Lagrangian marker なしで mass conservation を達成する、
という位置づけである。

Source:

- Sun and Beckermann (2007), *Sharp interface tracking using the phase-field equation*, JCP. DOI: https://doi.org/10.1016/j.jcp.2006.05.025

Chiu and Lin (2011) はこの流れを二相非圧縮 Navier-Stokes へ拡張し、Cahn-Hilliard
のような質量保存性をより簡単な conservative phase-field equation で実現する。

Source:

- Chiu and Lin (2011), *A conservative phase field method for solving incompressible two-phase flows*, JCP. DOI: https://doi.org/10.1016/j.jcp.2010.09.021

Recent representative:

- Jain (2022), *Accurate conservative phase-field method for simulation of two-phase flows*, JCP. DOI: https://doi.org/10.1016/j.jcp.2022.111529

Interpretation:

- Reinitialization is not removed for free; it is replaced by an always-on
  phase-field regularization / sharpening dynamics.
- This is attractive when interface thickness, boundedness, and conservation
  are more important than SDF purity.

Project risk:

- Current paper contracts are CLS + pressure-jump/Hodge, not Cahn-Hilliard or
  conservative phase-field free energy. Adopting this path changes the model
  class and must be presented as a representation pivot.
- Mobility/regularization must not double-count capillary surface energy.

### 5. THINC and THINC-LS: tanh reconstructionをvolume carrierにする

THINC represents the interface by a hyperbolic tangent reconstruction of a
volume-fraction field. It is conservative and algebraic, closer to VOF than LS.
It avoids the classic LS reinitialization problem by not transporting an SDF as
the primary mass carrier.

Sources:

- Xiao, Honma, Kono (2005), *A simple algebraic interface capturing scheme using hyperbolic tangent function*. DOI: https://doi.org/10.1002/fld.975
- Yokoi (2007), *Efficient implementation of THINC scheme: A simple and practical smoothed VOF algorithm*, JCP. DOI: https://doi.org/10.1016/j.jcp.2007.06.020
- Ii, Sugiyama, Takeuchi, Takagi, Matsumoto (2012), *An interface capturing method with a continuous function: The THINC method with multi-dimensional reconstruction*, JCP. DOI: https://doi.org/10.1016/j.jcp.2011.11.038

Hybrid with LS:

- Coupled THINC and LS (2018) combines THINC conservation with high-order LS
  surface representation. DOI: https://doi.org/10.1016/j.jcp.2018.06.074
- Xiong, Xie, Xiao (2023) propose THINC/CSLS with consistent single-step time integration for incompressible flow with surface tension. DOI: https://doi.org/10.1063/5.0173004

Project fit:

- Strong candidate if the design goal becomes "mass carrier is not CLS pseudo-time
  reinit, LS is geometry support".
- Best for aggressive deformation where `psi` profile collapse is the immediate
  failure mode.

Project risks:

- THINC/VOF-like carrier must be coupled to curvature/HFE and pressure-jump
  cochains without replacing the current projection-native PPE contract.
- Need to prove that the reconstructed geometry supplies `T_h^* dS_h` in the
  same face-space metric used by capillary Hodge diagnostics.

### 6. Gradient / jet augmented LS: frequency reduction, not a clean deletion

Nave, Rosales, Seibold (2010) advect both LS values and gradients coherently.
This improves local curvature and subgrid interface localization.

Source:

- Nave, Rosales, Seibold (2010), *A gradient-augmented level set method with an optimally local, coherent advection scheme*, JCP. DOI: https://doi.org/10.1016/j.jcp.2010.01.029

But in multiphase incompressible flow, later narrow-band GALS work still
introduces a simple reinitialization procedure.

Source:

- Owkes and Desjardins (2014), *A narrow-band gradient-augmented level set method for multiphase incompressible flow*, JCP. DOI: https://doi.org/10.1016/j.jcp.2014.04.055

Interpretation:

- Useful if the current problem is "reinit too frequent".
- Not enough if the target is "no profile projection step can alter capillary work".

### 7. Reinitialization literature itself says: deletion is still not the mainstream

Shakoor (2025) reviews 2014-2024 LS reinitialization methods and classifies them
into direct geometric distance, local Eikonal, and global Eikonal families. A key
lesson for this question is negative: most modern work still improves
reinitialization rather than deleting it; combined transport/reinit methods introduce
a control parameter whose tuning must be application-specific.

Source:

- Shakoor (2025), *Review of level-set reinitialization methods in computational mechanics and materials science*, Modelling and Simulation in Materials Science and Engineering. DOI: https://doi.org/10.1088/1361-651X/ade17b

Implication:

- If we keep current CLS/Ridge-Eikonal architecture, the safer near-term path is
  reinit-aware Hodge accounting and interface-preserving reinit.
- If the user goal is strictly "no reinit event", we need a representation change,
  not a smaller pseudo-time loop.

## Project Decision Matrix

| Candidate | Expected benefit | Main blocker | RA recommendation |
|---|---|---|---|
| Entropy anti-diffusion CLS | Removes pseudo-time reinit while keeping conservative `psi` carrier | Must rederive FCCD-compatible face flux and Hodge energy accounting | First PoC candidate |
| Modified `phi` source term | Keeps geometry/SDF gauge during advection | Does not conserve mass alone; discrete source may move capillary work | Theory probe, not standalone |
| Conservative phase-field | No reinit event; bounded mass carrier | Changes model class and capillary energy interpretation | Only if representation pivot is acceptable |
| THINC/CSLS | Strong mass/shape robustness under deformation | Need curvature/HFE/pressure-jump cochain from THINC geometry | Second PoC candidate |
| GALS/jet LS | Better curvature and less reinit pressure | Multiphase versions still reinit | Auxiliary improvement only |
| Turn off reinit | Simplicity | Profile collapse and curvature blow-up | Reject |

## Acceptance Gates for Any PoC

The following gates are required before any candidate can replace current
Ridge-Eikonal/profile repair.

1. Conservative carrier:
   - `sum(psi * cell_volume)` drift bounded to existing CLS tolerance.
   - no hidden global mass redistribution that masks local interface collapse.

2. Interface trace:
   - `Gamma_after_update` compared to a high-resolution reference on Zalesak,
     single-vortex reversal, and static droplet.
   - interface displacement separated from profile sharpening.

3. Profile quality:
   - `f_0.1-0.9`, local thickness, overshoot/undershoot, boundedness.
   - no static-profile broadening comparable to historical comp-diff defect.

4. Geometry:
   - normal/curvature errors on circle/ellipse.
   - curvature spectrum and HFE compatibility.

5. Capillary Hodge:
   - static droplet: weighted `P_h c_sigma` must converge to zero.
   - dynamic droplet: nonzero dynamic signal must survive.
   - no blanket `c_sigma -> Pi_R c_sigma` production shortcut.

6. Energy accounting:
   - measure `Delta S_transport`, `Delta S_profile_control`,
     `Delta KE`, and projection residual separately.
   - profile-control term must be labelled if it changes surface energy.

7. Implementation contract:
   - `backend.xp` GPU/CPU path.
   - no FD/WENO/PPE fallback.
   - no destructive replacement of tested Ridge-Eikonal code; keep legacy path
     registered as comparator.

## Recommended Research Plan

### PoC A: Monolithic conservative anti-diffusion CLS

Goal:

```text
psi^{n+1} = psi^n + dt * [FCCD conservative flux + profile-control face flux]
```

where the profile-control face flux is local, conservative, bounded, and recorded
as a separate diagnostic component.

Minimal experiments:

- static circle, `u=0`, sigma-positive and sigma-zero;
- Zalesak and single-vortex transport without NS coupling;
- static droplet Hodge gate;
- capillary wave / oscillating droplet with `Delta S_profile_control` reported.

Pass condition:

- No pseudo-time reinit call.
- Profile stays bounded and sharp.
- Static capillary Hodge residual improves or at least does not regress.
- Dynamic capillary signal is not projected away.

### PoC B: THINC/CSLS carrier with LS geometry

Goal:

```text
alpha/psi: THINC conservative carrier
phi: reconstructed geometry support for normal/curvature/HFE
capillary cochain: built from reconstructed trace in production face metric
```

Minimal experiments:

- same as PoC A, plus severe deformation where current CLS interface collapses.

Pass condition:

- THINC mass conservation and LS curvature both survive.
- Surface-energy change is attributable to physical transport, not reconstruction.

### Theory Probe C: Modified phi equation as gauge stabilizer

Goal:

Use modified LS source term only for `phi` geometry gauge while `psi` remains
the conservative physical carrier.

Pass condition:

- `Gamma(phi)` and `{psi=0.5}` stay locked.
- Source term has a discrete defect ledger and does not enter physical capillary
  work silently.

## Bottom Line

The best answer to the user's problem is not "find a better reinit loop". It is:

```text
move profile preservation from an after-the-fact projection into the physical
transport/update contract, or move mass transport to a THINC/phase-field carrier
and demote LS to geometry.
```

For this project, start with conservative anti-diffusion CLS as the least
disruptive PoC. If that fails the capillary Hodge/geometry gates, the next
serious route is THINC/CSLS. Variational/modified LS is valuable as a `phi`
gauge stabilizer, but not as a standalone replacement for CLS mass transport.
