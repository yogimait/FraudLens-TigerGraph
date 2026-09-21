# Development Plan — Phased Roadmap

> [[Home]] · [[Architecture]] · [[Implementation-Tasks]]

## Timeline

Deadline: **September 24, 2026** (from today ~3 days).

## Phase 0 — Foundation (First)
**Objective**: TigerGraph graph operational with data loaded.

**Prerequisites**: TigerGraph Savanna account, dataset files
**Tasks**:
1. Verify TigerGraph Savanna version and TigerVector availability.
2. Verify Jev SDK package and API key validity.
3. Validate `card_id` deterministic mapping from `transactions.csv` against provided IDs in `case_pack.csv` and `closed_cases_history.csv`.
4. Create TigerGraph Savanna workspace ("Explore with Your Own Data")
5. Define graph schema (vertices + edges from [[Data-Model]])
6. Write data ingestion script (Python) for transactions.csv, identity.csv, closed_cases_history.csv
7. Load core data: Customer → Card → Transaction → OWNS → MADE
8. Load identity layer: DeviceProfile → FROM_DEVICE, EmailDomain, BillingRegion
9. Load closed cases: ClosedCase → INVOLVES, ON_CARD, CONNECTED_TO
10. Build NEXT edges (transaction ordering within card)
11. Verify with manual GSQL queries — can we find a customer's transactions? Device neighbors?

**Outputs**: Validated architecture assumptions and loaded TigerGraph graph with all entities.
**Acceptance**: `card_id` mapping exactly matches provided data without creating fake IDs. Run `get_card_transactions` for a case_pack card_id and get results.
**Risks**: Large CSV ingestion may need chunking; `card_id` collisions or derivation mismatches.
**Dependencies**: None

---

## Phase 1 — TigerGraph MCP + Queries
**Objective**: Agent can query TigerGraph via MCP tools.

**Prerequisites**: Phase 0 complete
**Tasks**:
1. Install tigergraph-mcp (`pip install tigergraph-mcp`)
2. Configure MCP server to connect to Savanna workspace
3. Write GSQL queries from [[TigerGraph]]: get_card_transactions, get_device_neighbors, detect_card_testing, etc.
4. Install and test MCP queries
5. Set up vector index for closed_case analyst_notes
6. Set up vector index for policy text and pattern descriptions
7. Test GraphRAG retrieval: "find similar cases to this evidence pattern"

**Outputs**: Working MCP server with all investigation queries
**Acceptance**: Call each GSQL query via MCP and get correct results
**Risks**: MCP version compatibility; TigerVector configuration
**Dependencies**: Phase 0

---

## Phase 2 — Python Agent Core
**Objective**: LangGraph state machine processes a single case end-to-end.

**Prerequisites**: Phase 1 complete
**Tasks**:
1. Set up Python project (`agent/`): FastAPI, LangGraph, dependencies
2. Define `InvestigationState` TypedDict
3. Implement LangGraph nodes:
   - `load_case` — parse case_pack data, fetch flagged transaction
   - `investigate_graph` — run TG queries, collect evidence
   - `retrieve_memory` — search similar closed cases
   - `assess_evidence` — synthesize evidence (LLM + Jev)
   - `request_evidence` + `simulate_response` + `reassess_evidence`
   - `apply_policy` — deterministic policy engine
   - `generate_outputs` — LLM summaries, SAR narratives
   - `persist_case` — write to TigerGraph, save JSON
4. Wire conditional edges (evidence_sufficient logic)
5. Integrate Groq GPT-OSS-120B for LLM calls
6. Integrate Jev for classification
7. Test on ONE case (e.g., HHG-017 — simple risk_score case)
8. Verify output matches answer format exactly

**Outputs**: Agent produces valid answer JSON for 1 case
**Acceptance**: HHG-017.json matches schema, evidence is from graph, policy rules cited
**Risks**: LangGraph Python API surface; Groq rate limits; Jev API changes
**Dependencies**: Phase 1

---

## Phase 3 — Policy Engine + All Trigger Types
**Objective**: Agent handles all three trigger types correctly.

**Prerequisites**: Phase 2 complete
**Tasks**:
1. Implement all policy rules R1–R10 in deterministic code
2. Test risk_score trigger cases (HHG-001, HHG-002, etc.)
3. Test customer_report trigger cases (HHG-003, HHG-004, etc.)
4. Test analyst_request trigger (HHG-014)
5. Implement evidence request simulation logic
6. Test initial vs final action changes
7. Test SAR generation (FILE_REPORT cases)
8. Test CLOSE_NO_FRAUD (legitimate cases)

**Outputs**: Agent produces valid answer JSONs for all trigger types
**Acceptance**: At least 5 cases produce correct-looking outputs
**Risks**: Evidence simulation assumptions affect scoring
**Dependencies**: Phase 2

---

## Phase 4 — NestJS Integration
**Objective**: NestJS serves as the application backend between frontend and agent.

**Prerequisites**: Phase 3 partially complete (agent works for some cases)
**Tasks**:
1. Install MongoDB dependencies (`@nestjs/mongoose`, `mongoose`, `@nestjs/config`)
2. Set up MongoDB Atlas connection
3. Create investigation module (controller, service, schemas)
4. Implement `POST /api/cases/:id/investigate` → calls Python agent
5. Implement `GET /api/cases` → returns case_pack data + status
6. Implement `GET /api/cases/:id/result` → returns answer JSON
7. Implement SSE endpoint `GET /api/cases/:id/stream`
8. Create approval module (basic CRUD)

**Outputs**: NestJS API serving case data and triggering investigations
**Acceptance**: Frontend can list cases and trigger investigation via API
**Risks**: SSE implementation complexity; Python agent communication
**Dependencies**: Phase 3 (partial)

---

## Phase 5 — Frontend Dashboard
**Objective**: Analyst dashboard shows investigation process.

**Prerequisites**: Phase 4 complete
**Tasks**:
1. Build case dashboard page (`/`)
2. Build investigation view (`/case/:id`) with three-panel layout
3. Implement SSE consumption for live timeline
4. Build evidence panel with source badges
5. Build action comparison (initial vs final)
6. Add basic graph visualization (entity relationships)
7. Build approval queue page
8. Polish for demo (animations, status badges, colors)

**Outputs**: Working dashboard showing live investigation
**Acceptance**: Can watch agent investigate a case in real-time through the UI
**Risks**: SSE reliability; graph visualization complexity
**Dependencies**: Phase 4

---

## Phase 6 — Benchmark All 20 Cases
**Objective**: Run agent on all 20 cases, validate outputs.

**Prerequisites**: Phase 3 complete, Phase 5 ideally complete
**Tasks**:
1. Run agent on all 20 cases
2. Validate each output JSON against schema
3. Review verdicts, patterns, evidence for reasonableness
4. Check policy compliance (correct actions for each case)
5. Check SAR decisions (filed when required, not filed when not)
6. Verify all IDs exist in dataset
7. Check evidence provenance (all refs traceable to actual queries)
8. Ensure case memory works (later cases can find earlier ones)
9. Fix any incorrect/missing outputs
10. Save all 20 JSON files to `cases/` directory

**Outputs**: `cases/HHG-001.json` through `cases/HHG-020.json`
**Acceptance**: All 20 files valid, schema-compliant, policy-compliant
**Risks**: Some cases may require manual investigation to understand
**Dependencies**: Phase 3

---

## Phase 7 — Demo, Blog, Submission
**Objective**: Complete all submission requirements.

**Prerequisites**: Phase 5 + Phase 6
**Tasks**:
1. Record 3–5 minute demo video
2. Write technical blog post
3. Post on X or LinkedIn
4. Final README.md update
5. Ensure `cases/` folder has all 20 JSONs
6. Clean up repo
7. Submit

**Outputs**: Complete submission
**Acceptance**: All 6 deliverables from [[PRD]] completed
**Risks**: Time pressure
**Dependencies**: All previous phases

---

## Critical Path

```
Phase 0 (TigerGraph) → Phase 1 (MCP) → Phase 2 (Agent core)
     → Phase 3 (Policy + all triggers) → Phase 6 (20 cases)
                                                    ↓
Phase 4 (NestJS) → Phase 5 (UI) ──────────→ Phase 7 (Submit)
```

**Phase 6 (20 cases) is the MOST CRITICAL deliverable** — it's 50% of the score (investigation accuracy + next best action).

UI is important for demo (10%) but secondary to agent correctness.

## Cross-References

- Task breakdown: [[Implementation-Tasks]]
- Architecture: [[Architecture]]
- Agent design: [[Agent-Workflow]]
