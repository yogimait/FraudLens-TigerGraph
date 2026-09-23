# Demo Video Script — FraudLens (3–5 min)

> Deliverable per the problem statement: 3–5 minute video showing the agent working end to end. Structure follows the judging criteria: investigation accuracy, next best action, explainability, agentic design, innovation, demo quality. Pair with [[Home]] and [[Architecture]].
> Recording checklist at the bottom. Target runtime: **4:00**.

## Pre-recording state (do before recording)

- [ ] Fresh benchmark run done; Mongo contains only `HHG-001..020`
- [ ] Dashboard open on Dashboard page, approvals queue populated (17 awaiting approval expected)
- [ ] LangSmith trace page open in a second browser tab (agent trace evidence)
- [ ] TigerGraph Savanna dashboard open in a third tab (graph proof)
- [ ] Screen recorder at 1920×1080, browser zoom 100%

---

## Act 1 — The Problem (0:00–0:25)

**On screen:** Dashboard, KPI strip, case table.

> "Fraud analysts investigate every flagged transaction by hand: pulling card history, tracing devices, checking past cases, writing reports. Slow, fragmented, and the money is often already gone.
>
> This is FraudLens — an agentic fraud investigation system built on TigerGraph for the TigerGraph Hacker House Goa challenge. It investigates automatically, gathers evidence as a graph, reasons over it with an LLM, and recommends the next best action — inside a deterministic policy engine that says what it may and may not do."

## Act 2 — Trigger an Investigation (0:25–1:00)

**On screen:** Click **New Investigation**, select a benchmark case (e.g. HHG-014 analyst_request), trigger.

> "Everything starts with a trigger: a bank risk score, a customer dispute, or an analyst request. I'm triggering case HHG-014 — an analyst flagged several cards buying from the same unusual device profile.
>
> Behind the scenes a LangGraph state machine takes over: load the case from TigerGraph, walk the fraud network with GSQL, pull similar past cases from case memory, retrieve the fraud policy with GraphRAG, classify the pattern with Jev, and only then let the LLM reason over the assembled evidence.
>
> Every graph access goes through the TigerGraph MCP server — 69 tools — with a pyTigerGraph fallback. Deterministic, auditable, and nothing is invented."

**Cut to (optional overlay):** the LangGraph node diagram or a LangSmith trace listing the tool calls (get_card_transactions, get_transaction_device, vector search...).

## Act 3 — The Case Dossier: Evidence and Uncertainty (1:00–1:55)

**On screen:** Case detail page → Overview + Evidence & Analysis tabs.

> "Here is the investigation the agent built. Every fact carries provenance: blue for graph queries, amber for documents, green for the customer. Click any entity id and it's real — every ID in the output exists in the IEEE-CIS dataset.
>
> The verdict is deliberately shown as fraud_probability — a calibrated estimate, not the bank's risk score. The agent is explicitly told the risk score is a prior, not an answer, and half of flagged cases are legitimate.
>
> When evidence is thin, the agent doesn't guess — it asks for more: here it requested customer validation, simulated the reply, recorded the assumption, and reassessed. Policy rule R1: verify before you block on a weak signal. Stopping conditions are deterministic code, not prompt vibes."

## Act 4 — Policy Engine: Recommendations with Approval Routes (1:55–2:40)

**On screen:** Policy Actions tab — initial vs final actions, route badges, what_changed. Then Approvals Center, approve an L1 case.

> "Actions come from the policy engine — R1 through R10 are code, not prompts. The LLM can never override them. Note the initial recommendation before evidence, the final recommendation after, and what changed.
>
> Each action carries its approval route: green auto actions the agent executes itself; amber L1 goes to a team lead; red L2 goes to the fraud manager — file a report, block all cards, or block a card over $2,500 exposure, exactly as the policy table demands.
>
> The Approvals Center queues anything needing a human. I approve at the correct level — the backend rejects mismatched approvals — and the case closes with a full audit trail."

## Act 5 — SAR and Case Memory (2:40–3:10)

**On screen:** SAR tab on HHG-010; then Archive / case memory chips on the case page.

> "When policy triggers a report — confirmed fraud plus exposure over $1,000, a shared device, or an undocumented pattern — the agent drafts a standalone SAR narrative with subjects, dates and total exposure, ready for the analyst.
>
> Every investigation is written back into TigerGraph as an InvestigationCase vertex, linked with SIMILAR_TO edges, so the next investigation starts with memory, not amnesia. That's GraphRAG plus case memory in one graph."

## Act 6 — The Fraud Network (3:10–3:40)

**On screen:** Graph Explorer page; hover a node, then a case Graph View.

> "And because fraud is a network problem, here's the graph itself — an Obsidian-style force-directed explorer over the TigerGraph fraud network. Cards, transactions, devices and prior cases, hover to isolate a neighborhood. The agent sees exactly this structure through GSQL traversal and shared-device queries."

## Act 7 — Results and Close (3:40–4:00)

**On screen:** Analytics page — verdict distribution, patterns, exposure; end card with repo + blog link.

> "The agent investigated all 20 benchmark cases end to end: calibrated probabilities, honest uncertainty, policy-compliant actions with recorded approval routes, and a full evidence trail on every case.
>
> Uncertain is a verdict, not a failure — on ambiguous cases it escalates instead of blocking legitimate customers. That discipline is the whole point. FraudLens: detect, investigate, prevent."

---

## Recording notes

- Total narration ≈ 3:40–4:00 at normal pace; trim Act 1 if over.
- Show, don't claim: when narrating "69 MCP tools", have the MCP self-check output or LangSmith trace visible.
- If a 429 rate limit hits mid-recording, use the pre-generated benchmark case (open a case page that already has data) and re-record the trigger on another case.
- End card: repo URL + blog URL + "Built with TigerGraph MCP, LangGraph, Jev, Groq GPT-OSS-120B".