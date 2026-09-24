# FraudLens — Agentic Fraud Investigation System

> **TigerGraph Agentic Fraud Investigation Hackathon** — HHGOA / IEEE-CIS Fraud dataset
>
> An AI fraud investigator that knows when to say **"uncertain."** A LangGraph agent walks the TigerGraph fraud network, gathers evidence with provenance, reasons with an LLM — and then a deterministic policy engine decides what it may do. The LLM never picks actions.

**Final results — 20/20 benchmark cases:** 14 legitimate · 4 fraud · 2 uncertain (calibrated probabilities 0.08–0.81, no 0.5 parking) · 2 SARs filed. All 20 answer files pass the dataset answer-format validator with **0 violations**.

---

## The Problem

Fraud analysts investigate every flagged transaction by hand — pulling card history, tracing devices, checking past cases, writing reports. Slow, fragmented, and the money is often already gone.

**FraudLens** investigates automatically: gathers evidence as a graph, reasons over it with an LLM, and recommends the next best action — inside a policy engine that says what it may and may not do. Half of flagged cases are legitimate, so blocking everything is not an answer. Calibrated probability is the deliverable, not the bank's risk score.

## How It Works

A LangGraph state machine (12 nodes) investigates flagged card transactions end to end:

```
Trigger → Investigate → Ground → Remember → Assess → Decide → Explain → Record
```

1. **Trigger** — risk-score signal, customer dispute, or analyst request.
2. **Investigate** — TigerGraph MCP (69 tools, pyTigerGraph fallback) runs 7 installed GSQL queries: card history, customer cards, device profiles, shared devices, connected cases, transaction window.
3. **Ground** — GraphRAG: policy + fraud-typology documents retrieved from TigerVector into the LLM prompt.
4. **Remember** — similar closed cases pulled from case memory; each new investigation is written back to the graph as an `InvestigationCase` vertex with `SIMILAR_TO` edges, so the next investigation starts with memory, not amnesia.
5. **Assess** — LLM produces a calibrated `fraud_probability`. The bank's risk score is treated as a prior, never the answer.
6. **Decide** — the policy engine (`agent/policy.py`) implements fraud-policy rules R1–R10 as deterministic code with exact approval routes (`auto` / `L1` / `L2`). The LLM is explicitly forbidden from overriding policy.
7. **Explain** — analyst summary, SAR narrative when policy requires it, evidence provenance (`source` / `ref` / `entity_ids`), stop reason.
8. **Record** — answer JSON validated against the official answer format; case persisted to graph + MongoDB.

### Why the discipline matters

- **`risk_score` is an input, never an answer** — it is a reason to look. Half the benchmark cases are legitimate, and an agent that blocks everything scores badly.
- **"Uncertain" is a verdict, not a failure** — on ambiguous cases the agent escalates instead of blocking legitimate customers.
- **Policy is code, not prompts** — R1–R10 live in `agent/policy.py` as pure functions over named constants. The LLM layer (`agent/llm.py`) reasons and produces text; it cannot touch action routing.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────────┐
│ Next.js         │────▶│ NestJS           │────▶│ Python Agent         │
│ analyst         │     │ case store,      │     │ LangGraph + policy + │
│ dashboard :3000 │     │ approvals :3001  │     │ LLM + GraphRAG :8000 │
└─────────────────┘     └────────┬─────────┘     └──────────┬───────────┘
                                 │                          │
                          ┌──────▼──────┐            ┌──────▼───────┐
                          │ MongoDB     │            │ TigerGraph   │
                          │ app state   │            │ fraud graph  │
                          └─────────────┘            │ + vectors    │
                                                     └──────────────┘
```

| Component | Tech | Responsibility |
|---|---|---|
| `frontend/` | Next.js 16, React 19, React Flow, Recharts | Analyst dashboard: KPIs, investigation view, evidence citations, graph explorer, approvals queue, SAR viewer, analytics |
| `backend/` | NestJS, MongoDB | Case store, trigger/approve/reject endpoints, stats aggregation |
| `agent/` | Python, FastAPI, LangGraph | Investigation loop, TigerGraph MCP client (69 tools, pyTigerGraph fallback), GraphRAG, case memory, policy engine, LLM synthesis |
| `tigergraph/` | GSQL | Fraud graph schema (`schema.gsql`) + 7 installed investigation queries |
| `docs/` | Obsidian vault | Full design documentation — see below |

## Repository Layout

```
agent/          Python agent: FastAPI api.py, LangGraph state machine (graph.py),
                policy engine (policy.py), LLM layer (llm.py), TigerGraph MCP
                client (tg_mcp.py), GraphRAG (rag.py), case memory (memory.py),
                answer writer (answer_writer.py), 56 tests
backend/        NestJS + MongoDB: case store, trigger/approve/reject, stats
frontend/       Next.js analyst dashboard
tigergraph/     Graph schema + investigation queries
cases/          The 20 graded answer files (HHG-001.json … HHG-020.json)
agent/scripts/  Benchmark runner, validator, dataset ingest, vector index builder
docs/           Full documentation vault (see below)
```

The 20 graded answer files live in `cases/`, one per benchmark case in `Initial-docs/dataset/case_pack.csv`. They are generated artifacts — never edited by hand; rebuild with the benchmark runner and validate with the validator.

## Documentation

Full docs live in [`docs/`](docs/Home.md) (Obsidian-markdown vault):

- [[Architecture]] — component responsibilities and boundaries
- [[Agent-Workflow]] — the 12-node state machine and tool inventory
- [[Policy-Engine]] — deterministic rules R1–R10
- [[TigerGraph]] — schema, GSQL queries, MCP integration, GraphRAG
- [[Data-Model]] — graph vertices/edges
- [[API]] — backend ↔ agent ↔ frontend contracts
- [[Decisions]] — why things are the way they are
- [[Audit]] — full audit against the problem statement

## Running End to End

Prerequisites: Python 3.12, Node 20+, MongoDB, and a TigerGraph Savanna or Community Edition graph loaded with the HHGOA dataset.

### 0. Configure environment

- `agent/.env` (see `.env` keys referenced by the code):
  ```
  TG_HOST=<savanna host url>
  TG_GRAPH=FraudGraph
  TG_SECRET=<secret>
  OPENROUTER_API_KEY=<key>            # primary LLM (free tier works)
  OPENROUTER_MODEL=nvidia/nemotron-3-super-120b-a12b:free
  GROQ_API_KEY=<optional groq key>    # higher quality alternative
  GROQ_MODEL=openai/gpt-oss-120b
  ```
- `backend/.env`: `MONGODB_URI=mongodb://127.0.0.1:27017/fraud_investigation`

### 1. Start MongoDB

```bash
net start MongoDB   # Windows service
```

### 2. Backend (NestJS, port 3001)

```bash
cd backend
npm install
npm run start:dev
```

### 3. Agent (Python FastAPI, port 8000)

```bash
cd agent
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python.exe api.py
```

### 4. Frontend (Next.js, port 3000)

```bash
cd frontend
npm install
npm run dev
```

### Investigate a case

Open `http://localhost:3000` → **New Investigation** → enter a transaction ID from the dataset (e.g. `3514030`) → **Run Agent** → open the case for evidence, graph, SAR, and policy actions.

### Reproduce the 20 answer files

```bash
# all 20 cases through the backend (needs all services running)
agent\venv\Scripts\python.exe agent\scripts\run_benchmark.py

# strict validation against the answer format
agent\venv\Scripts\python.exe agent\scripts\validate_answers.py

# single case via CLI
agent\venv\Scripts\python.exe agent\main.py HHG-005 3523199 risk_score
```

`agent/scripts/trickle_benchmark.py` re-runs only degraded/missing cases through LLM rate-limit windows.

### Tests

```bash
agent\venv\Scripts\python.exe -m pytest agent/tests -q   # 56 tests
```

- `test_policy.py` (30) — every policy rule R1–R10, approval routes, threshold cases, action ordering
- `test_flow.py` (12) — end-to-end investigation on a mocked TigerGraph
- `test_answer_writer.py` (14) — answer schema, SAR consistency, verdict/zeroing rules

## Design Decisions Worth Knowing

- **The LLM never picks actions.** It assesses and explains; the policy engine routes. Verdict overrides (e.g. customer denial forces probability ≥ 0.70) are deterministic code, not prompt pressure.
- **Honest calibration over confident guessing.** Probabilities spread across 0.08–0.81; two cases are deliberately `uncertain` with escalations, because R8 says unresolved evidence escalates rather than blocks.
- **Every fact carries provenance.** Evidence items cite `source` (graph / document / customer), `ref` (query name), and `entity_ids` — every ID in the answers exists in the dataset.
- **Free-tier friendly.** Primary LLM runs on OpenRouter's free tier with Groq as fallback; the Jev classification layer has a deterministic heuristic fallback and a circuit breaker, so the agent degrades instead of dying.

## Team

Built for the TigerGraph Hacker House Goa 2026 challenge.
