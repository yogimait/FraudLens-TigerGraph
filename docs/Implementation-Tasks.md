# Implementation Tasks

> [[Home]] · [[Development-Plan]] · [[Architecture]]

Ordered task list. Each task includes objective, files, dependencies, acceptance criteria.

---

## Status Snapshot — 2026-09-23 (post-audit, see [[Audit]])

| Area | Status |
|---|---|
| Policy engine R1–R10 rewrite (`agent/policy.py`), routes, rule citations, §3a triggers | Completed — 24 policy tests pass |
| LangGraph uncertainty loop (`assess → request_evidence → simulate_response → reassess`), stopping conditions | Completed |
| Answer-file schema compliance (`agent/answer_writer.py` + `agent/scripts/validate_answers.py`) | Completed — 20/20 files validate |
| TigerGraph MCP client with pyTigerGraph fallback (`agent/tg_mcp.py`), 69 tools live | Completed |
| GraphRAG vector index + retrieval into LLM prompts (`agent/rag.py`) | Completed (local-hash embeddings fallback; DocChunk 28 chunks live) |
| Case memory: `similar_prior_cases` retrieval + `persist_investigation_case` write-back | Completed (written_to_graph=true on live runs) |
| Jev real typesafe-sdk calls with heuristic fallback (`agent/jev_client.py`) | Completed (API returns 402 no-credits → heuristic engine used) |
| Investigation queries installed on Savanna (7 queries incl. get_shared_device_cards) | Completed |
| Backend evidence/stats/approval-level handling + frontend citations/routes/uncertainty UI | Completed |
| Obsidian-style force-directed graph (`frontend/components/EvidenceGraph.tsx`, d3-force) | Completed |
| Benchmark live regeneration on 20 cases | Blocked by Groq 200K TPD quota — rerun `agent/scripts/run_benchmark.py` after quota reset (abort-guard now stops on degraded LLM output) |
| Known data gaps | FROM_DEVICE/BILLED_IN edges not ingested (device queries return []); ClosedCase ingest partial (40/5,565); graph card ids are card1-based, case_pack uses C{n}-K{n} style — resolved by edge-derived card lookup |

---

## Phase 0 — TigerGraph Setup

### T0.1 — Verify TigerGraph version and TigerVector
- **Objective**: Ensure the selected workspace supports required vector capabilities.
- **Actions**: Check Savanna workspace version. If not 4.2+, investigate upgrade paths before proceeding.
- **Acceptance**: Confirmed whether TigerVector is available.
- **Dependencies**: None

### T0.2 — Verify Jev SDK and API key
- **Objective**: Confirm Jev integration is viable.
- **Actions**: Test API key with current `jev` or `jevclient` PyPI package.
- **Acceptance**: Successful test API call.
- **Dependencies**: None

### T0.3 — Validate card_id deterministic mapping
- **Objective**: Ensure we can reconstruct exact card IDs from `transactions.csv` to match `case_pack.csv`.
- **Files**: `agent/scripts/validate_card_mapping.py` (new)
- **Actions**: Write script to group transactions by (customer_id, card1), assign K-index, and cross-reference with provided dataset IDs.
- **Acceptance**: Mapping is 1:1, stable, zero collisions, and exactly reproduces IDs without inventing any. Stop and report if mismatch occurs.
- **Dependencies**: None

### T0.4 — Create TigerGraph Savanna workspace
- **Objective**: Get a running TigerGraph instance
- **Actions**: Sign up savanna.tgcloud.io → "Explore with Your Own Data" → enable auto-stop/auto-start
- **Acceptance**: Workspace running, GSQL console accessible
- **Dependencies**: T0.1

### T0.5 — Define graph schema in GSQL
- **Objective**: Create all vertices and edges from [[Data-Model]]
- **Files**: `tigergraph/schema.gsql` (new)
- **Acceptance**: Schema installed, all vertex/edge types visible in TG Studio
- **Dependencies**: T0.4

### T0.6 — Write data ingestion script
- **Objective**: Python script to load all CSV files into TigerGraph
- **Files**: `agent/scripts/ingest_data.py` (new)
- **Actions**:
  - Parse transactions.csv (590K rows, selective columns)
  - Parse identity.csv (144K rows)
  - Parse closed_cases_history.csv (5,565 rows)
  - Derive Customer, Card, DeviceProfile, EmailDomain, BillingRegion vertices
  - Create all edges
  - Build NEXT edges (transaction ordering per card)
- **Acceptance**: All vertices/edges loaded, counts match source data
- **Dependencies**: T0.5
- **Edge cases**: 
  - card_id derivation from card1 field
  - Null/missing values in identity columns
  - 708 MB file needs streaming/chunking

### T0.7 — Load vector store content
- **Objective**: Load text content for GraphRAG retrieval
- **Files**: `agent/scripts/load_vectors.py` (new)
- **Actions**:
  - Embed and load analyst_notes from closed_cases_history
  - Embed and load fraud policy text
  - Embed and load pattern descriptions
- **Acceptance**: Vector search returns relevant results for "card testing pattern"
- **Dependencies**: T0.6
- **Status**: **Completed** as `agent/rag.py` + `agent/scripts/build_vector_index.py` (pattern docs + policy chunks + graph analyst notes; TigerVector primary path, in-memory fallback; TigerVector mode verified live)

### T0.8 — Verify graph with manual queries
- **Objective**: Confirm data loaded correctly
- **Actions**: Run test queries for each case_pack customer/card
- **Acceptance**: Can find transactions, devices, regions for case_pack entries
- **Dependencies**: T0.6

---

## Phase 1 — TigerGraph MCP

### T1.1 — Set up MCP server
- **Objective**: TigerGraph MCP running and connected to Savanna
- **Files**: `agent/mcp_config.json` (new)
- **Actions**: `pip install tigergraph-mcp`, configure connection
- **Acceptance**: MCP server starts, lists available tools
- **Dependencies**: T0.5
- **Status**: **Completed** as `agent/tg_mcp.py` (client spawning `tigergraph-mcp` stdio subprocess via the `mcp` SDK; handshake + tool listing verified, 69 tools; pyTigerGraph fallback on any MCP failure)

### T1.2 — Write GSQL investigation queries
- **Objective**: Create all GSQL queries from [[TigerGraph]]
- **Files**: `tigergraph/queries/*.gsql` (new)
- **Acceptance**: Each query returns expected results when called via MCP
- **Dependencies**: T1.1
- **Status**: **Completed** (`investigation_queries.gsql`: 3 original + `get_shared_device_cards`, `get_card_recent_window`, `get_region_activity`, `get_card_neighbor_degree`)

---

## Phase 2 — Agent Core

### T2.1 — Set up Python project
- **Objective**: Python project with FastAPI, LangGraph, dependencies
- **Files**: `agent/pyproject.toml`, `agent/requirements.txt`, `agent/main.py`
- **Acceptance**: `uvicorn agent.main:app` starts, `/health` returns OK
- **Dependencies**: None (can be parallel with Phase 0)

### T2.2 — Define InvestigationState
- **Objective**: LangGraph state schema
- **Files**: `agent/state.py` (new)
- **Acceptance**: State type passes mypy checks
- **Dependencies**: T2.1
- **Status**: **Completed 2026-09-23** (full TypedDict: assessment, evidence + requests, actions, SAR, outputs, graph-viz data, metadata counters; see [[Agent-Workflow]])

### T2.3 — Implement load_case node
- **Objective**: Parse case_pack, fetch flagged transaction
- **Files**: `agent/nodes/load_case.py` (new)
- **Acceptance**: Given case_id, returns populated state with case_data and flagged_txn
- **Dependencies**: T2.2, T1.1
- **Status**: **Completed 2026-09-23** as a node inside `agent/graph.py` (case_pack enrichment + TG fetch, graceful fallback to case-pack attributes)

### T2.4 — Implement investigate_graph node
- **Objective**: Run TigerGraph queries, collect evidence
- **Files**: `agent/nodes/investigate_graph.py` (new)
- **Acceptance**: Returns graph_evidence[], connected_card_ids, device profiles
- **Dependencies**: T2.3, T1.2
- **Status**: **Completed 2026-09-23** as a node inside `agent/graph.py` (all access via `tg_mcp` wrapper; device/card/window/shared-device/customer-cards queries; evidence + graph-viz data; graceful offline degradation)

### T2.5 — Implement retrieve_memory node
- **Objective**: Find similar closed cases
- **Files**: `agent/nodes/retrieve_memory.py` (new)
- **Acceptance**: Returns similar_prior_cases with case IDs from closed_cases_history
- **Dependencies**: T2.4, T0.4
- **Status**: **Completed** as `agent/memory.py` → `find_similar_cases` (pattern 0.5 / amount log-proximity 0.2 / identity overlap 0.3, CSV module cache)

### T2.6 — Implement assess_evidence node
- **Objective**: Synthesize evidence using LLM + Jev
- **Files**: `agent/nodes/assess_evidence.py` (new)
- **Acceptance**: Produces fraud_probability, pattern, verdict, affected_txn_ids
- **Dependencies**: T2.5
- **Status**: **Completed 2026-09-23** in `agent/llm.py` (calibrated synthesis, pattern enum enforcement, affected-id validation, confidence drivers, token counting) + `agent/graph.py` (`assess_evidence`/`reassess_evidence` nodes with deterministic clamps)

### T2.7 — Implement evidence request + simulate + reassess
- **Objective**: Evidence gathering loop
- **Files**: `agent/nodes/request_evidence.py`, `agent/nodes/simulate_response.py`, `agent/nodes/reassess_evidence.py` (new)
- **Acceptance**: Agent requests evidence, simulates response, updates assessment
- **Dependencies**: T2.6
- **Status**: **Completed 2026-09-23** as nodes inside `agent/graph.py` (request type by trigger/fraud-lean, deterministic denied/confirmed/no_reply simulation, assumption recorded verbatim, one request round per case)

### T2.8 — Implement apply_policy node
- **Objective**: Deterministic policy rules
- **Files**: `agent/nodes/apply_policy.py`, `agent/policy.py` (new)
- **Acceptance**: Actions + routes match policy rules R1–R10 for test cases
- **Dependencies**: T2.7
- **Status**: **Completed 2026-09-23** (`agent/policy.py` full rewrite: R1–R10 + §3a as code, route table auto/L1/L2, exposure-based BLOCK_CARD routing, dedup by highest-severity route, execution-order sorting, R10 guard, sar_required; tested in `agent/tests/test_policy.py`)

### T2.9 — Implement generate_outputs node
- **Objective**: LLM-generated summaries, SAR narratives
- **Files**: `agent/nodes/generate_outputs.py` (new)
- **Acceptance**: Produces valid summary, SAR narrative (when required), stop_reason
- **Dependencies**: T2.8
- **Status**: **Completed 2026-09-23** in `agent/llm.py` `generate_outputs` + `agent/graph.py` `generate_outputs` node; answer JSON assembled by `agent/answer_writer.py` `build_answer` (shared by API + CLI + benchmark)

### T2.10 — Implement persist_case node
- **Objective**: Write case to TigerGraph, save JSON file
- **Files**: `agent/nodes/persist_case.py` (new)
- **Acceptance**: Case vertex created in TG, JSON file matches answer format
- **Dependencies**: T2.9
- **Status**: **Completed** as `agent/memory.py` → `persist_investigation_case` (InvestigationCase upsert + INV_INVOLVES / INV_ON_CARD / INV_CONNECTED_TO / SIMILAR_TO edges, verified live)

### T2.11 — Wire LangGraph
- **Objective**: Complete graph with all nodes and conditional edges
- **Files**: `agent/graph.py` (new)
- **Acceptance**: End-to-end run on HHG-017 produces valid answer JSON
- **Dependencies**: T2.3–T2.10
- **Status**: **Completed 2026-09-23** (rebuilt `agent/graph.py`: 12 nodes + conditional `evidence_sufficient` edge; `retrieve_memory_context` node wires [[Jev]] hint → similar cases + GraphRAG; conditional request loop; persist + generate order per [[Agent-Workflow]])

### T2.12 — Integrate Groq GPT-OSS-120B
- **Objective**: LLM calls work with structured outputs
- **Files**: `agent/llm.py` (new)
- **Acceptance**: Evidence synthesis prompt returns valid structured JSON
- **Dependencies**: T2.6
- **Status**: **Completed 2026-09-23** (rewritten `agent/llm.py`: lazy Groq client, temperature 0, JSON mode, calibration instructions — risk_score is a prior — rag context + similar cases in prompt, pattern enum + affected-id validation, token counting from usage)

### T2.13 — Integrate Jev
- **Objective**: Classification calls work
- **Files**: `agent/jev_client.py` (new)
- **Acceptance**: Pattern classification returns valid distribution; fallback to LLM if unavailable
- **Dependencies**: T2.6
- **Status**: **Completed** (real `typesafe-sdk` calls: pattern Choice + sufficiency/coordination Noul; deterministic heuristic fallback with `"engine"` labeling and circuit breaker; TypeSafe API currently returns 402 no-credits, heuristics active)

---

## Phase 3 — Policy + All Triggers

### T3.1 — Test risk_score trigger cases
- **Files**: Review outputs for HHG-001, 002, 005, 007, 010, 012, 013, 015, 017, 019, 020
- **Acceptance**: Actions match policy for various risk levels
- **Status**: **In progress 2026-09-23** (`--dry-run` benchmark produces valid answers for all 20 cases offline; live LLM regeneration via backend still pending)

### T3.2 — Test customer_report trigger cases
- **Files**: Review outputs for HHG-003, 004, 006, 008, 009, 011, 016, 018
- **Acceptance**: Evidence simulation consistent (customer already complained → simulate denial)
- **Status**: **In progress 2026-09-23** (dispute path: R7 + customer_validation request with deterministic response simulation; verified in dry-run)

### T3.3 — Test analyst_request trigger case
- **Files**: Review output for HHG-014
- **Acceptance**: Agent investigates shared device across cards as trigger suggests
- **Status**: **In progress 2026-09-23** (dry-run valid; shared-device evidence requires live TigerGraph data)

### T3.4 — Validate SAR decisions
- **Acceptance**: FILE_REPORT in actions ↔ sar.file == true; narrative present when filed
- **Status**: **Completed 2026-09-23** (enforced in `agent/answer_writer.py` and checked by `agent/scripts/validate_answers.py`; policy tests cover the R2/R6/R9/§3a filing triggers)

### T3.5 — Validate stopping conditions
- **Acceptance**: Each case stops for a documented reason matching policy section 6
- **Status**: **Completed 2026-09-23** (`graph.evidence_sufficient` router + deterministic `_stop_reason`; LLM refines wording only)

### T3.6 — Answer schema validator (added)
- **Files**: `agent/scripts/validate_answers.py` (new)
- **Acceptance**: Strict README-schema check; exit 1 on violation
- **Status**: **Completed 2026-09-23** (all required fields, enums, route/rule citations, sar↔FILE_REPORT consistency, legitimate zeroing, `--known-ids` optional subset check, per-file report)

### T3.7 — Benchmark runner + offline dry-run (added)
- **Files**: `agent/scripts/run_benchmark.py` (rewritten)
- **Acceptance**: Iterates case_pack.csv against the NestJS API with 5s delay then validates; `--dry-run` runs the graph in-process with mocked TG/LLM and writes valid `cases/*.json` fully offline
- **Status**: **Completed 2026-09-23** (dry-run verified: 20/20 files written, validator reports 0 violations)

### T3.8 — Agent test suite (added)
- **Files**: `agent/tests/` (new: `test_policy.py`, `test_answer_writer.py`, `test_flow.py`, fixtures, offline mock TG)
- **Acceptance**: `agent\venv\Scripts\python.exe -m pytest agent/tests -q` passes with no network
- **Status**: **Completed 2026-09-23** (56 passed)

---

## Phase 4 — NestJS

### T4.1 — Install NestJS dependencies
- **Files**: `backend/package.json`
- **Actions**: `npm install @nestjs/config @nestjs/mongoose mongoose`
- **Status**: **Completed** (Replaced Atlas with Local MongoDB for network bypass)

### T4.2 — MongoDB Atlas setup
- **Actions**: Create Atlas cluster, get connection string
- **Files**: `backend/.env`
- **Status**: **Completed** (Switched to local MongoDB)

### T4.3 — Investigation module
- **Files**: `backend/src/cases/` (module, controller, service, schemas)
- **Status**: **Completed**

### T4.4 — Case endpoints
- **Files**: `backend/src/cases/` (controller, service)
- **Status**: **Completed** (`GET /cases`, `POST /cases/:id/trigger`)

### T4.5 — SSE endpoint
- **Files**: `backend/src/cases/cases.controller.ts`
- **Status**: **Deferred** (MVP uses synchronous polling/response for now)

### T4.6 — Approval module
- **Files**: `backend/src/cases/`
- **Status**: **Completed** (`POST /cases/:id/approve|reject`)

---

## Phase 5 — Frontend

### T5.1 — Case dashboard page
- **Status**: **Completed** (`app/page.tsx`)

### T5.2 — Investigation view (three-panel)
- **Status**: **Completed** (`app/cases/[id]/page.tsx`)

### T5.3 — SSE timeline component
- **Status**: **Deferred**

### T5.4 — Evidence panel
- **Status**: **Completed**

### T5.5 — Action comparison component
- **Status**: **Completed**

### T5.6 — Advanced graph visualization
- **Status**: **Completed** (Full interactive React Flow graph with custom Card/Txn/Device nodes and Legend)

### T5.7 — Approval queue page
- **Status**: **Completed** (Dedicated `/approvals` split-pane UI)

### T5.8 — Polish for demo
- **Status**: **Completed** (Tailwind animations, proper Empty States, layout fixes)

---

## Phase 6: E2E Benchmark Execution
- [x] Integrate `run_benchmark.py` with the NestJS API (`POST {BACKEND_URL}/cases/{id}/trigger`, 5s delay)
- [x] Strict schema validation via `agent/scripts/validate_answers.py` (replaces the earlier non-strict check)
- [x] Offline `--dry-run` executed 2026-09-23: 20/20 answer files written, 0 schema violations
- [x] Live LLM run of the 20 HHG cases end-to-end — **completed 2026-09-24 01:30**: stale pre-calibration outputs purged, regenerated via trickle runner on OpenRouter free model (`nvidia/nemotron-3-super-120b-a12b:free`); final distribution: 13 legitimate / 5 fraud / 2 uncertain, probabilities 0.08–0.81 (no 0.5 parking), 3 SARs filed; `validate_answers.py` 20/20, 0 violations
- [x] Save outputs in `cases/` directory

## Phase 7: UI & Dashboard Polish (Done)
- [x] Apply premium, modern styling (Tailwind CSS, clean aesthetics)
- [x] Add dynamic UI elements (Framer Motion, Shadcn components)
- [x] Polish data visualization and typography
- [x] Verify frontend responsiveness and load time
