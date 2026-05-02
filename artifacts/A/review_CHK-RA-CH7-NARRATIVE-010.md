# CHK-RA-CH7-NARRATIVE-010 — Chapter 7 strict review

Verdict: PASS after fixes. Open findings: 0 FATAL / 0 MAJOR / 0 MINOR.

Scope: `paper/sections/07_time_integration.tex`.

## Findings fixed

- MAJOR: The advection subsection stated that only the advective CFL remains, which contradicted the later synthesized timestep minimum over advection, capillarity, buoyancy, and discrete-spectrum constraints. It now limits that claim to the two advection updates and points the reader back to the global synthesis.
- MAJOR: The stiffness map used `界面 CFL` for CLS advection while `界面張力 CFL` appears elsewhere, making the narrative ambiguous. The CLS row now says `界面移流 CFL |\bu|\Delta t/h`.
- MINOR: The stability taxonomy called L-stability useful for `高 Re 拡散`, which is physically misleading. The wording now refers to damping high-frequency components of stiff diffusion.
- MINOR: Prose and notation mixed `PPE 側`, `NS 側`, English `proof sketch`, plain `O(...)`, and `fractional step`. These were normalized to mathematical Japanese phrasing, `\Ord{...}`, and `fractional-step`.

## Reviewer checks

- Narrative: causal order remains `CLS -> predictor -> IPC PPE`, while chapter order is explained as closure-dependency order.
- Notation: CFL names now distinguish advection, viscous, capillary, buoyancy, and discrete-spectrum restrictions.
- Scope: no old-version framing and no implementation/runtime discussion was introduced.
- [SOLID-X] paper/review documentation only; no production code boundary changed.
