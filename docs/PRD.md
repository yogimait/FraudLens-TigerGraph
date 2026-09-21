# Product Requirements Document

> Source of truth: [[Home]] ← `Initial-docs/TigerGraph Agentic Fraud Investigation HHGOA.md` and `Initial-docs/dataset/README (1).md`

## Problem Statement

Fraud analysts at financial institutions manually investigate transaction history, trace money movement, identify connected accounts, review policies, assess risk, document findings, and decide actions. This process is slow, fragmented, and often completes after money is gone.

## What We Are Building

An **agentic fraud investigation system** that:

1. Receives fraud triggers (risk score, customer report, analyst request)
2. Investigates using TigerGraph (graph traversal, pattern detection, historical case retrieval)
3. Assesses fraud patterns and risk level using evidence
4. Creates and progresses fraud cases
5. Uses case memory from prior investigations
6. Requests additional evidence when uncertain (customer validation, step-up auth, analyst info)
7. Recommends policy-compliant next-best-actions with proper approval routing
8. Explains reasoning with evidence provenance
9. Generates SAR narratives when policy requires
10. Writes completed cases back to graph as case memory

**This is NOT an ML fraud-detection model. This is NOT a chatbot. This is an agentic investigator.**

## Target Users

- **Primary**: Fraud analysts reviewing investigations and approving/rejecting agent recommendations
- **Secondary**: Team leads (L1) and fraud managers (L2) for approval workflows
- **Tertiary**: Hackathon judges evaluating the 20 benchmark cases

## Core Investigation Flow

```
Trigger → Investigate → Gather evidence → Assess uncertainty
    → Gather more evidence if needed → Take action → Explain → Update case memory
```

## Required Deliverables

### 1. Working Agent
Processes all 20 benchmark cases from `case_pack.csv`.

### 2. Answer Files
One JSON per case (`cases/HHG-001.json` through `cases/HHG-020.json`), each containing:

| Part | Contents |
|---|---|
| **Case** (Part 1) | Status, verdict, fraud_probability, pattern, affected_txn_ids, connected_card_ids, connected_device_profiles, exposure_usd, evidence[], similar_prior_cases[], summary, written_to_graph, graph_case_id |
| **SAR** (Part 2) | file (bool), reason, narrative (who/what/when/where/how/why), subjects[], total_amount_usd, activity_dates |
| **Next Best Actions** (Part 3) | initial[] (before evidence request), final[] (after), what_changed |
| **Metadata** | stop_reason, tool_calls, tokens, latency_s, evidence_requests[] |

### 3. GitHub Repository
Complete source code.

### 4. Demo Video (3–5 minutes)
End-to-end demonstration showing the agent investigating, gathering evidence, recommending actions, and explaining decisions.

### 5. Technical Blog Post
Architecture, TigerGraph usage, agentic capabilities, learnings, improvements.

### 6. Social Media Post
X or LinkedIn, tag @TigerGraphDB, link to blog/demo.

## Dataset Constraints

- **590,742 transactions**, 6 months (July–December 2016), ~13,500 customers
- **No `isFraud` flag** — only `risk_score` (0–1), which is an input, NOT an answer
- **risk_score ≠ fraud verdict**: many high scores are legitimate, some fraud scores low
- **Half the 20 cases are likely legitimate** — blocking everything scores badly
- **5,565 closed cases** (Jul–Oct): 4,665 confirmed fraud, 900 cleared — this IS the labeled ground truth
- **20 exam cases** (Nov–Dec): the benchmark; 11 risk_score triggers, 8 customer_reports, 1 analyst_request
- **Trigger types**: `risk_score`, `customer_report`, `analyst_request`
- **5 known patterns**: `card_testing`, `card_not_present_fraud`, `card_not_present_new_device`, `out_of_region_use`, `account_takeover`
- **Additional patterns exist** in data — `undocumented` pattern value is scored
- **IDs must exist in dataset** — made-up IDs score zero
- **DO NOT use public Kaggle IEEE-CIS files** to recover outcomes — disqualification
- Customer/analyst replies NOT provided — simulate responses, record assumptions

## Verdict Values

`fraud` · `legitimate` · `uncertain`

`uncertain` is valid and earns full credit on ambiguous cases **if actions follow R1 and R8**.

## Pattern Values

`card_testing` · `card_not_present_fraud` · `card_not_present_new_device` · `out_of_region_use` · `account_takeover` · `undocumented` · `none`

## Scoring Note

- `fraud_probability` is scored for **calibration** — honest assessment matters
- Initial and final recommendations must be recorded separately
- Evidence must cite source (`graph` | `document` | `customer` | `external`), ref (query name, document section), and entity_ids

## Cross-References

- Fraud policy rules: [[Policy-Engine]]
- Answer format: `Initial-docs/dataset/README (1).md` → "Answer Format" section
- Graph schema: [[Data-Model]]
- Agent workflow: [[Agent-Workflow]]
