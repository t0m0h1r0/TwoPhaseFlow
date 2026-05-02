# CHK-RA-CH7-NARRATIVE-011 — Chapter 7 strict review

Verdict: PASS after fixes. Open findings: 0 FATAL / 0 MAJOR / 0 MINOR.

Scope: `paper/sections/07_time_integration.tex`.

## Findings fixed

- MAJOR: Local stability paragraphs still concluded with a two-term minimum over advection and capillary constraints, contradicting the chapter-level synthesis that also includes buoyancy and discrete-spectrum restrictions. The local paragraphs now state only the constraint they actually establish and defer the final timestep to `\Delta t_{\mathrm{syn}}`.
- MAJOR: The stability taxonomy ended with “three axes complete the scheme choice,” which made pressure projection, capillary closure, and buoyancy look secondary despite being central to the narrative. It now separates stability classification from simultaneous closure and physical-resolution conditions.
- MINOR: The introduction still called the advective CFL “dominant,” which over-claimed before the global synthesis. It now identifies it as the advection-origin explicit restriction.
- MINOR: Wording around hydrostatic buoyancy used vague `圧力側` phrasing and the section title used `タイムステップ`; both were normalized to `PPE の楕円型作用素` and `時間刻み制御`.

## Reviewer checks

- Narrative: local derivations now feed into the global minimum instead of competing with it.
- Notation: timestep terminology is unified around `時間刻み` / `\Delta t_{\mathrm{syn}}`.
- Scope: no old-version framing and no implementation/runtime discussion was introduced.
- [SOLID-X] paper/review documentation only; no production code boundary changed.
