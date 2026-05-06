# SKILL-PRESENTATION-ILLUSTRATION

id: SKILL-PRESENTATION-ILLUSTRATION
purpose: Turn a supported slide claim into a conceptual illustration brief, then audit the image by reverse readback against the source claim.
trigger:
- PresentationWriter needs conceptual, painting-like, mechanism, or readback visual planning
- PaperReviewer audits a generated or proposed presentation visual
minimal_instruction: Separate abstraction, concretization, image language, and reverse readback; the visual must make the supported claim clearer without inventing mechanism, result, scale, or novelty.
full_ref: prompts/meta/kernel-ops.md §VISUAL-CONCEPT-01
input_contract:
- one slide claim with source refs and allowed scope
- intended audience, visual role, and forbidden implications
- output medium constraints and review artifact path
forbidden_context:
- decorative images without claim function
- unverified physical mechanism or quantitative result implied by the visual
- style prompt accepted without reverse-readback audit
success_metric:
- illustration brief names claim, abstraction, concrete scene, and forbidden implications
- reverse readback matches the source claim and flags unsupported implications
token_target: 180
