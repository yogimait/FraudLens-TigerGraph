# FraudLens: Ops Intelligence

An agentic fraud investigation system built for the **TigerGraph Agentic Fraud Investigation Hackathon** (HHGOA / IEEE-CIS Fraud dataset).

The 20 graded answer files live in `cases/` (`HHG-001.json` … `HHG-020.json`), one per benchmark case in `Initial-docs/dataset/case_pack.csv`.

## What It Does

A LangGraph agent (12 nodes) investigates flagged card transactions end to end:

1. **Trigger** — risk-score signal, customer report, or analyst request.
2. **Investigate** — TigerGraph MCP (69 tools, pyTigerGraph fallback) runs 7 installed GSQL queries: card history, customer cards, device profiles, shared devices, connected cases, transaction window.
3. **Ground** — GraphRAG: policy + fraud-pattern typology documents retrieved from TigerVector into the LLM prompt.
4. **Remember** — similar closed cases retrieved from `closed_cases_history.csv` (case memory), new investigation written back to the graph.
5. **Assess** — LLM (openai/gpt-oss-120b via Groq; OpenRouter free-tier fallback) produces a calibrated `fraud_probability` — the bank's risk score is treated as a prior, never the answer.
6. **Decide** — policy engine (`agent/policy.py`) implements fraud-policy rules R1–R10 as deterministic code with exact approval routes (`auto` / `L1` / `L2`). The LLM never picks actions.
7. **Explain** — analyst summary, SAR narrative when policy requires it, evidence provenance (`source`/`ref`/`entity_ids`), stop reason.
8. **Record** — answer JSON validated against the dataset answer format; case persisted to graph + MongoDB.

## Architecture

- `agent/` — Python FastAPI (`api.py`) + LangGraph state machine (`graph.py`), TigerGraph MCP client (`tg_mcp.py`), GraphRAG (`rag.py`), case memory (`memory.py`), policy engine (`policy.py`), LLM layer (`llm.py`), answer writer (`answer_writer.py`).
- `backend/` — NestJS + MongoDB: case store, trigger/approve/reject endpoints, stats.
- `frontend/` — Next.js analyst dashboard: KPIs, investigation view, evidence citations, d3-force graph, approvals queue.
- `tigergraph/` — graph schema (`schema.gsql`) and investigation queries (`queries/investigation_queries.gsql`).
- `docs/` — full documentation vault (open in Obsidian): [[Architecture]], [[Agent-Workflow]], [[Policy-Engine]], [[TigerGraph]], [[Data-Model]], [[Decisions]].

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