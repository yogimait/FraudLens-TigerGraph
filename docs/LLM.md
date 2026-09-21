# LLM — GPT-OSS-120B Responsibilities

> [[Home]] · [[Architecture]] · [[Agent-Workflow]] · [[Jev]]

## Model

**Groq GPT-OSS-120B** via OpenAI-compatible API.

| Spec | Value |
|---|---|
| Context | 131,072 tokens |
| Max output | 65,536 tokens |
| Speed | ~500 tok/s |
| Input cost | $0.15 / 1M tokens |
| Output cost | $0.60 / 1M tokens |
| Tool use | ✅ |
| JSON Schema | ✅ (structured outputs) |
| Reasoning | ✅ |

## What the LLM DOES

1. **Evidence synthesis** — reason over structured graph evidence + historical cases to form hypotheses
2. **Investigation planning** — decide which TigerGraph queries to run next given current state
3. **Evidence gap identification** — determine what information is missing
4. **Pattern reasoning** — explain why evidence matches or doesn't match known patterns
5. **Fraud probability calibration** — produce honest probability based on all evidence (with Jev signal as input)
6. **Case summary generation** — 2–6 sentence analyst summary
7. **SAR narrative generation** — 6–12 sentences: who, what, when, where, how, why
8. **Stop reason generation** — explain why investigation ended
9. **What-changed explanation** — explain why final actions differ from initial

## What the LLM does NOT do

| Responsibility | Owned by |
|---|---|
| Deterministic policy rules | Policy Engine (code) |
| Approval route selection | Policy Engine (code) |
| Exposure calculation | Code (sum of amounts) |
| Graph traversal | TigerGraph (GSQL) |
| Evidence provenance tracking | Code (structured evidence objects) |
| Fast classification/routing | Jev |
| Case writing to graph | TigerGraph MCP |
| Dataset truth | Dataset files |

## Structured Output Schemas

### Evidence Synthesis
```json
{
  "fraud_probability": 0.72,
  "pattern": "card_not_present_new_device",
  "pattern_description": "",
  "reasoning": "Three transactions from a device marked New...",
  "confidence_factors": [
    "Device marked New for this account",
    "Same device seen on closed case CC-0141"
  ],
  "uncertainty_factors": [
    "Customer has not been contacted yet"
  ],
  "needs_more_evidence": true,
  "suggested_evidence_type": "customer_validation"
}
```

### Case Summary
```json
{
  "summary": "Textbook card testing: three sub-$3 online authorizations in 40 minutes, then a $259 purchase in a category the cardholder has never used. All four share a device profile marked New for this account. Customer denied the activity."
}
```

### SAR Narrative
```json
{
  "narrative": "On 2016-11-14 between 09:12 and 09:52, card C00377-K1 belonging to customer C00377 was used for three online authorizations of $1.10, $2.40, and $0.95 followed at 10:31 by a $259.98 online purchase..."
}
```

## Prompt Design Principles

1. **Provide structured evidence**, not raw data — the LLM should reason over pre-processed graph results
2. **Include policy context** — pass relevant policy rules (retrieved via GraphRAG) alongside evidence
3. **Include similar prior cases** — analyst_notes from closed_cases_history
4. **Request structured output** — use JSON Schema mode for all LLM calls
5. **Be explicit about what V/C/D/M columns mean** — "unnamed engineered features used as signals"
6. **Never ask LLM to replace graph analysis** — it reasons OVER graph results, not INSTEAD of them

## Token Budget Per Case

Target: < 15,000 tokens per case investigation.

| Component | Estimated tokens |
|---|---|
| System prompt + policy | ~2,000 |
| Evidence context | ~3,000 |
| Historical cases | ~2,000 |
| Evidence synthesis call | ~3,000 |
| Summary generation | ~1,500 |
| SAR narrative (if needed) | ~2,000 |
| Stop reason + what_changed | ~500 |
| **Total** | **~14,000** |

## Cross-References

- Jev handles fast classification: [[Jev]]
- Agent uses LLM in these nodes: [[Agent-Workflow]] → `assess_evidence`, `generate_outputs`
- Structured outputs feed into: [[Policy-Engine]]
