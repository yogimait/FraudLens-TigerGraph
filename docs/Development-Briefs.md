# Development Phase Briefs

> [[Home]] · [[Development-Plan]] · [[Implementation-Tasks]]

This document provides a high-level executive brief for each phase of the project's development. It is intended to guide the engineering mindset for each specific stage.

---

## Phase 0: Graph Foundation
**"If the data isn't right, the agent cannot be right."**

This phase is entirely about data integrity and graph construction. Before writing any agent logic, we must ensure that the dataset maps perfectly into TigerGraph. 

**Key Directives:**
1. **Validate Before Loading:** We must programmatically prove that our method of deriving `card_id` from `transactions.csv` perfectly reconstructs the IDs in `case_pack.csv` and `closed_cases_history.csv`. Never guess or invent IDs.
2. **Verify Environment:** Confirm TigerVector availability in the Savanna workspace. GraphRAG is important, but if vector search isn't available, the underlying graph structure must still be robust enough to support investigation.
3. **Establish the Schema:** The graph must accurately represent the relationships: Customers own Cards, Cards make Transactions, Transactions occur at Devices/Regions.

---

## Phase 1: Tooling & GraphRAG (TigerGraph MCP)
**"Give the agent eyes into the graph."**

In this phase, we wrap the TigerGraph database in an MCP (Model Context Protocol) server. This bridges the gap between the graph database and the LLM agent.

**Key Directives:**
1. **GSQL is King:** The heavy lifting of data traversal should be done in GSQL, not Python. Write efficient GSQL queries (`get_card_transactions`, `find_device_neighbors`) that return structured, pre-digested JSON.
2. **Context, Not Raw Data:** MCP tools should return summarized evidence, not millions of raw transaction rows.
3. **GraphRAG Setup:** Implement similarity search over closed cases and fraud policy texts so the agent can reference historical precedent.

---

## Phase 2: Agent Brain (LangGraph Core)
**"Build the state machine, not a chatbot."**

This phase constructs the Python backend that orchestrates the investigation. We are building a deterministic state machine (LangGraph) where an LLM (Groq) and a classifier (Jev) make isolated decisions.

**Key Directives:**
1. **Separation of Concerns:** The LLM does *not* query the graph directly; it receives evidence from the state and returns structured reasoning. Jev provides fast classification signals.
2. **Graceful Degradation:** If Jev is unavailable, the agent must fall back to the LLM. 
3. **Structured Outputs Only:** Every LLM call must use strict JSON schemas. 
4. **End-to-End Proof:** Prove that the agent can take one simple case, traverse the graph, synthesize evidence, apply policy, and output a perfectly formatted JSON file.

---

## Phase 3: Policy Enforcement & Simulation
**"Policy is code. Assumptions are documented."**

This phase makes the agent legally and procedurally compliant. The dataset policy rules (R1–R10) must be hardcoded.

**Key Directives:**
1. **Deterministic Rules:** The LLM does *not* decide if a SAR is filed or if a case needs L2 approval. Code decides this based on the LLM's evidence synthesis and the exposure amount.
2. **Evidence Simulation:** We must programmatically simulate customer/analyst responses. These simulations must be consistent (e.g., if it's a customer report trigger, they clearly dispute the charge) and explicitly logged as `assumed_response`.
3. **Stop Conditions:** The agent must know when to stop investigating to avoid infinite loops and token waste.

---

## Phase 4: Application Backend (NestJS)
**"Bridge the agent to the humans."**

This phase builds the standard web application layer that serves the frontend UI, manages the MongoDB state, and triggers the Python agent.

**Key Directives:**
1. **Keep it Standard:** Use NestJS best practices. REST for CRUD operations, Server-Sent Events (SSE) for streaming the agent's thought process to the UI.
2. **No Over-engineering:** Authentication is not required for this MVP. Do not add Redis unless caching becomes a proven bottleneck.
3. **Asynchronous Execution:** The Python agent might take 10-30 seconds to investigate. The NestJS backend must handle this asynchronously.

---

## Phase 5: Analyst Dashboard (Next.js)
**"Make the invisible investigation visible."**

This phase builds the frontend UI where human analysts will observe the agent, review evidence, and approve L1/L2 recommendations.

**Key Directives:**
1. **Investigation Readability:** Prioritize a clean, three-panel layout showing the timeline, the current evidence, and the recommended actions.
2. **Lightweight Vis:** Use simple SVG or Mermaid charts for graph visualization first. Don't bog down the browser with massive interactive physics graphs unless absolutely necessary.
3. **Show the "Why":** The UI must clearly display the difference between the *initial* actions and the *final* actions, and explain why the agent changed its mind.

---

## Phase 6: The Benchmark Run
**"The 50% score."**

This is the most critical phase of the project. We run the agent against all 20 provided benchmark cases to generate the final answer files.

**Key Directives:**
1. **Rate Limit Respect:** Do not blast Groq with all 20 cases concurrently. Run them sequentially or in small batches with retry logic.
2. **Strict Schema Adherence:** Every output file must perfectly match the required JSON schema. Missing fields score zero.
3. **No Hallucinations:** Every `entity_id` in the output MUST exist in the provided dataset. Zero tolerance for invented IDs.
4. **Calibrate:** Ensure the `fraud_probability` reflects a balanced assessment, not just 0% or 100%.

---

## Phase 7: Polish & Submission
**"Tell the story."**

The final stretch. Packaging the results for the judges.

**Key Directives:**
1. **Local Fallback:** Ensure the entire stack can spin up on `localhost` via a simple script or `docker-compose`. 
2. **The Demo:** Record a concise 3-5 minute video focusing on the agent's reasoning process and policy compliance, not just the UI.
3. **Submission Check:** Verify all 20 JSON files are in the `cases/` folder, the codebase is clean, and the `README.md` explains how to run the system.
