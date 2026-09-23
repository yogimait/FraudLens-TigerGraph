# Architectural Decisions

> [[Home]] · [[Architecture]] · [[Questions]]

## D1. Python for agent runtime, TypeScript for application backend

**Decision**: Agent runtime in Python; application backend in NestJS (TypeScript).

**Rationale**: TigerGraph MCP is Python-native. LangGraph has strongest tooling in Python. Keeping agent in Python avoids cross-runtime MCP friction. NestJS stays as application API because the user wants to learn it and it handles REST/SSE/MongoDB well.

**Alternative considered**: Everything in TypeScript (LangGraph.js). Rejected because TigerGraph MCP integration would require a Python sidecar anyway, adding complexity without benefit.

---

## D2. MongoDB Atlas over PostgreSQL/Supabase

**Decision**: MongoDB Atlas for application state.

**Rationale**: Investigation runs, approval records, and agent outputs are naturally document-shaped. MongoDB Atlas free tier is sufficient. NestJS has first-class Mongoose integration. User preference.

**Alternative considered**: PostgreSQL via Supabase. Valid but adds another paradigm; MongoDB is simpler for this use case.

---

## D3. No Redis

**Decision**: No caching layer initially.

**Rationale**: No demonstrated caching need. Adding Redis increases deployment complexity for zero immediate benefit. Can add later if TG queries or LLM calls need caching.

---

## D4. No separate vector DB

**Decision**: Use TigerGraph's vector capabilities (TigerVector) for GraphRAG.

**Rationale**: Challenge explicitly asks to use TigerGraph for graph AND vector storage/retrieval. Adding Pinecone/Qdrant would contradict the challenge intent and add infrastructure.

---

## D5. V1–V339 as JSON blob, not individual attributes

**Decision**: Store Vesta's 339 engineered features as a single JSON blob on Transaction vertices.

**Rationale**: Columns are unnamed. Individual attributes would bloat schema. Agent can access specific V-columns from the blob when needed as signals. The investigation value is in entity relationships (graph), not in 339 anonymous numeric features.

---

## D6. Groq GPT-OSS-120B as primary LLM

**Decision**: Use Groq GPT-OSS-120B for all generative LLM tasks.

**Rationale**: 131K context, tool use, structured outputs, fast (~500 tok/s), cheap. Sufficient reasoning capability for evidence synthesis and narrative generation.

**Rate Limit Strategy**: Do NOT hardcode a fixed delay. Use sequential/low-concurrency processing, adaptive rate limiting, exponential backoff on HTTP 429, respect `Retry-After` headers, cache deterministic outputs, and avoid unnecessary LLM calls. Process the 20 benchmark cases in controlled batches.

---

## D7. Jev as supplementary, not primary

**Decision**: Jev provides fast classification signals; LLM + policy engine make final decisions.

**Rationale**: Jev is designed for structured decisions alongside generative models. Treating Jev as the sole fraud classifier would bypass graph evidence and policy rules. Using it as a signal alongside other evidence is architecturally cleaner and more defensible.

**Integration Strategy**: Use the current supported official Python package (`jev` or `jevclient`). Verify key and API before making it a hard dependency. If Jev is unavailable, agent MUST degrade gracefully to GPT-OSS-120B + deterministic rules. Jev is NOT the source of truth for fraud decisions.

---

## D8. Deterministic policy engine in code

**Decision**: All fraud policy rules (R1–R10) implemented as deterministic code, not LLM prompts.

**Rationale**: Policy rules have exact thresholds ($500, $1,000, $2,500, 0.70 probability). These must be reliably enforced, not left to LLM interpretation. Judges can inspect the policy logic.

---

## D9. Evidence simulation strategy

**Decision**: Use policy-driven evidence simulation rather than a single universal response.

**Strategy**:
- **customer_report cases**: Treat report as evidence customer disputes activity. Simulate denial only when workflow requires it. Record in `evidence_requests.assumed_response`.
- **risk_score cases**: Do NOT automatically assume fraud or legitimacy. If graph evidence is weak/conflicting and verification appropriate, use conservative confirmation. If evidence strongly supports fraud, simulate denial. If evidence strongly supports legitimacy, simulate confirmation.

**Rationale**: The dataset README says to simulate responses and record assumptions. Explicitly tracking the simulated response and being consistent ensures the final case record is transparent.

---

## D10. FastAPI for Python agent service

**Decision**: Use FastAPI for the Python agent's HTTP interface.

**Rationale**: Lightweight, async, good for SSE streaming, widely used with LangGraph. Minimal overhead.

**Alternative considered**: Flask. Rejected — async support is weaker.

---

## D11. Case memory as graph vertices

**Decision**: Store completed investigation cases as `InvestigationCase` vertices in TigerGraph, with edges to transactions and cards.

**Rationale**: Challenge explicitly requires writing cases to graph. Later investigations should find them via graph traversal. This IS the case memory.

---

## D12. Answer file format exactly as specified

**Decision**: Match the JSON schema from the README exactly. No extra fields, no missing fields.

**Rationale**: "Submit one JSON file per case... Missing fields score zero for that part."

---

## D13. TigerGraph Savanna & TigerVector

**Decision**: Use TigerGraph Savanna as primary deployment. Target 4.2+ for TigerVector (hybrid graph + vector retrieval).

**Rationale**: Vector capabilities are required for closed-case/narrative GraphRAG. If the workspace doesn't have 4.2+, try to upgrade/recreate before falling back to Community Edition. Graph investigation must remain fully functional even without vector search.

---

## D14. Deterministic card_id derivation

**Decision**: Do NOT blindly assume `customer_id + "-K" + card_index`. Create a deterministic validation step before finalizing graph schema.

**Rationale**: Need a stable 1:1 mapping between `transactions.csv` (`customer_id`, `card1`) and `case_pack.csv` / `closed_cases_history.csv` (`card_id`). The mapping must be validated against all provided card IDs. Never create fake card IDs. Stop and report mismatch if it cannot be exactly reconciled.

---

## D15. Number of evidence requests

**Decision**: Default maximum: 1 evidence request per case.

**Rationale**: Benchmark rewards efficient investigation. Repeated requests create unnecessary loops. Most cases are resolvable via graph + history + policy. Agent should stop once evidence is sufficient according to policy. Architecture should technically support more, but benchmark uses 0 or 1.

---

## D16. Deployment Strategy

**Decision**: Primary development and fallback demo target is `localhost`.

**Rationale**: Full system must run locally. Cloud deployment (Next.js -> NestJS -> Python -> TG Savanna) can be added for the final demo if stable and time permits, but investigation correctness must never be sacrificed for deployment polish.

---

## D17. Graph visualization library

**Decision**: Use lightweight SVG/Mermaid first for UI graph visualization.

**Rationale**: Prioritize investigation readability over visual complexity. Avoid heavy interactive libraries (`react-force-graph-2d`) unless the basic UI is already complete and time permits.

---

## D18. LangSmith setup

**Decision**: LangSmith is optional but strongly preferred for development/debugging.

**Rationale**: Do not block the project on LangSmith. If API key exists, trace LangGraph runs, tools, and LLM calls. If not, implement local structured logging. Agent must remain fully functional without LangSmith.

---

## D19. Optional monitoring of exam period

**Decision**: SKIP this for primary implementation.

**Rationale**: Focus 100% on the 20 benchmark cases (50% of score). Treat continuous monitoring as an innovation extension only if everything else is fully stable.

---

## D20. Authentication

**Decision**: NO authentication for hackathon MVP.

**Rationale**: Dashboard can be open-access. Human approval in fraud workflow is simulated, not a requirement for an actual RBAC/auth system. Saves critical development time.

---

## D21. Regulatory documents / external vector corpus

**Decision**: Do NOT make external regulatory-document ingestion part of the critical path.

**Rationale**: Priority order: 1) Provided policy, 2) Provided dataset, 3) Closed-case history, 4) Fraud pattern descriptions. External documents can only be added if time permits, must come from authoritative sources, must be clearly identified, and cannot be used to infer hidden ground-truth labels for benchmark cases.

## D22. Local MongoDB over Atlas (Network Bypass)

**Decision**: Use a local MongoDB instance instead of MongoDB Atlas for MVP application state.

**Rationale**: The provided Atlas URI `mongodb+srv://...` experienced DNS resolution / firewall blocks within this environment, causing NestJS to crash on startup. Switching to `localhost:27017` allowed seamless end-to-end flow testing without blocking Phase 3 execution.

---

## D23. Next.js UI Dependencies

**Decision**: Rely heavily on `Tailwind`, `shadcn/ui`, `framer-motion`, and `lucide-react` for the UI rather than initializing a raw Next.js app.

**Rationale**: The user explicitly required a modern, premium design system. Leveraging `shadcn` components gives immediate access to professional styling. `lazy loading` and lightweight graph visualizations are prioritized to prevent dashboard lag over complex interactive 2D graph libraries.

## D24. TigerGraph access via MCP server with pyTigerGraph fallback

**Decision**: Route TigerGraph calls through the installed `tigergraph-mcp` server (spawned as a stdio subprocess via the `mcp` SDK, `agent/tg_mcp.py`), but treat it as an accelerator, not a dependency: every call falls back to a direct pyTigerGraph connection on any MCP failure, and the first failure permanently flips `use_mcp` off for the process.

**Rationale**: The MCP server satisfies the challenge's integration goal and gives a uniform tool surface, but the stdio data path proved slow/flaky for query execution in practice (handshake and `list_tools` are reliable; tool calls occasionally time out or return unparseable payloads). pyTigerGraph is the proven path. Guarded fallback keeps the agent working offline (CI) and under Savanna auto-stop, at the cost of one wasted call when MCP dies.

## D25. Local hash-based embeddings + DocChunk vertex for GraphRAG

**Decision**: Embed the RAG corpus (7 pattern docs, policy rule chunks, closed-case analyst notes) with a deterministic pure-Python hash bag-of-words vector (256-dim TF, L2-normalized) — no external embeddings API. Primary indexing path stores chunks in a `DocChunk` vertex type (created at runtime via local schema-change job) with a 256-dim COSINE `embedding` vector attribute and an installed `rag_vector_search` helper query; retrieval falls back to in-memory cosine scoring over the cached corpus.

**Rationale**: Groq has no embeddings API and no new dependencies are allowed; a hash TF vector is deterministic, dependency-free, and adequate for ranking a ~30-chunk corpus. TigerGraph vector attributes cannot be searched in interpreted mode (`vectorSearch()` requires an installed query with a `LIST<FLOAT>` parameter), and schema changes on Savanna are version-sensitive — hence the guarded attempt + in-memory fallback, which always works offline.

## D26. Jev circuit breaker with engine labeling

**Decision**: `agent/jev_client.py` makes real `typesafe-sdk` calls (pattern Choice, sufficiency Noul, coordination Noul in one `system_one` request) but trips a process-wide circuit breaker after the first Jev failure, switching to the deterministic graph heuristics and marking every result `"engine": "jev" | "heuristic"`.

**Rationale**: The TypeSafe endpoint currently answers `402 no available credits`; without the breaker, every classification would pay a doomed API round-trip (plus retries) during benchmark runs. Explicit engine labeling keeps results honest — Jev confidence is a signal, never the verdict.

## D?. No paid Jev credits; self-hosted Laya is the optional revival path

**Decision**: Do not purchase TypeSafe Jev credits for the submission. The deterministic heuristic engine ships as the active decision layer. [Laya](https://huggingface.co/convaiinnovations/laya) (Apache-2.0, Jev-compatible HTTP server `laya-serve`, same `POST /v1/systemone` shape) may be self-hosted locally after the benchmark regeneration is secured — wired via a `JEV_BASE_URL` HTTP shim in [[Jev]], only if a side-by-side eval on our own case states beats the heuristics.

**Rationale**: The Jev account showed ~130M input tokens consumed (MCP tool sessions + repeated benchmark runs), so paid credits risk another burn. Laya costs $0 and is API-compatible, but its card documents near-chance zero-shot typed-decision accuracy outside its fine-tuned domains and a `noul` label-following defect — both of our Noul call types (sufficiency, coordination) are exposed. Evaluation before adoption is mandatory; the policy engine and verdicts never depend on the decision layer either way.

**Eval result (2026-09-24, `laya-typed-decisions` checkpoint, 4 real cases)**: 3/4 pattern choices matched the LLM's evidence-based pattern (correct on HHG-002 card_not_present_fraud, HHG-013/020 undocumented), but confidence 0.03–0.13 on 7 options (near-random calibration, needs per-domain temperature refit) and a false `undocumented` on HHG-004, a legitimate case. Not adopted; deterministic heuristics ship. Revisit only with a domain temperature refit.

## Cross-References

- Open questions: [[Questions]]
- Architecture: [[Architecture]]
