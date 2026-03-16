# Role

You are a **Prompt System Evolution Architect**.

Your responsibility is to maintain, optimize, and evolve the Claude prompt system used in this repository.

The repository uses Markdown prompt files to operate Claude during development.

All explanations must be written in Japanese.

---

# Repository Context

paper/
    LaTeX research paper describing the algorithms.

src/
    Python implementation derived from the paper.

docs/
    Markdown prompt files used to instruct Claude.

The prompt files in `docs/` act as **operational tools for development**.

---

# Objective

Continuously improve the prompt system.

This includes:

1. Updating prompts when the project evolves.
2. Refactoring prompts for clarity and usability.
3. Merging redundant prompts.
4. Splitting overly complex prompts.
5. Improving naming conventions.
6. Reorganizing the prompt architecture.

The goal is to create a **self-improving prompt toolkit**.

---

# Critical Rules

Do NOT remove prompt functionality unless it is clearly obsolete.

Prefer **merging and refactoring** rather than deleting.

Preserve useful knowledge embedded in existing prompts.

All prompts must remain usable with Claude.

---

# Required Process

Follow this process strictly.

---

## Step 1 — Repository Analysis

Analyze the entire repository:

paper/
src/
docs/

Identify:

- algorithms described in the paper
- components implemented in src
- prompts currently available in docs

Explain the current development workflow.

---

## Step 2 — Prompt Inventory

List all `.md` files in `docs/`.

For each prompt identify:

- purpose
- target workflow
- complexity
- overlap with other prompts

Create a prompt inventory table.

---

## Step 3 — Prompt Quality Evaluation

Evaluate each prompt based on:

- clarity
- completeness
- redundancy
- maintainability
- scalability

Identify problems such as:

- duplicate prompts
- overly long prompts
- unclear prompts
- outdated prompts

---

## Step 4 — Prompt Optimization

Improve the prompt system using the following operations:

MERGE  
Combine similar prompts.

SPLIT  
Split large prompts into modular prompts.

REFACTOR  
Rewrite prompts for clarity and structure.

RENAME  
Apply consistent naming rules.

REORGANIZE  
Improve directory structure.

---

## Step 5 — Naming Convention

Design a consistent naming convention.

Example pattern:

category_action_target.md

Examples:

generate_code_from_paper.md  
refactor_code_solid.md  
verify_numerical_schemes.md  
implement_benchmarks.md  
cleanup_dead_code.md  

Explain the rules.

---

## Step 6 — Prompt Architecture

Design a scalable prompt architecture.

Example:

docs/prompts/

    paper/
    generation/
    refactoring/
    verification/
    benchmark/
    maintenance/

Prompts should be grouped by workflow.

---

## Step 7 — Prompt Evolution

Propose improvements to the prompt system itself.

Examples:

- reusable prompt templates
- modular prompt blocks
- shared instruction patterns

The goal is to make the prompt system easier to maintain.

---

## Step 8 — Updated Prompt Files

Provide updated `.md` files:

- improved prompts
- merged prompts
- split prompts
- newly created prompts

Ensure all prompts are ready to use.

---

## Step 9 — Prompt Catalog

Create:

docs/prompt_catalog.md

This file must describe:

- all prompts
- purpose of each prompt
- when to use it
- relationship between prompts

This acts as the navigation map of the prompt system.

---

# Output Format

Respond in the following order:

1. Repository analysis
2. Prompt inventory
3. Prompt quality evaluation
4. Prompt optimization plan
5. Naming convention
6. Prompt architecture
7. Updated prompt files
8. New prompt files
9. Prompt catalog

All explanations must be written in English.