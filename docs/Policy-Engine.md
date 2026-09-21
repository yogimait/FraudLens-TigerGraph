# Policy Engine

> [[Home]] · [[Agent-Workflow]] · [[PRD]]

## Principle

The fraud policy is **deterministic, inspectable code** — NOT hidden inside LLM prompts.

```
LLM reasoning → produces evidence + probability
Jev classification → produces pattern + signals
Policy engine → deterministically selects actions + approval routes
```

The LLM must NOT override policy. It informs; policy decides.

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

Multiple actions per case allowed. Order by execution priority.

## Approval Routes

| Route | Actions |
|---|---|
| `auto` | ALLOW_TRANSACTION, MONITOR_CARD, MONITOR_CONNECTED_CARDS, WARN_CUSTOMER, VERIFY_WITH_CUSTOMER, STEP_UP_AUTH, GENERATE_REPORT, CREATE_CASE, ESCALATE_TO_ANALYST, CLOSE_NO_FRAUD |
| `L1` (team lead) | DECLINE_TRANSACTION; BLOCK_CARD when exposure ≤ $2,500 |
| `L2` (fraud manager) | BLOCK_CARD when exposure > $2,500; BLOCK_ALL_CARDS always; FILE_REPORT always |

**Only `auto` actions may be executed by the agent.** L1/L2 are recommendations.

## Rules (R1–R10) — Implementation Pseudocode

### R1. Verify before blocking on weak signal
```python
if single_signal and fraud_probability < 0.70:
    actions.append(VERIFY_WITH_CUSTOMER or STEP_UP_AUTH)
    # DO NOT add any block action
    # Blocking on single weak signal is a policy breach
```

### R2. Customer denies the transaction
```python
if customer_denies:
    actions.append(("BLOCK_CARD", get_block_route(exposure)))
    actions.append(("CREATE_CASE", "auto"))
    if exposure > 1000 or shared_device_fraud or other_card_fraud:
        actions.append(("FILE_REPORT", "L2"))
```

### R3. Customer confirms the transaction
```python
if customer_confirms:
    actions = [("CLOSE_NO_FRAUD", "auto")]
    # Note confirmation in case file
```

### R4. No reply within 24 hours
```python
if no_reply_24h:
    actions.append(("MONITOR_CARD", "auto"))
    actions.append(("DECLINE_TRANSACTION", "L1"))  # pending auths
    if exposure > 500:
        actions.append(("ESCALATE_TO_ANALYST", "auto"))
```

### R5. Card testing
```python
if card_testing_detected:  # 3+ small online auths in 1h → larger purchase
    actions.append(("DECLINE_TRANSACTION", "L1"))
    actions.append(("STEP_UP_AUTH", "auto"))
    if any_cleared_purchase_over_100:
        actions.append(("BLOCK_CARD", get_block_route(exposure)))
```

### R6. Shared origin
```python
if shared_device_fraud or shared_region_fraud or shared_email_fraud:
    # Name the shared element in evidence
    actions.append(("CREATE_CASE", "auto"))
    actions.append(("FILE_REPORT", "L2"))
    actions.append(("MONITOR_CONNECTED_CARDS", "auto"))  # every card sharing the element
```

### R7. Disputed but legitimate (recurring pattern match)
```python
if customer_disputes and matches_recurring_pattern:
    actions.append(("CREATE_CASE", "auto"))
    actions.append(("VERIFY_WITH_CUSTOMER", "auto"))
    actions.append(("WARN_CUSTOMER", "auto"))
    # DO NOT block
```

### R8. Escalate when uncertain and exposed
```python
if verdict == "uncertain" and (exposure > 500 or evidence_conflicts):
    actions.append(("ESCALATE_TO_ANALYST", "auto"))
```

### R9. Undocumented patterns
```python
if evidence_shows_coordinated_abuse and not_known_pattern:
    pattern = "undocumented"
    # Describe in pattern_description
    actions.append(("CREATE_CASE", "auto"))
    actions.append(("FILE_REPORT", "L2"))
    actions.append(("ESCALATE_TO_ANALYST", "auto"))
```

### R10. BLOCK_ALL_CARDS guard
```python
if action == "BLOCK_ALL_CARDS":
    assert (
        count_cards_with_confirmed_fraud >= 2
        or credentials_confirmed_compromised
    ), "R10: need 2+ cards with fraud OR confirmed credential compromise"
```

## Approval Route Helper

```python
def get_block_route(exposure_usd: float) -> str:
    return "L1" if exposure_usd <= 2500 else "L2"
```

## Case vs Report Decision (Section 3a)

### CREATE_CASE when:
- `fraud_probability >= 0.30`
- Evidence was requested
- Customer disputed a charge

### FILE_REPORT when:
- Fraud confirmed or strongly suspected AND at least one:
  - Exposure > $1,000
  - Shared device profile with another customer's fraud
  - Shared region cluster with another customer's fraud
  - Coordinated or undocumented pattern (R9)

### `sar.file` must agree with `FILE_REPORT` in final actions.

## Stopping Conditions (Section 6)

Stop when ONE holds:
1. `fraud_probability >= 0.85` or `fraud_probability <= 0.15` with **2+ independent evidence**
2. Verification response settles the question
3. Further steps unlikely to change the decision (state in `stop_reason`)

**Both early stops and late stops are marked down.**

## Evidence Request Simulation (Section 5)

Agent may ask without approval:
- `customer_validation` — ask customer if they made the transaction
- `step_up_auth` — request OTP/app confirmation
- `analyst_info` — request information from analyst

Responses are NOT provided. Simulate in system, state assumption in `evidence_requests[].assumed_response`.

## Cross-References

- Agent applies these rules: [[Agent-Workflow]] → `apply_policy` node
- Actions in API: [[API]]
- Answer format: [[PRD]]
