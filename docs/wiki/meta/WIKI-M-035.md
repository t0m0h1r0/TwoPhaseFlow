---
ref_id: WIKI-M-035
title: "Meta-Prompt Deployment Needs Project Boundaries, Native Adapters, and Token ROI Gates"
domain: meta
status: ACTIVE
superseded_by: null
tags:
  - metaprompt
  - deployment
  - kernel_project
  - skill_capsules
  - token_roi
  - artifact_convergence
  - presentation_workflow
  - role_scope
sources:
  - path: artifacts/M/presentation_agent_evolution_CHK-RA-PRES-AGT-001.md
    description: "Deck-generation project pattern: source-grounded PPTX/PDF/preview pipeline rather than one-shot slide text"
  - path: artifacts/M/presentation_story_pipeline_CHK-RA-PRES-AGT-002.md
    description: "Story-map-before-slide-spec workflow and staged review gates"
  - path: artifacts/M/presentation_audience_review_loop_CHK-RA-PRES-AGT-003.md
    description: "Audience-role, skeptic, Q&A, diff, and delivery review loops"
  - path: artifacts/M/presentation_convergence_loop_CHK-RA-PRES-AGT-004.md
    description: "Issue register, remaining delta, freeze gates, focused repair, and stop criteria"
  - path: artifacts/M/skill_deploy_compliance_CHK-RA-PRES-AGT-005.md
    description: "Requirement that skills and support artifacts deploy from the metaprompt source"
  - path: artifacts/M/kernel_project_sync_safety_CHK-RA-PRES-AGT-006.md
    description: "kernel-project.md as a user-owned project overlay preserved during submodule sync"
  - path: artifacts/M/cross_domain_meta_convergence_research_CHK-RA-META-COMMON-001.md
    description: "Research note extracting a domain-neutral artifact-convergence primitive"
  - path: artifacts/M/cross_domain_meta_convergence_design_policy_CHK-RA-META-COMMON-002.md
    description: "Design policy for native domain adapters instead of presentation vocabulary everywhere"
  - path: artifacts/M/artifact_convergence_implementation_issues_CHK-RA-META-COMMON-003.md
    description: "Implementation issue log for common convergence primitive and adapters"
  - path: artifacts/M/metaprompt_audit_repair_CHK-RA-META-AUDIT-001.md
    description: "Audit and repair of project leakage, role-scope drift, fixed PR semantics, and prompt bloat"
  - path: artifacts/M/generated_prompt_roi_audit_CHK-RA-META-AUDIT-002.md
    description: "Generated agent/skill token ROI audit and Q3-16 token ROI gate"
  - path: prompts/meta/kernel-deploy.md
    description: "Deployment source defining Skill Capsule specs, project overlay rules, Q3 audit, and token ROI gate"
  - path: scripts/deploy_codex_agents.py
    description: "Project-local deploy script that regenerates agents/skills and emits telemetry/ROI reports"
depends_on:
  - "[[WIKI-M-014]]"
  - "[[WIKI-M-016]]"
  - "[[WIKI-M-022]]"
  - "[[WIKI-M-030]]"
  - "[[WIKI-M-031]]"
  - "[[WIKI-M-032]]"
  - "[[WIKI-M-033]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-16
---

# Meta-Prompt Deployment Needs Project Boundaries, Native Adapters, and Token ROI Gates

## Purpose

Meta-prompt evolution is not complete when the shared kernel text looks good.
It is complete only when the deployed agents, skills, helper scripts, and
reports preserve behavior with minimal static prompt cost, no project leakage,
and no role-scope drift.  The source of truth is the metaprompt bundle plus the
receiving project's `kernel-project.md`; generated artifacts are evidence, not
the place to hand-patch behavior.

## Practices

1. Keep project facts in the project overlay.
   - Shared kernels must not hard-code implementation paths, chapter names,
     experiment directories, figure formats, or local rule semantics.
   - `kernel-project.md` owns project identity, PR-rules, path conventions,
     validation commands, remote/local execution policy, and forbidden shortcuts.
   - If `prompts/meta` is a submodule, `kernel-project.md` can still live there,
     but sync tooling must snapshot/restore it as a user-owned overlay.
   - Deploy reports should record the project profile source and ownership so
     future operators know it is not an upstream file to overwrite.

2. Use native adapters, not vocabulary leakage.
   - Extract common control primitives, then map them into each domain's native
     artifacts.
   - Presentation uses `audience_profile.yaml`, `story_map.md`,
     `slide_spec.yaml`, role reviews, and deck exports.
   - Code uses equation/spec/interface, `SchemeCodePlan`, verifier evidence,
     tests, and acceptance-critical remaining delta.
   - Paper uses `ManuscriptSectionPlan`, claim register, source scope, reviewer
     issue tracking, and claim/evidence/rhetoric/submission freezes.
   - Do not force presentation terms such as audience belief, slide 2, or
     story maps into code or manuscript skills.

3. Build decks as projects, then converge them.
   - The stable deck workflow is
     `brief -> audience profile -> story map -> slide spec -> generation -> preview/export -> review -> issue register -> focused repair -> final acceptance`.
   - Story and audience decision come before visual polish.
   - Reviews should rotate lenses: primary audience, skeptic, Q&A, visual
     clarity, evidence, accessibility/delivery, and diff review.
   - Repeated review must reduce remaining delta; after stabilization, avoid
     zero-base review and block slide growth unless it closes a Must-fix
     decision issue.

4. Deploy everything from the metaprompt source.
   - Agents, Skill Capsules, base configs, helper scripts, schema reports,
     token reports, and wiki-injection reports should be generated from
     `prompts/meta/` plus `kernel-project.md`.
   - Do not hand-edit generated agents or skills to encode a rule.
   - If a generated artifact exposes a flaw, repair the metaprompt source or
     deploy script, regenerate, then audit the generated output.

5. Treat token ROI as a correctness gate.
   - Every generated agent prompt needs a static prompt budget.
   - Every Skill Capsule needs a `token_target`.
   - Deployment should emit `token_telemetry_report.json` and
     `token_roi_report.json`; over-budget skills or agents should fail unless
     an explicit waiver names the behavioral ROI.
   - Long procedures should live behind `full_ref`, SkillID, RULE_MANIFEST, or
     on-demand wiki refs, not in every generated prompt.
   - A prompt that is too large is not merely inefficient; it reduces the chance
     that the agent follows the highest-value rule at the right time.

6. Assign rules by role, not broad domain labels.
   - Domain-wide rule manifests are tempting but can over-activate the wrong
     workflow.
   - PaperWriter should not load presentation generation rules by default.
   - PresentationWriter should not inherit manuscript-writing rules merely
     because it lives in the paper domain.
   - Workflow coordinators and reviewers may need multiple adapters; builders
     should get only the operations they execute.

7. Audit generated outputs, not only source diffs.
   - Scan shared kernels for project leakage outside `kernel-project.md`.
   - Scan generated code/paper skills for presentation-specific artifacts.
   - Review role manifests for out-of-role operation IDs.
   - Check generated skills against `token_target`.
   - Check agents against the static prompt limit.
   - Require Q3 audit, AP-13, AP-17, token telemetry, token ROI, skill capsule
     generation, and schema reports to close the loop.

## Checklist

- Project overlay: are all project paths, PR semantics, and validation commands
  in `kernel-project.md` or derived project docs?
- Sync safety: does the submodule sync path preserve the user-owned project
  overlay?
- Native adapter: does each domain use its own artifact names and review gates?
- Generated-source boundary: did the change edit `prompts/meta/` and redeploy,
  rather than patch generated agents by hand?
- Role scope: does each generated agent receive only the operation IDs and
  SkillIDs it can execute or audit?
- Skill ROI: does every generated skill stay within `token_target`?
- Agent ROI: does every generated agent stay under its static prompt limit?
- Reportability: does deployment emit schema, token telemetry, token ROI, skill
  generation, wiki injection, and Q3 audit reports?
- Convergence: did review findings become issues, focused repairs, validation,
  and remaining-delta or final-acceptance records?

## Anti-Patterns

- Copying a useful workflow into every role instead of creating a native adapter.
- Encoding project-specific paths or PR meanings in shared kernel files.
- Treating generated skills as manually editable source files.
- Letting `token_target` be advisory while Q3 still passes.
- Passing source-level prompt audit without auditing regenerated agents/skills.
- Adding new review suggestions forever instead of shrinking unresolved delta.
- Moving `kernel-project.md` outside the manageable submodule layout when the
  chosen operation is to preserve it as a local overlay.

## Operational Consequence

Future meta-prompt work should preserve this chain:

```text
session/artifact lesson
-> shared primitive or domain-native adapter
-> kernel-project boundary check
-> generated agents/skills/scripts
-> token telemetry + token ROI
-> Q3/AP/generated-output audit
-> wiki card only after validation
```

This keeps the agent system portable, strict, and cheap enough to keep the
right rules active when they matter.
