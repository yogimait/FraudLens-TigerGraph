# API Contract

> [[Home]] · [[Architecture]] · [[Agent-Workflow]] · [[UI]]

## Communication Overview

```
Next.js ←→ NestJS:         REST + SSE
NestJS  → Python Agent:     HTTP (FastAPI)
Python  → TigerGraph MCP:   MCP protocol
```

## NestJS REST API (Frontend ↔ Backend)

### Cases

#### `GET /api/cases`
List all 20 benchmark cases.

**Response**:
```json
{
  "cases": [
    {
      "case_id": "HHG-001",
      "opened_at": "2016-12-05T01:55:28",
      "trigger_type": "risk_score",
      "trigger_text": "Real-time model scored...",
      "flagged_txn_id": "3514030",
      "card_id": "C12382-K1",
      "customer_id": "C12382",
      "risk_score": 0.61,
      "status": "pending" | "investigating" | "completed",
      "verdict": null | "fraud" | "legitimate" | "uncertain"
    }
  ]
}
```

#### `GET /api/cases/:caseId`
Get case detail including investigation result if completed.

**Response**: Full case data + investigation result (answer JSON) if available.

#### `POST /api/cases/:caseId/investigate`
Trigger investigation for a case.

**Request**: `{ "case_id": "HHG-001" }`
**Response**: `{ "investigation_id": "inv_xxx", "status": "started" }`

#### `GET /api/cases/:caseId/result`
Get the completed answer JSON for a case.

**Response**: The full answer file JSON (as specified in PRD).

---

### Investigation Progress (SSE)

#### `GET /api/cases/:caseId/stream`
Server-sent events for live investigation progress.

**Events**:
```
event: step
data: {"step": 1, "node": "load_case", "status": "completed", "message": "Loaded case HHG-001"}

event: step
data: {"step": 2, "node": "investigate_graph", "status": "in_progress", "message": "Querying card history..."}

event: evidence
data: {"claim": "Device marked New for this account", "source": "graph", "ref": "get_transaction_device"}

event: assessment
data: {"fraud_probability": 0.65, "pattern": "card_not_present_new_device", "verdict": "uncertain"}

event: action
data: {"actions": [{"action": "VERIFY_WITH_CUSTOMER", "route": "auto"}], "phase": "initial"}

event: complete
data: {"case_id": "HHG-001", "status": "closed_fraud", "verdict": "fraud"}
```

---

### Approvals

#### `GET /api/approvals`
List pending approval requests.

#### `POST /api/approvals/:id/approve`
Approve a pending action (for demo — simulated L1/L2 approval).

#### `POST /api/approvals/:id/reject`
Reject a pending action.

---

### Batch

#### `POST /api/batch/investigate`
Run all 20 cases sequentially. Returns investigation_id for tracking.

#### `GET /api/batch/:batchId/status`
Check batch progress.

---

## NestJS → Python Agent (Internal API)

### `POST /investigate`
Trigger a single case investigation.

**Request**:
```json
{
  "case_id": "HHG-001",
  "case_data": {
    "opened_at": "2016-12-05 01:55:28",
    "trigger_type": "risk_score",
    "trigger_text": "...",
    "flagged_txn_id": "3514030",
    "card_id": "C12382-K1",
    "customer_id": "C12382",
    "risk_score": 0.61
  },
  "stream": true
}
```

**Response** (streaming):
SSE stream of investigation steps, then final complete JSON.

**Response** (non-streaming):
```json
{
  "case_id": "HHG-001",
  "case": { ... },
  "evidence_requests": [ ... ],
  "next_best_actions": { ... },
  "sar": { ... },
  "stop_reason": "...",
  "tool_calls": 9,
  "tokens": 12480,
  "latency_s": 18.7
}
```

### `GET /health`
Agent service health check.

### `GET /status/:investigationId`
Check investigation status (for async processing).

## MongoDB Collections

### `investigationcases`
```json
{
  "_id": "6ab198ebadfe...",
  "case_id": "CASE_2987000",
  "transaction_id": "2987000",
  "status": "awaiting_approval",
  "trigger_type": "risk_score",
  "fraud_probability": 0.3,
  "pattern": "None",
  "verdict": "uncertain",
  "exposure_usd": 0,
  "affected_txn_ids": ["2987000"],
  "sar": { "file": false, "narrative": "", "subjects": [] },
  "next_best_actions": {
    "initial": [],
    "final": [{ "action": "REQUIRE_L1_APPROVAL", "reason": "..." }]
  },
  "approval_status": {
    "decision": "approved",
    "level": "L1",
    "reason": "Analyst review",
    "timestamp": "2026-09-21..."
  }
}
```

### `approvals`
```json
{
  "_id": "appr_xxx",
  "investigation_id": "inv_xxx",
  "case_id": "HHG-001",
  "action": "BLOCK_CARD",
  "route": "L1",
  "reason": "R2: customer denied; exposure $268",
  "status": "pending" | "approved" | "rejected",
  "decided_by": null | "analyst_1",
  "decided_at": null
}
```

## Cross-References

- Frontend consuming these: [[UI]]
- Agent producing these: [[Agent-Workflow]]
- Answer format: [[PRD]]
