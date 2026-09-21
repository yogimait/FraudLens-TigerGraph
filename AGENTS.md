# AGENTS.md — Core Project Rules

Follow these rules throughout the entire project. These are persistent project-level instructions and should be considered before starting any development task (applies to every coding agent working in this repo, including opencode).

---

## 1. Living Documentation & Obsidian

Maintain the project's documentation continuously as the codebase evolves.

- Keep important project knowledge in well-structured Markdown files that can be used inside an Obsidian Vault (the project's `docs/` folder).
- Document meaningful changes such as new features, architecture changes, APIs, data pipeline changes, integrations, workflows, and important technical decisions.
- Do not document trivial changes such as minor styling, variable renaming, formatting, or insignificant refactoring.
- Keep related documentation connected using Obsidian wiki links such as `[[Architecture]]`, `[[Simulation-Model]]`, or `[[Data-Pipeline]]`.
- When creating or updating documentation, maintain logical relationships between related documents rather than creating isolated files.
- Keep documentation synchronized with the actual implementation and update outdated documentation when necessary.

The documentation should act as the project's long-term technical memory and should help both developers and coding agents understand the system.

---

## 2. High-Quality Markdown Documentation

All documentation must be clear, structured, readable, and useful.

- Use proper Markdown headings and logical sections.
- Use bullet points and numbered lists where appropriate.
- Use Markdown tables when information is naturally tabular.
- Use Mermaid diagrams for architecture, workflows, data flow, sequences, or other concepts where a visual representation improves understanding.
- Explain not only what something does, but also how it works and why important decisions were made.
- Avoid unnecessary walls of text and avoid excessive documentation of obvious implementation details.
- Keep documentation visually clean and easy to navigate.
- Prefer linking to existing documentation instead of duplicating the same information across multiple files.

---

## 3. Professional Code Quality

Write code at a professional, production-quality software engineering standard.

- Follow consistent naming and casing conventions appropriate for the language (`snake_case` for Python modules, functions, and variables; `camelCase`/`PascalCase` for TypeScript).
- Use meaningful names for variables, functions, components, classes, and files.
- Keep functions and modules focused and maintainable.
- Avoid messy code, unnecessary complexity, duplication, dead code, unused files, unused imports, and unused variables.
- Remove obsolete code when it is no longer required.
- Choose appropriate data structures and algorithms for the problem.
- Avoid unnecessary dependencies; do not introduce a dependency when a simple existing solution is sufficient.
- Follow established project conventions before introducing new patterns.
- Apply engineering principles such as **KISS, DRY, YAGNI, separation of concerns, and single responsibility** pragmatically.
- Prefer clean, readable, maintainable solutions over clever or unnecessarily complex implementations.

---

## 4. Mandatory Rule & Context Review

Before starting any meaningful task:

1. Review this `AGENTS.md` file (and `README.md` if present).
2. Understand the requested task and identify which rules apply.
3. Inspect the relevant code, data files, and existing documentation before making changes.
4. Follow the project's existing architecture and conventions.
5. Implement the requested changes.
6. Update relevant documentation when the change is significant.
7. Before finishing, verify that the implementation and documentation remain clean and consistent.

These rules should be followed automatically for every task in this project. The user should not need to repeat them in every prompt.

If a task is ambiguous in a way that could significantly affect architecture, security, data integrity, or project behavior, ask for clarification before proceeding.

---

## 5. Project Docs for Every Important Part

Create and maintain a dedicated `.md` file in `docs/` for every important part of the project. A part counts as important when it is a major component, subsystem, workflow, or design area that others must understand or modify.

- Each major part gets its own file, named after the part, e.g. `PRD.md`, `Architecture.md`, `UI.md`, `API.md`, `Data-Model.md`, `Data-Pipeline.md`, `Agent.md`, `Graph-Schema.md`, `Deployment.md`, `Testing.md`.
- Create the file when the part first becomes meaningful (first meaningful work in that area), not earlier. Do not create empty placeholder files "for later".
- Each file must be cross-linked into the index and related docs using Obsidian wiki links (`[[Architecture]]`, `[[UI]]`, `[[API]]`).
- Update the corresponding file whenever the part changes in a meaningful way; keep it synchronized with the implementation.
- Use the existing `docs/` structure and conventions before creating new files; prefer extending or linking to an existing file over splitting into many small ones.

---

## 6. Obsidian Vault as the Source of Truth for Discovery

When you need to find a feature, file, component, or any project knowledge, consult the Obsidian vault first before searching the codebase blindly.

- The project's `docs/` folder is the project vault; the central hub vault `C:\Users\Hp\Obsidian\DevVault` indexes all projects. See the vault conventions in `C:\Users\Hp\Desktop\opencode_obsidian_setup.md` (per-project `docs/` as vault, wiki links, `Home.md` as project index, DevVault as cross-project hub).
- Start from `docs/Home.md` (project index) and follow the wiki links to the relevant doc, then to the code.
- When mapping new knowledge into the vault, follow Obsidian best practices: one note per concept, meaningful note names, wiki links between related notes, a Home/MOC index note, logical folder structure, and Mermaid diagrams for complex relationships.
- Keep the vault mapping complete and current: whenever a new feature, module, or important file is created, make sure it is discoverable from the vault (via a doc note and wiki links) so future agents find it through the vault, not by guessing.
- Prefer vault-first discovery over regex/grep hunting; treat the vault as the project's living map.

---

## Project Context Notes

- This project is a TigerGraph Agentic Fraud Investigation hackathon submission (HHGOA / IEEE-CIS Fraud dataset). Deadline and judging criteria are in `Initial-docs/TigerGraph Agentic Fraud Investigation HHGOA.md`; read the dataset README in `Initial-docs/dataset/` before touching data.
- Repo layout:
  - `agent/` — Python agent: fraud investigation loop (trigger → investigate → gather evidence → assess uncertainty → act → explain → update case memory), TigerGraph MCP client, LLM reasoning, GraphRAG, case memory.
  - `backend/` — NestJS (TypeScript) API serving the dashboard and agent-facing endpoints.
  - `frontend/` — Next.js analyst dashboard: investigation view, case progression, evidence, uncertainty, recommendations, next actions.
  - `Initial-docs/` — hackathon brief, dataset, planning notes. Source material; do not edit the dataset files.
- TigerGraph (Savanna or Community Edition) is the graph + vector store; the agent talks to it via TigerGraph MCP and GSQL. Graph schema, GSQL queries, and graph algorithms are core deliverables.
- Datasets and derived artifacts (graph loads, model artifacts, case outputs) are derived artifacts — never modify them by hand; rebuild them through scripts and document the change.
- Agent behavior must respect the fraud policy and permission model: recommend actions, execute only authorized ones, require approval where policy says so.
- Tests run before finishing changes; keep them passing.

---

## 7. Dataset Integrity Rules

These rules are non-negotiable and originate from the challenge requirements.

- **NEVER modify files in `Initial-docs/dataset/`**. These are the source-of-truth data files.
- **NEVER use the public Kaggle IEEE-CIS dataset** to look up fraud labels or outcomes. This is explicitly disqualification.
- **Every ID in answer files must exist in the provided dataset**. Made-up IDs score zero.
- **`risk_score` is an input, NOT an answer**. It is a reason to look, never a verdict.
- **Half the benchmark cases are likely legitimate**. An agent that blocks everything scores badly.
- **`fraud_probability` must be calibrated honestly** — it is scored for calibration.
- **`uncertain` is a valid verdict** and earns full credit on ambiguous cases if actions follow policy R1 and R8.

---

## 8. Answer Format Compliance

All 20 answer files must strictly follow the JSON schema defined in `Initial-docs/dataset/README (1).md` → "Answer Format" section.

- One JSON file per case: `cases/<case_id>.json`
- Three-part structure: `case` + `sar` + `next_best_actions`
- `initial` actions recorded BEFORE evidence requests; `final` actions AFTER
- `sar.file` must agree with whether `FILE_REPORT` appears in final actions
- For `legitimate` verdict: `affected_txn_ids` is empty, `exposure_usd` is 0, `sar.file` is false
- Evidence must cite `source` (graph|document|customer|external), `ref` (query name), `entity_ids`

---

## 9. Policy Engine Rules

The fraud policy in the dataset README is the law. These rules MUST be enforced deterministically in code.

- **Policy rules R1–R10 are implemented as code**, not LLM prompts.
- **The LLM must NOT override policy**. It provides evidence and reasoning; policy determines actions.
- **Approval routes (auto/L1/L2) must be exactly as defined in the policy table**.
- **Only `auto` actions may be executed by the agent**. L1/L2 are recommendations.
- **Case creation triggers**: `fraud_probability >= 0.30`, evidence requested, or customer dispute.
- **SAR filing triggers**: confirmed/strongly suspected fraud AND (exposure > $1,000 OR shared device/region with other fraud OR coordinated/undocumented pattern).

---

## 10. Documentation-First Development

Before implementing any feature, consult `docs/` for:

1. **Architecture** (`docs/Architecture.md`) — component responsibilities and boundaries
2. **Agent Workflow** (`docs/Agent-Workflow.md`) — state machine, node definitions, tool inventory
3. **Data Model** (`docs/Data-Model.md`) — TigerGraph schema
4. **Policy Engine** (`docs/Policy-Engine.md`) — deterministic rules R1–R10
5. **API** (`docs/API.md`) — endpoint contracts
6. **Development Plan** (`docs/Development-Plan.md`) — phased roadmap
7. **Decisions** (`docs/Decisions.md`) — why things are the way they are

Start from `docs/Home.md` and follow wiki links to the relevant doc.

---

## 11. Component Boundaries

Respect the separation of concerns defined in `docs/Architecture.md`:

- **TigerGraph** discovers facts (graph traversal, algorithms, vector search)
- **Jev** makes fast structured decisions (classification, sufficiency, routing)
- **LLM** reasons over evidence and generates text (synthesis, summaries, SAR narratives)
- **Policy engine** determines actions deterministically (code, not LLM)
- **NestJS** serves the application API and manages app state (MongoDB)
- **Next.js** renders the analyst dashboard
- **Python agent** orchestrates the investigation (LangGraph state machine)

Do NOT let one component do another's job.