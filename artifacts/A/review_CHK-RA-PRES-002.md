# CHK-RA-PRES-002 Additional Presentation Review

Scope: `paper/presentations/ra-presentation-intro-20260506/`

Artifact reviewed: `output/twophaseflow-research-introduction.pptx`, generated slide modules, speaker notes, source map, and rendered contact sheet from artifact-tool.

Additional user comments considered:

- Audience-facing labels such as V7/V10 are inappropriate because they require manuscript-specific context.
- The deck does not make it clear enough that CCD/FCCD/UCCD are the computational core.

Stop condition: repeat review/fix until no MAJOR+ findings remain or round > 10.

## Round 3

Verdict: MAJOR findings found. Fix required before acceptance.

| ID | Severity | Slide/Artifact | Finding | Response |
|---|---|---|---|---|
| R3-1 | MAJOR | 10--15 | Verification labels and chart language still relied on paper-internal U/V-test semantics, so a fluid-mechanics audience could not understand the claims without reading the manuscript first. | Replaced U/V identifiers with descriptive validation categories, physical error sources, and audience-readable verdict labels across slides 10--15, speaker notes, and manifest. |
| R3-2 | MAJOR | 1, 3, 5, 10, 15 | CCD/FCCD/UCCD6 appeared as one item among many rather than as the numerical method's operator core. | Reframed the title, architecture slide, operator-stack slide, component-verification slide, and conclusion around CCD node derivatives, FCCD face flux, and UCCD6 momentum convection. |
| R3-3 | MAJOR | Footers / slide modules | Source footers exposed manuscript filenames such as `12u6_split_ppe_dc_hfe.tex`, which reintroduced paper-internal codes in a conference-facing deck. | Changed slide footers and speaker notes to human-readable source labels; retained exact manuscript trace only in `source_map.md` for auditability. |

## Round 4

Verdict: no MAJOR+ findings.

Checks performed after Round 3 fixes:

- Artifact-tool PPTX export PASS: 15 slides, 281003 bytes.
- Rendered contact sheet manually inspected: CCD/FCCD/UCCD6 are first-viewport and repeated core signals; no audience-facing V/U labels found.
- Layout checker PASS with 0 errors / 20 warning-only conservative padding/tight-text notes.
- Audience-facing internal-ID scan PASS for generated slides and speaker notes: no `V7`, `V10`, `U1`, `U9`, `12u*`, or `13v*` matches.
- `unzip -t` PPTX integrity PASS.

Remaining notes:

- `source_map.md` intentionally retains exact manuscript paths for traceability; those paths are not sent into the rendered slide payload.
- Layout warnings are unchanged conservative heuristics. Manual contact-sheet inspection found no visible overlap or broken wrap after the revision.

Stop reason: no MAJOR+ findings before round 10.
