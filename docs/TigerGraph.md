# TigerGraph — Setup, Queries, MCP, GraphRAG

> [[Home]] · [[Data-Model]] · [[Architecture]] · [[Agent-Workflow]]

## Status Overview

| Area | Status |
|---|---|
| Savanna connection (pyTigerGraph) | **Implemented** (`agent/graph.py`, `agent/tg_mcp.py`) |
| TigerGraph MCP client with fallback | **Implemented** (`agent/tg_mcp.py`) |
| Investigation queries (installed) | **Implemented** (`tigergraph/queries/investigation_queries.gsql`) |
| GraphRAG corpus + vector index | **Implemented** (`agent/rag.py`, `agent/scripts/build_vector_index.py`) |
| Case write-back (InvestigationCase) | **Implemented** (`agent/memory.py`) |
| Graph algorithms (CC, PageRank, ...) | Planned — not yet integrated |

## Setup

### TigerGraph Savanna
1. Sign up at https://savanna.tgcloud.io
2. Create workspace → "Explore with Your Own Data"
3. **Enable auto-stop and auto-start** (challenge requirement)
4. Connection config lives in `agent/.env`: `TG_HOST`, `TG_GRAPH` (FraudGraph), `TG_SECRET`

### Connection (pyTigerGraph)
```python
import pyTigerGraph as tg
conn = tg.TigerGraphConnection(
    host=os.environ["TG_HOST"],
    graphname=os.environ["TG_GRAPH"],
    gsqlSecret=os.environ["TG_SECRET"],
    tgCloud=True,
)
conn.getToken(conn.createSecret())
```

## TigerGraph MCP Client (IMPLEMENTED, with fallback)

`agent/tg_mcp.py` provides `TigerGraphMCP`:

- Spawns the installed `tigergraph-mcp` server (1.0.3) as a **stdio subprocess** using the `mcp` SDK client (`stdio_client` + `ClientSession`), configured from `TG_*` env vars (`TG_GRAPHNAME` is derived from `TG_GRAPH`, `TG_TGCLOUD=true`).
- A persistent background event-loop thread keeps the MCP session alive across synchronous calls (LangGraph nodes are sync).
- `run_installed_query(name, params)` / `run_interpreted_query(gsql, params)` prefer the MCP tools `tigergraph__run_installed_query` / `tigergraph__run_query` and **fall back to a direct pyTigerGraph connection** (same construction as `agent/graph.py`) on any failure.
- After the first MCP failure, `use_mcp` flips to `False` permanently and all calls route through pyTigerGraph — the agent degrades gracefully when the subprocess or Savanna is unavailable.
- `list_tools()` returns the served tool names; `close()` shuts the session down.
- Module import never raises and never blocks (guarded imports, lazy connection).
- Self-check: `python -m tg_mcp` (from `agent/`) prints the handshake result and tool count.

Observed: MCP handshake + `list_tools` work (69 tools); installed/interpreted queries are served via fallback when the MCP data path is slow or unparseable.

## Investigation Queries

`tigergraph/queries/investigation_queries.gsql` — all INTERPRET-compatible (STRING/DATETIME/INT params, no VERTEX params). Installed queries are executed via `runInstalledQuery`; the same bodies run interpreted during development.

| Query | Params | Purpose |
|---|---|---|
| `get_customer_cards` | `cust_id` | Cards owned by a customer |
| `get_card_transactions` | `c_id` | All transactions of a card |
| `get_transaction_device` | `t_id` | Device profile of a transaction |
| `get_shared_device_cards` | `t_id` | Cards sharing the flagged txn's device (coordination signal) |
| `get_card_recent_window` | `c_id, anchor_ts, hours` | Card txns in `[anchor − hours, anchor]` for velocity/card-testing detection |
| `get_region_activity` | `region_id, anchor_ts, hours` | Txns billed in a region in the window |
| `get_card_neighbor_degree` | `c_id` | Degree counts: total txns + connected devices |

> Window queries anchor on the flagged txn's `ts` rather than `now()`: the dataset timestamps are synthetic (2026-01-01 + `TransactionDT` seconds), so a `now()`-relative window would be empty.

## GraphRAG — Vector Search (IMPLEMENTED)

`agent/rag.py`:

- **Corpus**: 7 pattern typology docs (5 known patterns + `undocumented` + `none`), fraud-policy chunks parsed at runtime from `Initial-docs/dataset/README (1).md` (`policy:R1`…`policy:R10` plus section chunks), and `ClosedCase.analyst_notes` fetched from the graph when available.
- **Embeddings**: deterministic local hash bag-of-words (256-dim TF, L2-normalized, pure Python stdlib). No external embeddings API — Groq has none.
- **Index build** (`build_vector_index(conn)`, CLI `agent/scripts/build_vector_index.py`):
  1. Primary path: ensure a `DocChunk` vertex type on the graph (local schema-change job), add a 256-dim COSINE `embedding` vector attribute, install a `rag_vector_search` helper query (`vectorSearch()` is **not** supported in interpreted mode — it needs an installed query with a `LIST<FLOAT>` param), upsert all chunks, probe search.
  2. Fallback: in-memory corpus + Python cosine scoring (small corpus; always works offline).
- **Retrieval** (`retrieve_context(conn, queries, top_k=3)`) returns `[{"source": "document", "ref": "pattern:card_testing" | "policy:R5" | "closed_case:CC-0141", "text", "score"}]`, using the TigerGraph kNN query when the index is live in-process, otherwise local cosine.

## Case Write-Back (IMPLEMENTED)

`agent/memory.py`:

- `find_similar_cases(conn, txn, pattern_hint, limit=3)` scores `Initial-docs/dataset/closed_cases_history.csv` (loaded once, module cache): pattern match 0.5, amount log-proximity 0.2, card/txn identity overlap 0.3.
- `persist_investigation_case(conn, state)` upserts an `InvestigationCase` vertex (`upsertVertex`) with verdict, fraud probability, pattern, exposure, summary, timestamp and wires `INV_INVOLVES` / `INV_ON_CARD` / `INV_CONNECTED_TO` edges to flagged txn and card ids, plus `SIMILAR_TO` edges to prior `ClosedCase` ids that exist. Returns the graph case id, `""` + warning on failure.

## Graph Algorithms (Candidates, Not Integrated)

| Algorithm | Use Case |
|---|---|
| **Connected Components** | Find fraud rings — groups of cards/customers sharing devices |
| **PageRank** | Identify central nodes in suspicious networks |
| **Community Detection** | Identify clusters of coordinated activity |

## Cross-References

- Schema details: [[Data-Model]]
- How agent uses these: [[Agent-Workflow]]
- MCP in architecture: [[Architecture]]
- Jev decision layer: [[Jev]]
