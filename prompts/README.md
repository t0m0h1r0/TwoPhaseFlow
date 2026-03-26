# **Research-to-Paper-to-Code Workflow System**

This system is a deterministic, self-evolving prompt architecture designed to transform ideas into "validated scientific papers," "correct numerical solvers," and "robust infrastructure."

It is designed NOT to maximize the LLM's "creativity," but rather to maximize **Correctness, Traceability, Reproducibility, and Structural Integrity**.

## **1\. Core Axioms**

This system operates on strict rules defined in meta-prompt.md.

* **3-Layer Traceability:** The chain of Equation → Discretization → Code must ALWAYS be preserved.  
* **External Memory First:** Never rely on the LLM's implicit context. All states, decisions, and assumptions must be explicitly written to files under the docs/ directory (e.g., ACTIVE\_STATE.md, ASSUMPTION\_LEDGER.md).  
* **Strict Layer Separation:** Logic/content/tags/styles must be separated. The numerical solver (core math) and infrastructure (I/O, logging) must be completely isolated.  
* **Diff-First Output:** Full file rewrites are prohibited. The system enforces patch-style edits to save tokens and prevent context destruction.

## **2\. Directory Structure**

We recommend the following directory layout for your project. Note that all core system prompts are stored in the meta/ directory.

project-root/  
├── meta/                      \# Core system prompts  
│   ├── meta-prompt.md         \# The Constitution / Core rules  
│   ├── meta-bootstrapper.md   \# Bootstrapper for initial agent generation  
│   ├── prompt-architect.md    \# \[Generated\] Creates role-specific prompts  
│   ├── prompt-compressor.md   \# \[Generated\] Compresses memory/prompts  
│   └── prompt-auditor.md      \# \[Generated\] Validates outputs against axioms  
│  
├── agents/                    \# \[Generated\] Task-specific prompts (e.g., paper-writer)  
│  
├── docs/                      \# External Memory (Mandatory)  
│   ├── ACTIVE\_STATE.md        \# Current phase and next actions  
│   ├── CHECKLIST.md           \# Task completion status  
│   ├── ASSUMPTION\_LEDGER.md   \# Ledger of constraints and assumptions  
│   ├── LESSONS.md             \# Record of failures and solutions  
│   └── ARCHITECTURE.md        \# High-level design  
│  
├── paper/                     \# LaTeX workspace for the paper  
└── src/                       \# Source code  
    ├── solver/                \# Pure numerical computation core  
    └── infra/                 \# I/O, logging, visualization

## **3\. Initial Deployment (Bootstrapping)**

To start using the system, you need to generate the **Core Agents** optimized for your specific execution environment (e.g., Claude, Codex, Ollama).

### **Shortest Path to Deployment**

For the initial deployment, simply place these two files in your meta/ directory:

1. meta-prompt.md  
2. meta-bootstrapper.md

### **First Execution**

Run your LLM (preferably an agentic IDE tool) with a command like this:

Execute EnvMetaBootstrapper  
Using meta-bootstrapper.md  
On meta-prompt.md  
Target Claude

After execution, follow the DEPLOYMENT NOTES provided in the output to save prompt-architect.md, prompt-compressor.md, and prompt-auditor.md into the meta/ directory. Your initial deployment is now complete.

## **4\. Author's Notes & Best Practices: The Claude Code Workflow**

**Conclusion:** Claude Code (in VSCode) is highly compatible with this system—much more so than standard chat interfaces or basic completion tools.

Because this architecture is fundamentally a **"File-Based State Management System"**, you must treat the LLM as a **File Manipulation Agent**, not just a text generator.

### **The Optimal Workflow (Zero Copy-Paste)**

Instead of having the LLM print prompts inline for you to copy, instruct Claude to generate the files directly in your workspace.

1. **Bootstrap via File Generation:**  
   When running the bootstrapper, ensure your prompt includes instructions like:*"You are a file-generating agent. Read meta-prompt.md and generate three files (prompt-architect.md, prompt-compressor.md, prompt-auditor.md). DO NOT print prompts inline. Instead, WRITE them directly as files in the meta/ workspace."*  
   Run this via @bootstrap.md or Run bootstrap.md in Claude Code. The files will be created automatically, eliminating human error.  
2. **Diff-First Update Mode:**  
   Once the initial files are generated, switch to an "Update Mode" for future iterations.*"If files already exist, DO NOT rewrite. Apply minimal diffs only. Preserve existing structure."*  
   This aligns perfectly with the system's diff \> rewrite axiom.  
3. **Advanced: Pipeline Automation:**  
   You can further automate the workflow by defining pipelines in your bootstrapper:  
   *Step 1: Generate agents → Step 2: Compress prompts → Step 3: Audit prompts → Step 4: Auto-fix if needed.*  
   If you change meta-prompt.md in the future, you can simply trigger a command to automatically update all downstream agents via diffs.

## **5\. Executing Tasks**

Once your core agents are ready, use prompt-architect.md to generate task-specific prompts (e.g., paper-writer.md, solver-dev.md, infra-engineer.md).

**The Execution Loop:**

1. **Record State:** Update docs/ACTIVE\_STATE.md before starting.  
2. **Single-Action Discipline:** Load only ONE role-specific prompt per step.  
3. **Apply Patch:** The LLM will output a diff/patch. Apply it directly to the code or paper.  
4. **Record Assumptions:** Log any new constraints to docs/ASSUMPTION\_LEDGER.md with an ASM-ID.  
5. **Audit:** Run the Auditor agent to ensure layer separation and solver purity are maintained before merging the changes.

## **6\. Meta Rules (Reminders)**

* **Diff \> Rewrite:** Always output minimal changes to prevent context destruction.  
* **Stop Early \> Guess:** If the agent lacks information, it must STOP and escalate, rather than hallucinating or guessing.  
* **Explicit \> Implicit:** All decisions must be recorded in the docs/ external memory with IDs. Never rely on the LLM's context window memory.