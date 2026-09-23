# Project Audit — 2026-09-23

> Full audit of the working system against the challenge problem statement ([[PRD]], `Initial-docs/TigerGraph Agentic Fraud Investigation HHGOA.md`) and the dataset README answer format.
> Purpose: find every gap between what the PS requires and what the code does, with proof (file:line), then drive fixes. See [[Home]] for index.

## Verdict Summary

| PS Required Component | Status | Evidence |
|---|---|---|
| 1. TigerGraph (graph + vector storage) | ⚠️ Partial — graph used, vector store unused | `agent/graph.py:14-23` pyTigerGraph; zero vector queries anywhere |
| 2. GSQL + graph algorithms | ⚠️ Partial — traversal yes, algorithms none | 3 installed queries in `tigergraph/queries/investigation_queries.gsql`; no PageRank/community/degree |
| 3. TigerGraph MCP | ❌ Not used (required component) | `tigergraph-mcp==1.0.3` installed in venv but zero imports; `pyproject.toml:12` declares it |
| 4. GraphRAG | ❌ Missing | No vector search, no policy/typology documents in any LLM prompt (`agent/llm.py:31-74`, `107-139`) |
| 5. UI | ✅ Present | `frontend/` dashboard, case view, approvals, graph explorer |

Agent flow: **linear 7-node graph** (`agent/graph.py:184-205`) — no uncertainty loop, no evidence requests, no case memory retrieval, no write-back to graph.

Answer files: **non-compliant with the required schema** (details below). This is the highest-risk item: investigation accuracy (25%) + next best action (25%) are scored on these files.

## Findings

### F1. Policy engine does not implement R1–R10 (Critical)

`agent/policy.py` implements a fabricated rule set. Verified against `Initial-docs/dataset/README (1).md` §Fraud Policy:

| Code (policy.py) | Official rule | Problem |
|---|---|---|
| `NOTIFY_CUSTOMER` (:20) | — | Invalid action name (valid: `WARN_CUSTOMER`) |
| "R3" prob≥0.95 → BLOCK_CARD+REJECT_TRANSACTION+REQUIRE_L2 (:27-30) | R3 = customer confirms → CLOSE_NO_FRAUD | Wrong rule; `REJECT_TRANSACTION` invalid (valid: `DECLINE_TRANSACTION`); BLOCK_CARD route ignores ≤$2,500→L1 split |
| "R4" 0.70≤p<0.95 → REQUIRE_L1 (:33-34) | R4 = no reply in 24h → MONITOR_CARD+DECLINE_TRANSACTION | Fabricated |
| "R5" BLOCK_DEVICE+FORCE_PASSWORD_RESET (:37-39) | R5 = card testing → DECLINE_TRANSACTION+STEP_UP_AUTH (+BLOCK_CARD if >$100 cleared) | Both action names invalid |
| "R6/R7" SAR check (:42-49) | R6 = shared origin; R7 = disputed-but-legitimate | Neither implemented; `shared_attributes` hard-coded False (:44); misses "strongly suspected" leg (uncertain never reaches SAR) |
| "R8" uncertain → REQUIRE_L1_APPROVAL (:52-53) | R8 = uncertain AND exposure>$500 or conflict → ESCALATE_TO_ANALYST (auto) | Wrong action + threshold + route; **unreachable** for prob<0.30 due to early return :18-24 |
| "R10" REFUND_CUSTOMER (:56-57) | R10 = BLOCK_ALL_CARDS guard | Wrong rule; `REFUND_CUSTOMER` invalid |

Also missing entirely: `CREATE_CASE` triggers (fp≥0.30 / evidence requested / customer dispute — §3a), `route` field (`auto|L1|L2`) on actions, `BLOCK_ALL_CARDS`, `CLOSE_NO_FRAUD`, rule-number citations in reasons (§7), exposure limited to the identified fraud episode (§4 — current code sums flagged txn + up to 9 arbitrary recent card txns, `graph.py:59-60,116-121`).

### F2. Answer files violate the required schema (Critical)

Checked all 25 files in `cases/` against README "Answer Format". Missing fields (0/25 contain): `case_id` top-level, `evidence_requests`, `stop_reason`, `tool_calls`, `tokens`, `latency_s`, `case.status`, `case.evidence`, `similar_prior_cases`, `connected_card_ids`, `connected_device_profiles`, `written_to_graph`, `graph_case_id`, `sar.reason`, `sar.total_amount_usd`, `sar.activity_dates`, `next_best_actions.route`, `what_changed`. All `"initial": []` — the initial recommendation (required before evidence) is never recorded. Pattern strings are invalid (`"Card Testing"` vs required enum `card_testing`); several files are stale artifacts of older code (`HHG-001/002`), stray non-benchmark files pollute `cases/` (`CASE_HHG-020.json`, `HHG-TEST-*`, `HHG-NEW-*`). README requires exactly 20 files `HHG-001..020.json`.

### F3. TigerGraph MCP not used (Required component)

`tigergraph-mcp==1.0.3` + `mcp==2.2.0` are installed (`agent/venv` pip list) but the agent talks to Savanna via pyTigerGraph directly (`agent/graph.py:14-23`). Documented as a deliberate deviation in [[TigerGraph]] ("reduce infrastructure overhead") — but the PS lists MCP as **required**. Decision: wire the real MCP client in as the graph tool layer with a pyTigerGraph fallback, so the agent demonstrably uses TigerGraph MCP.

### F4. GraphRAG absent (Required component)

No vector index usage, no embeddings, no documents (fraud policy, typologies, closed-case analyst notes) reach the LLM. Prompts contain only raw graph rows. Required: GraphRAG grounding via TigerGraph vector store.

### F5. Case memory not implemented

`ClosedCase`/`InvestigationCase` vertices and `SIMILAR_TO` edges exist in schema (`tigergraph/schema.gsql:50-94`) but nothing reads/writes them; `closed_cases_history.csv` is never used for retrieval; `similar_prior_cases` is empty in 25/25 answer files; no `persist_case` node.

### F6. Jev is fake (dep misuse)

`agent/jev_client.py:14-58` is hardcoded Python if/elif with fabricated confidences; `TypeSafeClient` instantiated at :12 and never used. The only real Jev call is the smoke test `scripts/verify_jev.py`. `typesafe-sdk==0.7.1` installed. Per [[Jev]]: Jev should make fast structured decisions (pattern classification Choice, sufficiency Noul, coordination Noul) as *inputs*, never verdicts.

### F7. No uncertainty loop / stopping conditions

`docs/Agent-Workflow.md:9-27` documents an 11-node flow with `evidence_sufficient` conditional edge — code has none (`agent/graph.py:196-203`, all linear). Policy §6 stopping conditions (fp≥0.85/≤0.15 with 2+ evidence) exist nowhere in code. `evidence_requests`, `assumed_responses` state fields are dead.

### F8. Backend drops evidence; frontend mocks (High)

- Backend persists only `metadata.evidence_count`; the agent's evidence list (with `source/ref/entity_ids`) is discarded (`backend/src/cases/cases.service.ts:89`). Evidence tab renders only the summary prose.
- Approval level hardcoded `L1` in both frontend callers and never validated by backend → L2 cases approvable at L1.
- No `uncertain` count in `/cases/stats` (frontend donut reads `stats.uncertain`, always 0).
- Mock data: dashboard "System Performance" card, KPI trends, Memory page ("GraphRAG" label over substring filter with fabricated relevance), Settings page fully cosmetic, Reports dead buttons.
- No SSE (deferred per [[Implementation-Tasks]] T4.5/T5.3).

### F9. Graph visualization unreadable (Demo)

`frontend/components/EvidenceGraph.tsx`: hand-rolled grid layout (cards 600px apart, txns in rows of 4 at fixed offsets, :109-158), `isHighRisk = amount > 1000` hardcoded, no force layout, no semantic grouping — produces the confusing screenshots from `/graph` and the case Graph View tab. Redesign: Obsidian-style force-directed graph (physics layout, colored node types, hover highlight, neighbor focus, labels on demand).

### F10. Security / hygiene

- Hard-coded TG secret `agent/scripts/ingest_data.py:14`; hard-coded JEV API key `agent/scripts/verify_jev.py:4`.
- CORS `allow_origins=["*"]` with `allow_credentials=True` (`agent/api.py:11-17`) — invalid combination.
- Dead code: `conn` in jev_client (:12), ~17 never-written state fields (`agent/state.py`), `get_customer_cards` installed query never called, MUI/Emotion deps unused in frontend.
- Card-ID derivation in chunked ingest is per-chunk, not global baseline_k (`agent/scripts/ingest_data.py:65-71`) — inconsistent card IDs vs validation script.

## Dependency Check (user request 3)

| Required dep | Installed | Actually used | Proof |
|---|---|---|---|
| TigerGraph MCP | tigergraph-mcp 1.0.3 + mcp 2.2.0 | ❌ never imported | grep `import mcp|tigergraph_mcp` → 0 hits in agent code |
| pyTigerGraph | 2.0.4 | ✅ direct REST/GSQL | `agent/graph.py:14` |
| typesafe-sdk (Jev) | 0.7.1 | ⚠️ imported, unused client | `agent/jev_client.py:2,12` |
| langgraph | 1.2.12 | ✅ state machine | `agent/graph.py:6` |
| groq (LLM) | 1.7.0 | ✅ GPT-OSS-120B | `agent/.env` GROQ_MODEL |
| @xyflow/react (frontend graph) | 12.11.6 | ✅ | `frontend/components/EvidenceGraph.tsx` |
| @mui/material, @emotion | 9.4.0 | ❌ unused | zero imports |
| recharts, framer-motion, lucide-react | ✅ | ✅ used | dashboard pages |

## Fix Plan (this audit drives it)

1. **CORE** — rewrite `agent/policy.py` to true R1–R10 with `route` field + rule citations + case/SAR triggers; add evidence-request loop + simulated responses + stopping conditions; enforce answer-file schema (all required fields, initial before evidence, valid pattern enum, calibration); fix exposure to fraud episode only; track tool_calls/tokens/latency; clean `cases/` to exactly 20 files.
2. **TG** — TigerGraph MCP client (with pyTigerGraph fallback); GraphRAG vector index (policy text, pattern typologies, closed-case notes) + retrieval into LLM prompts; case memory (retrieve `similar_prior_cases` from `closed_cases_history.csv` + graph SIMILAR_TO; `persist_investigation_case` write-back); graph algorithms (degree/shared-device counts via GSQL).
3. **APP** — backend stores `evidence` list, adds `uncertain` stats count, validates approval `level` against case route; frontend renders evidence citations (source/ref/entity_ids), route badges, uncertain styling, real data replaces mocks.
4. **VIZ** — Obsidian-style force-directed graph rewrite of `EvidenceGraph.tsx`.
5. Re-run/validate the 20 benchmark answers; docs sync in same tasks.
---

## Addendum � Live Fixes Applied (2026-09-23 evening)

All F1�F9 fixes implemented and verified live:

- **F1 Policy**: gent/policy.py now implements R1�R10 + �3a with exact routes and rule citations; 24 pytest cases.
- **F2 Answers**: gent/answer_writer.py + gent/scripts/validate_answers.py; 20/20 files validate; strays moved to cases/archive/.
- **F3 MCP**: gent/tg_mcp.py � TigerGraph MCP server spawned via stdio (69 tools live), markdown-fenced JSON responses parsed, success:false triggers pyTigerGraph fallback, GSQL param binding inlined, single-agent process.
- **F4 GraphRAG**: gent/rag.py � DocChunk vector index (28 chunks live: pattern typologies + policy chunks), retrieval feeds LLM prompts; Groq has no embeddings API ? deterministic local TF-hash embeddings (documented in [[TigerGraph]]).
- **F5 Memory**: gent/memory.py � similar_prior_cases from closed_cases_history.csv + persist_investigation_case write-back (written_to_graph: true on live runs).
- **F6 Jev**: real typesafe-sdk calls with circuit breaker; TypeSafe account returned 402 no credits ? heuristic engine fallback labeled engine: heuristic.
- **F7 Loop**: ssess ? request_evidence ? simulate_response ? reassess with policy �6 stopping; llm_ok degraded-guard propagates through LangGraph state (was silently dropped before being added to [[Agent-Workflow]] state schema).
- **F8 UI**: evidence citations, route badges, uncertain styling, real stats � see [[UI]].
- **F9 Viz**: Obsidian-style d3-force rewrite of EvidenceGraph.tsx.

New findings during live verification:

- GSQL reverse-edge traversal cannot be chained multi-hop in this Savanna version ("mixed usage of v1 and v2 syntax") � get_shared_device_cards implemented single-hop + Python composition.
- TigerGraph MCP install_query only CREATEs; explicit INSTALL QUERY required.
- Graph ingest gaps confirmed live: 0 FROM_DEVICE/BILLED_IN edges, ClosedCase 40/5,565, graph card ids are card1-based (17108_0) vs case_pack C{n}-K{n} style � resolved by edge-derived card lookup in graph.py.
- Groq free tier TPD (200,000 tokens/day) cannot sustain repeated 20-case runs; 
un_benchmark.py now aborts on degraded LLM output (metadata.llm_ok=false) and --case supports subsets; scripts/trickle_benchmark.py retries through quota windows. Final benchmark regeneration must complete after quota reset.

## Addendum 2 — Submission Blockers Cleared (2026-09-23 night)

- **.gitignore unblocked `cases/` and `tigergraph/`** — both were excluded, so the 20 answer files and the GSQL schema/queries (core deliverables) would never have reached the public repo. `Initial-docs/` stays ignored.
- **Groq dual-key rotation** in `agent/llm.py` `_call`: iterates `GROQ_API_KEY` then `GROQ_API_KEY_2`, retires a key in-process on rate-limit signatures (429/TPD/TPM), keeps per-key client cache. Key 2 (fresh) primary, key 1 (refills next day) fallback.
- **Zombie process cleanup**: two api.py, two tigergraph_mcp, two trickle runners were alive simultaneously (one set under system Python 3.12) — double-burning Groq quota via duplicate POSTs. All killed; single venv api.py + single trickle relaunched.
- **Secret removal**: `agent/scripts/verify_jev.py` hardcoded JEV API key (already committed) replaced with `os.environ.get("JEV_API_KEY")`.
- **Stale case purge**: 003–019 were pre-calibration-fix outputs parked at uncertain/0.5 with `llm_ok: true` — invisible to the trickle retry logic (which only retries `llm_ok: false`). All 19 (plus 002/020 junk and cases/archive) moved to `%TEMP%\cases_stale_20260923`; regeneration restarted on key 2. First post-fix outputs verified calibrated (HHG-001 legitimate/0.10, HHG-002 fraud/0.78/card_not_present_fraud).
- **LLM switched to OpenRouter** (Groq org pool exhausted both keys): `agent/llm.py` now talks to `https://openrouter.ai/api/v1` via the `openai` SDK with `OPENROUTER_API_KEY`/`OPENROUTER_MODEL` env; hardened `_call` against free-tier quirks — 3-attempt retry on empty completion content, response_format fallback, rate-limit key retirement, and `_call_json` strict-JSON retry on malformed model output. Free-tier limits (per OpenRouter docs): 20 req/min, 1000 req/day for accounts with ≥$10 lifetime credits.
- **Deterministic verdict-band alignment** in `_validate_assessment`: verdict derives from fraud_probability (≥0.70 fraud, ≤0.30 legitimate, else uncertain); legitimate zeroes affected ids. `graph.py:_absorb_assessment` retains the policy override: customer `no_reply` downgrades fraud→uncertain below 0.85 (R4 posture), `denied` forces ≥0.70/fraud, `confirmed` forces legitimate.
- **MongoDB crashed at 01:07** (WiredTiger tcmalloc crash in service log) → NestJS backend died with it (ECONNREFUSED 27017). Restarted service elevated (UAC), backend reconnected in watch mode. Data intact.
- **Final result 2026-09-24 01:30**: trickle "20/20 complete"; 13 legitimate / 5 fraud / 2 uncertain (HHG-013 0.58 ambiguous, HHG-019 0.78 fraud-lean post-no_reply), SARs on 015/019/020; `validate_answers.py` 20/20 files, 0 violations. README rewritten with end-to-end run + benchmark reproduction; `agent/requirements.txt` created.
