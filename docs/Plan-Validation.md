# Plan Validation

> [[Home]] · [[PRD]] · [[Architecture]] · [[Questions]]

## Consistency Check

| Check | Status | Notes |
|---|---|---|
| PRD agrees with architecture | ✅ | All 10 PRD capabilities mapped to architecture components |
| Architecture agrees with API | ✅ | API endpoints match component responsibilities |
| API agrees with agent workflow | ✅ | Agent produces answer JSON matching API response schema |
| Agent workflow agrees with policy | ✅ | `apply_policy` node implements R1–R10 deterministically |
| Policy agrees with dataset rules | ✅ | Actions, routes, thresholds match dataset README exactly |
| TigerGraph schema agrees with dataset | ✅ | Vertices/edges map to CSV files; suggested schema followed + extended |
| UI reflects backend capabilities | ✅ | UI pages consume actual API endpoints |
| Implementation tasks cover requirements | ✅ | Phases 0–7 cover all deliverables |
| No undocumented dependency introduced | ✅ | All tech choices justified in [[Decisions]] |
| No prohibited dataset assumption | ✅ | No Kaggle data, no invented IDs, no isFraud flag |
| No fake IDs/data assumed | ✅ | All IDs must come from dataset |
| No required output forgotten | ✅ | All 6 deliverables accounted for |

## Confirmed Requirements

1. ✅ 20 answer files in `cases/` folder matching exact JSON schema
2. ✅ Three-part answer: case + SAR + next_best_actions
3. ✅ Initial and final actions recorded separately
4. ✅ Evidence requests with assumed responses
5. ✅ Evidence provenance (source, ref, entity_ids)
6. ✅ Cases written to TigerGraph graph
7. ✅ SAR only when policy requires (case vs report distinction)
8. ✅ Policy rules R1–R10 as deterministic code
9. ✅ Approval routes (auto/L1/L2) correctly assigned
10. ✅ Stop conditions from policy section 6
11. ✅ All IDs from dataset
12. ✅ risk_score treated as input, not answer
13. ✅ `uncertain` is valid verdict
14. ✅ `undocumented` is valid pattern
15. ✅ `fraud_probability` calibrated honestly

## Unresolved Questions

See [[Questions]] — 3 CRITICAL, 3 HIGH, 3 MEDIUM, 3 LOW.

**None of the CRITICAL questions block starting Phase 0.** All have reasonable defaults.

## Assumptions

| Assumption | Risk if wrong | Mitigation |
|---|---|---|
| card_id can be derived from (customer_id, card1) | Data loading fails; case_pack cards not found | Verify during T0.3; adjust derivation logic |
| TigerGraph Savanna free tier has TigerVector 4.2+ | GraphRAG falls back to keyword search | Check during T0.1; use CE if needed |
| Jev SDK is stable enough for integration | Classification falls back to LLM-only | Build fallback from day 1 (D7) |
| Groq rate limits won't block 20-case batch | Add delays; worst case process sequentially | Monitor during T3.1 |
| One evidence request per case is sufficient | Some cases under-investigated | Can add second request loop if needed |
| Customer_report trigger → simulate customer denial | Simulation may not match answer key | Reasonable assumption; README suggests this |

## Architectural Risks

| Risk | Severity | Mitigation |
|---|---|---|
| TigerGraph data loading for 590K txns takes too long | HIGH | Stream in batches; load core entities first, expand |
| LLM hallucinating transaction IDs in evidence | HIGH | All IDs must be verified against actual graph query results |
| Policy engine misinterpreting edge cases | MEDIUM | Test each rule against known closed_cases_history patterns |
| Evidence simulation assumptions don't match answer key | MEDIUM | Document all assumptions transparently |
| MCP connection instability | MEDIUM | Retry logic; fall back to direct REST if needed |
| Time pressure — 3 days for full system | HIGH | Critical path: TG → MCP → Agent → 20 cases; UI is secondary |

## Missing Information

| Item | Impact | Source |
|---|---|---|
| Answer key for 20 cases | Can't pre-validate accuracy | Only judges have this |
| Exact card_id derivation formula | Data loading correctness | Verify empirically during T0.3 |
| TigerGraph Savanna version | TigerVector availability | Check during T0.1 |
| Jev SDK current API surface | Integration code | Check docs at integration time |

## Recommended First Implementation Step

**Start with Phase 0, Task T0.1**: Create TigerGraph Savanna workspace.

Then immediately T0.2 (schema) and T0.3 (data loading) — because the entire agent depends on having a populated graph to query.

In parallel, start T2.1 (Python project setup) since it has no TigerGraph dependency.

```
PARALLEL TRACK A:  T0.1 → T0.2 → T0.3 → T0.4 → T0.5 → T1.1 → T1.2
PARALLEL TRACK B:  T2.1 → T2.2 (state schema)
MERGE:             T2.3 → T2.4 → ... (agent nodes need MCP)
```

## Cross-References

- All documentation: [[Home]]
- Open questions: [[Questions]]
- Decisions: [[Decisions]]
- Development plan: [[Development-Plan]]
