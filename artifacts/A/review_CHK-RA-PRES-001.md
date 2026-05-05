# CHK-RA-PRES-001 Presentation Review

Scope: `paper/presentations/ra-presentation-intro-20260506/`

Artifact reviewed: `output/twophaseflow-research-introduction.pptx` and rendered contact sheet from artifact-tool.

Stop condition: repeat review/fix until no MAJOR+ findings remain or round > 10.

## Round 1

Verdict: MAJOR findings found. Fix required before acceptance.

| ID | Severity | Slide | Finding | Response |
|---|---|---:|---|---|
| R1-1 | MAJOR | 1 | Title slide right-side "face-space contract" panel wrapped awkwardly and overlapped the tag rail, weakening the first-view signal. | Fixed by narrowing title/lead text zones, moving tags to a 2x2 rail, and widening the right-side panel. |
| R1-2 | MAJOR | 8 | Face-contract slide used floating boxes around `FCCD face jet J_f(u)` without visual connectors, so the shared-footprint claim was not visually proven. | Fixed by adding connector strokes from the central face-jet block to the surrounding operation boxes. |
| R1-3 | MAJOR | 11 | Verdict bar chart mixed V-test count and expanded判定軸 count; audience could misread the bars as "10 tests". | Fixed by adding an explicit note: V10 is split into mass and shape axes. |
| R1-4 | MAJOR | 12 | The title wrapped with a stranded final character in the rendered deck, which looked unprofessional at conference scale. | Fixed by shortening the title. |

## Round 2

Verdict: no MAJOR+ findings.

Remaining notes:

- Layout checker reports warnings only, mostly conservative bottom-padding and tight arrow text heuristics. Manual contact-sheet inspection found no visible overlap, overflow, or source-fidelity problem after Round 1 fixes.
- Claims remain bounded to the manuscript sources listed in `source_map.md`.

Stop reason: no MAJOR+ findings before round 10.
