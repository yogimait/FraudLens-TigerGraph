# Open Questions

> [[Home]] · [[Decisions]] · [[Architecture]]

Questions that could materially affect implementation. Grouped by priority.

---

## CRITICAL — Blocks implementation if unresolved

*(None - all critical questions resolved. See [[Decisions]])*

---

## HIGH — Affects quality if unresolved

*(None - all high priority questions resolved. See [[Decisions]])*

---

## MEDIUM — Affects demo/polish

*(None - all medium priority questions resolved. See [[Decisions]])*

---

## LOW — Nice to have

*(None - all low priority questions resolved. See [[Decisions]])*

---

## Resolved

### Q1. TigerGraph Savanna version and TigerVector availability
**Resolved**: Use TigerGraph Savanna as primary deployment. Target is 4.2+ for TigerVector. Must verify version first. If not available, determine if upgrade is possible before falling back to Community Edition. Graph investigation must work without vector search. (Decision: D13)

### Q2. card_id derivation from transactions.csv
**Resolved**: Do NOT blindly assume K-suffix mapping. Create deterministic validation step before finalizing schema to verify exact reconstruction of `card_id`s in `case_pack.csv` and `closed_cases_history.csv`. (Decision: D14)

### Q3. Jev API key validity and SDK version
**Resolved**: Jev is a structured decision component but not a hard dependency. Verify official Python package (jev/jevclient) and API key first. Agent must degrade gracefully to GPT-OSS-120B if Jev is unavailable. (Decision: D7 updated)

### Q4. Evidence simulation strategy
**Resolved**: Use policy-driven simulation. Customer_report → assume customer disputes. Risk_score → simulate based on evidence strength (weak evidence = conservative confirmation, strong evidence = denial). Record assumptions explicitly. (Decision: D9 updated)

### Q5. How many evidence requests per case?
**Resolved**: Default maximum: 1 evidence request per case. Architecture should support more, but for benchmark use 0 or 1 to reward efficient investigation. (Decision: D15)

### Q6. Groq rate limits for batch processing
**Resolved**: Do not hardcode fixed delays. Use adaptive rate limiting, exponential backoff on 429, respect Retry-After, and process benchmark cases in controlled batches/sequential. (Decision: D6 updated)

### Q7. Deployment strategy for demo
**Resolved**: Primary target: localhost. Full system must be locally runnable. Cloud deployment only if time permits. (Decision: D16)

### Q8. Graph visualization library
**Resolved**: Use lightweight SVG/Mermaid first. Prioritize readability. Only add `react-force-graph-2d` if UI is complete and time permits. (Decision: D17)

### Q9. LangSmith setup
**Resolved**: Optional but strongly preferred. Do not block on it. Implement local structured logging fallback. (Decision: D18)

### Q10. Optional monitoring of exam period
**Resolved**: Skip. Focus entirely on the 20 benchmark cases. (Decision: D19)

### Q11. Authentication
**Resolved**: No authentication for MVP. (Decision: D20)

### Q12. Regulatory documents
**Resolved**: Do NOT make external ingestion part of critical path. Priority is challenge-provided policy/data. (Decision: D21)

## Cross-References

- Decisions: [[Decisions]]
- Architecture: [[Architecture]]
- Development plan: [[Development-Plan]]
