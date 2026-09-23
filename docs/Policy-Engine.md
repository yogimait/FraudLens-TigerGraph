# Policy Engine

> [[Home]] · [[Agent-Workflow]] · [[PRD]] · [[Jev]]

## Principle

The fraud policy is **deterministic, inspectable code** in `agent/policy.py` — NOT hidden inside LLM prompts.

```
LLM reasoning → produces evidence + probability
Jev classification → produces pattern + coordination signals
Policy engine (policy.apply_policy) → deterministically selects actions + approval routes
```

The LLM must NOT override policy. It informs; policy decides. Every action object
carries `{"action", "route", "reason"}` and the reason cites the driving rule
(e.g. `"R5: a purchase over $100 has already cleared"`).

## Implemented Engine

`apply_policy(state)` evaluates the **current** state and returns:

```python
{
  "final_actions":  [{"action", "route", "reason"} ...],   # ordered by execution order
  "initial_actions": [...],                                # echo of state's recorded pre-evidence actions
  "sar_required": bool,                                    # == (FILE_REPORT in final_actions)
  "sar_reason": str,                                       # the FILE_REPORT reason, or ""
}
```

The graph calls it twice: once **before** evidence requests (stored as
`initial_actions`, with the prior probability and no customer response) and once
after assessment/reassessment (stored as `final_actions`). Actions are deduped by
name keeping the highest-severity route (`auto` < `L1` < `L2`) and sorted by
execution order (policy §1): ALLOW → VERIFY → STEP_UP → WARN → MONITOR_CARD →
MONITOR_CONNECTED_CARDS → DECLINE → BLOCK_CARD → BLOCK_ALL_CARDS → CREATE_CASE →
GENERATE_REPORT → FILE_REPORT → ESCALATE → CLOSE_NO_FRAUD.

## Actions Reference

| Action | Customer Impact | Description |
|---|---|---|
| `ALLOW_TRANSACTION` | None | Let the flagged transaction stand |
| `DECLINE_TRANSACTION` | Low | Decline the flagged authorization only |
| `MONITOR_CARD` | None | Raise monitoring sensitivity 72h |
| `MONITOR_CONNECTED_CARDS` | None | Monitor cards linked by device/region/ring |
| `WARN_CUSTOMER` | None | Send informational message |
| `VERIFY_WITH_CUSTOMER` | Low | Ask cardholder to confirm transaction |
| `STEP_UP_AUTH` | Low | Require OTP/app confirmation |
| `BLOCK_CARD` | High | Block and reissue this card |
| `BLOCK_ALL_CARDS` | Very High | Block ALL customer cards |
| `GENERATE_REPORT` | None | Internal writeup without opening case |
| `CREATE_CASE` | None | Open internal fraud case, write to graph |
| `FILE_REPORT` | None | File SAR with regulator |
| `ESCALATE_TO_ANALYST` | None | Hand to human analyst |
| `CLOSE_NO_FRAUD` | None | Close alert as legitimate |

## Approval Routes (implemented in `_route`)

| Route | Actions |
|---|---|
| `auto` | ALLOW_TRANSACTION, MONITOR_CARD, MONITOR_CONNECTED_CARDS, WARN_CUSTOMER, VERIFY_WITH_CUSTOMER, STEP_UP_AUTH, GENERATE_REPORT, CREATE_CASE, ESCALATE_TO_ANALYST, CLOSE_NO_FRAUD |
| `L1` | DECLINE_TRANSACTION; BLOCK_CARD when exposure ≤ $2,500 |
| `L2` | BLOCK_CARD when exposure > $2,500; BLOCK_ALL_CARDS always; FILE_REPORT always |

**Only `auto` actions may be executed by the agent.** L1/L2 are recommendations
that wait for a human.

## Rules as Implemented (R1–R10)

Inputs read from state: `verdict`, `fraud_probability`, `pattern`, `exposure_usd`,
`trigger_type`, `customer_response` (`""|denied|confirmed|no_reply`),
`evidence` (graph/customer/external entries count as signals; documents don't),
`connected_device_profiles` (shared origin), `jev_classification.coordination`,
`related_txns` (R5 cleared-purchase check), `evidence_request_count`.

- **R1 verify-before-block**: `BLOCK_CARD` is suppressed whenever the case rests
  on ≤1 independent signal at `fraud_probability < 0.70`; `VERIFY_WITH_CUSTOMER`
  (or `STEP_UP_AUTH` when fp ≥ 0.70 on multiple signals) is recommended instead,
  plus `MONITOR_CARD` while unverified.
- **R2 customer denies**: `BLOCK_CARD` (route by exposure) + `CREATE_CASE`;
  `FILE_REPORT` via the §3a computation when exposure > $1,000 or a shared
  device/other-card connection exists.
- **R3 customer confirms**: verdict treated as `legitimate`; `CLOSE_NO_FRAUD`;
  never blocks, never files. For disputed-but-legitimate charges, R7 actions apply.
- **R4 no reply**: `MONITOR_CARD` + `DECLINE_TRANSACTION`; `ESCALATE_TO_ANALYST`
  when exposure > $500. Not applied when the verdict is already `fraud` on
  independent evidence.
- **R5 card testing**: pattern `card_testing` → `DECLINE_TRANSACTION` +
  `STEP_UP_AUTH`; `BLOCK_CARD` when a related purchase over $100 has cleared.
- **R6 shared origin**: connected device profiles linking other cards →
  `CREATE_CASE` + `FILE_REPORT` (L2) + `MONITOR_CONNECTED_CARDS`.
- **R7 disputed but legitimate**: `customer_report` trigger + legitimate verdict →
  `CREATE_CASE` + `VERIFY_WITH_CUSTOMER` (unless already confirmed) +
  `WARN_CUSTOMER`; never blocks.
- **R8 uncertain and exposed**: `ESCALATE_TO_ANALYST` when uncertain and
  exposure > $500, or the evidence is unresolved (verification left unanswered at
  fp ≥ 0.50 counts as conflict).
- **R9 undocumented coordinated**: pattern `undocumented` with coordination ≥ 0.5
  (or shared origin) → `CREATE_CASE` + `FILE_REPORT` + `ESCALATE_TO_ANALYST`;
  the pattern is described in `pattern_description`, never forced into a known type.
- **R10 guard**: `BLOCK_ALL_CARDS` is stripped from the final list unless ≥2 cards
  are confirmed fraud/credentials compromised (`confirmed_compromised_card_count ≥ 2`).
  No engine rule ever emits it; the filter is the standing guard.

## Section 3a Triggers

- **CREATE_CASE** whenever `fraud_probability >= 0.30`, evidence was requested,
  or the customer disputed a charge.
- **FILE_REPORT** when fraud is confirmed or strongly suspected (`fraud` verdict,
  or fp ≥ 0.70 without a settling customer confirmation) AND any of: exposure >
  $1,000; shared device/region/other-customer fraud connection; coordinated or
  undocumented pattern (R9). `sar.file` always equals `(FILE_REPORT in final)`.
- A disputed-but-legitimate case still opens a case (R7) and a legitimate
  risk-score case records `GENERATE_REPORT` instead when no case is required.

## Stopping Conditions (Section 6, implemented in `graph._stop_reason`)

The router `evidence_sufficient` stops when one holds:

1. `fraud_probability >= 0.85` or `<= 0.15` with ≥2 independent evidence items
2. A verification response settles the question (`denied`/`confirmed`)
3. The one evidence-request round completed — further steps are unlikely to
   change the decision

`stop_reason` states which condition held; the LLM may refine the wording only.

## Evidence Request Simulation (Section 5)

Implemented in `graph.request_evidence` / `simulate_response`:

- Request type: `customer_validation` for disputes/weak signals,
  `step_up_auth` for strong fraud lean (fp ≥ 0.70 or fraud-like pattern),
  `analyst_info` available per policy.
- The response is simulated deterministically: `denied` when strong fraud
  evidence exists (fp ≥ 0.70 or fraud-like pattern), `confirmed` when the case
  matches a legitimate recurring dispute (fp ≤ 0.30, pattern `none`,
  `customer_report` trigger), otherwise `no_reply`.
- The assumption is recorded verbatim in `evidence_requests[].assumed_response`
  and the response enters the evidence list as `source: "customer"`.

## Exposure (Section 4)

`exposure_usd` = sum of `abs(amount)` over `affected_txn_ids` only (the fraud
episode, flagged txn included). Legitimate verdicts → `0`. Unrelated card
transactions are never summed.

## Tests

`agent/tests/test_policy.py` covers every rule, route boundary (≤/$ > $2,500),
section 3a triggers, R10 guard, legitimate path, and R8 escalation (56 tests
total with `test_answer_writer.py` and `test_flow.py`).

## Cross-References

- Where rules run: [[Agent-Workflow]] → `apply_policy` node
- Actions in API: [[API]]
- Answer format: [[PRD]]
- Decisions: [[Decisions]]