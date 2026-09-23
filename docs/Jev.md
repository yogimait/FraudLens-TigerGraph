# Jev / System One — Fast Decision Layer

> [[Home]] · [[Architecture]] · [[Agent-Workflow]] · [[LLM]]

## Role

Jev is the **fast structured decision layer** operating alongside the generative LLM (GPT-OSS-120B). It handles closed-form classification, scoring, and routing decisions.

TypeSafe System One models provide three decision primitives:
- **Choice** — select one of predefined classes
- **Score** — numerical/ordered scoring
- **Noul** — yes/no probability

## Where Jev Fits

```
Graph evidence → Jev (fast classification) → signals
                                              ↓
              → LLM (reasoning/synthesis) → explanations
                                              ↓
                             Policy Engine (deterministic) → actions
```

## Jev Decision Definitions

### 1. Pattern Classification (Choice)

**Question**: "What fraud pattern best explains the evidence?"

**Options**: `card_testing`, `card_not_present_fraud`, `card_not_present_new_device`, `out_of_region_use`, `account_takeover`, `undocumented`, `none`

**Input state**: Transaction details, graph evidence summary, device status, region history, historical case patterns

**Output**: Selected pattern + probability distribution across all options

**Usage**: Input signal to `assess_evidence` node. NOT the final verdict — LLM and graph evidence validate.

### 2. Evidence Sufficiency (Noul)

**Question**: "Is the current evidence sufficient to make a defensible decision?"

**Input state**: Number of evidence items, evidence types (graph/customer/document), number of independent signals, fraud probability range

**Output**: Probability of sufficiency (0–1)

**Usage**: Feeds into `evidence_sufficient` conditional edge. Combined with policy rules (R1, R8).

### 3. Coordination Detection (Noul)

**Question**: "Does the evidence indicate coordinated activity across multiple customers or cards?"

**Input state**: Shared device profiles, shared regions, shared email domains, timing of activity across cards

**Output**: Probability of coordination (0–1)

**Usage**: Triggers R6/R9 policy rules if high. Feeds into `MONITOR_CONNECTED_CARDS` and `FILE_REPORT` decisions.

### 4. Investigation Routing (Choice) — Optional

**Question**: "Which investigation tool should be used next?"

**Options**: `check_device_neighbors`, `check_region_history`, `check_email_connections`, `search_similar_cases`, `check_card_sequence`, `sufficient_evidence`

**Input state**: What has been investigated so far, current evidence gaps

**Usage**: Helps LangGraph decide which TigerGraph query to prioritize. Can fall back to LLM if Jev unavailable.

## What Jev Must NOT Do

| Don't | Why |
|---|---|
| Final fraud verdict | Verdict requires graph evidence + policy + LLM reasoning |
| Action selection | Actions are policy-determined (deterministic code) |
| Approval routing | Routing is deterministic based on exposure thresholds |
| SAR narrative | Requires free-form generation (LLM territory) |
| Graph traversal | TigerGraph's job |
| Exposure calculation | Arithmetic on amounts (code) |

## Jev Output ≠ Ground Truth

**Critical**: Jev's pattern classification probability is NOT `fraud_probability`. They measure different things:
- Jev confidence = how strongly the model selects a pattern
- `fraud_probability` = calibrated probability that the activity IS fraud

The agent must synthesize Jev's signal with graph evidence, historical cases, and policy to produce the final `fraud_probability`.

## Fallback

If Jev API is unavailable:
- Pattern classification → LLM with structured output
- Evidence sufficiency → Rule-based heuristic (evidence count + signal diversity)
- Coordination detection → Graph query (shared device count > 1)
- Investigation routing → LLM tool selection

The system must work without Jev, just with reduced speed/quality for classification.

## Implementation (REAL CALLS — implemented)

`agent/jev_client.py` talks to the real TypeSafe API via `typesafe-sdk` 0.7.1 (`TypeSafeClient.system_one`), keyed by `JEV_API_KEY` from `agent/.env`:

- **`classify_fraud_pattern(txn, history, evidence_summary="", coordination_facts=None)`** — one `system_one` request carrying three questions over a compact JSON state (transaction fields + history velocity stats + evidence summary + sharing facts):
  - `pattern`: **Choice** over the 7 canonical patterns with per-pattern criteria descriptions.
  - `sufficient`: **Noul** — probability the evidence is sufficient for a defensible decision.
  - `coordinated`: **Noul** — probability the sharing facts indicate coordination (feeds R6/R9).
- Standalone `classify_pattern`, `check_sufficiency`, `detect_coordination` wrappers are available for the individual calls.
- Results are marked `"engine": "jev"` or `"heuristic"`. The heuristic fallback is the deterministic graph logic (small-txn velocity, risk + distance, burst counts); it runs when `JEV_API_KEY` is missing or any API call fails.
- A **circuit breaker** stops API retries after the first failure, so a dead/unfunded Jev endpoint adds at most one call of latency per process.
- Backward-compatible keys (`jev_pattern`, `jev_confidence`, `status`) are preserved for `agent/graph.py` / `agent/llm.py`.

**Observed**: with the current `JEV_API_KEY` the API responds `402 no available credits`, so the agent runs on the `heuristic` engine end-to-end; the Jev path activates automatically once credits exist.

```python
from jev_client import classify_fraud_pattern, check_sufficiency, detect_coordination

result = classify_fraud_pattern(txn, history, evidence_summary, {"shared_devices": 2})
# {"engine": "jev"|"heuristic", "pattern": "card_testing", "pattern_label": "Card Testing",
#  "confidence": 0.9, "probabilities": {...}, "sufficiency": 0.7, "coordination": 0.6, ...}
```

## Cross-References

- LLM handles reasoning/synthesis: [[LLM]]
- Agent uses Jev in: [[Agent-Workflow]] → `assess_evidence`, `evidence_sufficient`
- Policy engine consumes Jev signals: [[Policy-Engine]]
