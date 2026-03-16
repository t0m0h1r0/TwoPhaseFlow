# Role

You are a **LaTeX Refactoring and Academic Writing Compliance Engine**.

Your task is to automatically detect and fix **hard-coded section, figure, table, and equation references** in the LaTeX project.

Hard-coding references is strictly forbidden in this repository.

You must convert all manual references to proper LaTeX cross-reference commands.

---

# Target Repository

Scan the entire repository and analyze:


paper//*.tex
paper//.sty
paper/**/.cls
docs//*.md
instructions//*.md


---

# Problem Definition

Some LaTeX source files contain **hard-coded references**, such as:

Bad examples:


Section 3
section 4
Eq. (12)
Figure 5
Table 2
see 3.1


These must **never be written manually**.

Instead, LaTeX cross-reference commands must be used.

---

# Correct LaTeX Usage

## Sections

Bad:


In Section 3 we show...


Correct:


In Section~\ref{sec:method} we show...


---

## Equations

Bad:


From Eq. (12) we obtain


Correct:


From Eq.~\eqref{eq:poisson} we obtain


---

## Figures

Bad:


Figure 4 shows


Correct:


Figure~\ref{fig:velocity} shows


---

## Tables

Bad:


Table 2 summarizes


Correct:


Table~\ref{tab:results} summarizes


---

# Tasks

## 1. Scan All .tex Files

Search for patterns indicating hard-coded references:

Examples:


Section [0-9]
section [0-9]
Eq. 
[
0
−
9
]
+
[0−9]+
Figure [0-9]
Table [0-9]
[0-9]+.[0-9]+


Determine whether these refer to actual document elements.

---

## 2. Detect Correct Labels

Locate the correct labels associated with:


\section{}
\subsection{}
\subsubsection{}
\begin{equation}
\begin{figure}
\begin{table}


Typical labels:


sec:
subsec:
eq:
fig:
tab:


If labels do not exist, **create them** following the naming rules below.

---

# Label Naming Convention

You must enforce consistent labels.

Sections


\label{sec:<name>}


Subsections


\label{subsec:<name>}


Equations


\label{eq:<name>}


Figures


\label{fig:<name>}


Tables


\label{tab:<name>}


Names must be **semantic**, not numeric.

Bad:


\label{eq1}


Good:


\label{eq:navier_stokes}


---

# 3. Automatically Rewrite the Text

Replace hard-coded references with:


\ref{}
\eqref{}


Examples:

Before


As shown in Section 4.2, the velocity...


After


As shown in Section~\ref{subsec:velocity_solver}, the velocity...


---

# 4. Insert Missing Labels

If a referenced element does not have a label, add one:

Example:

Before


\section{Projection Method}


After


\section{Projection Method}
\label{sec:projection_method}


---

# 5. Update Writing Instruction Files (.md)

Locate all documentation files that instruct the LLM to write LaTeX:


docs//*.md
instructions//*.md


Update them to include the following strict rule:

---

## Cross-Reference Policy (Mandatory)

The following practices are **strictly prohibited**:

- Writing section numbers manually
- Writing equation numbers manually
- Writing figure numbers manually
- Writing table numbers manually

Always use LaTeX cross references:


\ref{}
\eqref{}


Example:

Bad


Section 3 explains


Correct


Section~\ref{sec:method} explains


All structural elements must contain labels.

---

# 6. Prevent Future Violations

Add a **LaTeX Authoring Rules** section to the main instruction file:


docs/latex_authoring_rules.md


This must include:

- label naming rules
- reference usage rules
- prohibited patterns
- examples

---

# 7. Generate a Refactoring Report

Create a report file:


docs/reference_refactor_report.md


Include:

1. Files modified
2. Hard-coded references found
3. Labels added
4. References replaced
5. Remaining ambiguous cases

---

# Output Requirements

You must output:

1. Modified `.tex` files
2. Updated `.md` instruction files
3. A new rule file:
   

docs/latex_authoring_rules.md


4. A refactoring report


docs/reference_refactor_report.md


---

# Quality Requirements

The following must hold after refactoring:

- No manual section numbers remain
- All equations are referenced via `\eqref`
- All figures use `\ref`
- All tables use `\ref`
- All structural elements have labels
- Label naming follows repository conventions

---

# Important

Do NOT introduce compilation errors.

After modification, ensure the document still compiles correctly.

---

# Begin

Analyze the repository and perform the refactoring.