# UI — Analyst Dashboard

> [[Home]] · [[API]] · [[Architecture]]

## Design Goal

A fraud analyst dashboard that makes the agent's investigation **visible, understandable, and actionable**. Prioritize demo quality — judges must see the agentic loop.

## Pages

### 1. Case Dashboard (`/`)
**Purpose**: Overview of all 20 benchmark cases.

**Layout**: Table/card grid with:
- Case ID, trigger type badge (risk_score / customer_report / analyst_request)
- Customer ID, Card ID
- Risk score (if applicable)
- Status badge: pending → investigating → completed
- Verdict badge: fraud (red) / legitimate (green) / uncertain (amber)
- Quick-action: "Investigate" button

**Priority**: HIGH — entry point for demo

---

### 2. Investigation View (`/case/:id`)
**Purpose**: Real-time view of agent investigating a case. **This is the money shot for the demo.**

**Layout**: Three-panel:

#### Left Panel — Case Info
- Case metadata (ID, trigger, customer, card, risk_score)
- Current status / verdict / fraud probability gauge
- Exposure amount
- Pattern identified

#### Center Panel — Investigation Timeline
Live-updating timeline showing each agent step:
```
[09:32:01] 🔍 Investigation triggered — HHG-001
[09:32:02] 📊 Loading transaction 3514030 — $77.07
[09:32:03] 🔗 Querying card history for C12382-K1
[09:32:04] 🖥️ Checking device profile
[09:32:05] 📁 Found 2 similar historical cases
[09:32:06] ⚖️ Assessing evidence — probability: 0.65
[09:32:07] ❓ Evidence insufficient — requesting customer verification
[09:32:08] 📩 Customer denies transaction
[09:32:09] ⚖️ Reassessing — probability: 0.88
[09:32:10] ✅ Actions: BLOCK_CARD (L1), CREATE_CASE (auto)
```

**Implementation**: SSE from `GET /api/cases/:id/stream`

#### Right Panel — Evidence & Actions
Tabbed:
- **Evidence tab**: List of evidence items with source badges (graph/document/customer)
- **Actions tab**: Initial actions vs Final actions, approval routes, what_changed
- **Graph tab**: Visual representation of connected entities (customer → cards → devices → other cards)
- **Similar Cases tab**: Prior cases retrieved, with pattern and outcome

---

### 3. Case Result (`/case/:id/result`)
**Purpose**: Completed investigation detail.

Sections:
- **Summary**: 2–6 sentence case summary
- **Evidence**: Full evidence list with provenance
- **SAR**: If filed — narrative, subjects, dates, amount
- **Next Best Actions**: Initial vs Final comparison
- **Graph View**: Entity relationship visualization
- **Similar Cases**: Prior case citations
- **Metadata**: tool_calls, tokens, latency

---

### 4. Approval Queue (`/approvals`)
**Purpose**: Show pending L1/L2 approval requests. Demonstrates permission model.

- List of pending actions with case context
- Approve / Reject buttons (simulated for hackathon)

---

## Component Hierarchy

```
App
├── CaseDashboard
│   ├── CaseCard (×20)
│   └── CaseFilters (trigger type, status, verdict)
├── InvestigationView
│   ├── CaseInfoPanel
│   │   ├── CaseMetadata
│   │   ├── VerdictBadge
│   │   ├── FraudProbabilityGauge
│   │   └── ExposureAmount
│   ├── InvestigationTimeline
│   │   └── TimelineStep (×N, live-updating via SSE)
│   └── EvidencePanel
│       ├── EvidenceTab
│       │   └── EvidenceItem (×N)
│       ├── ActionsTab
│       │   ├── InitialActions
│       │   ├── FinalActions
│       │   └── WhatChanged
│       ├── GraphTab
│       │   └── EntityGraph (graph visualization)
│       └── SimilarCasesTab
│           └── CaseReference (×N)
├── CaseResult
│   ├── CaseSummary
│   ├── EvidenceList
│   ├── SARSection
│   ├── ActionComparison
│   ├── GraphVisualization
│   └── InvestigationMetrics
└── ApprovalQueue
    └── ApprovalCard (×N)
```

## Visualization Libraries

| Need | Recommended |
|---|---|
| Graph visualization | `react-force-graph-2d` or `d3-force` (lightweight) |
| Charts/gauges | CSS-only or `recharts` |
| Timeline | Custom component (simple list) |
| Icons | `lucide-react` |

## Demo Flow (3–5 min)

1. **0:00–0:30** — Show case dashboard with 20 cases
2. **0:30–1:00** — Click "Investigate" on a risk_score case → watch timeline populate live
3. **1:00–2:30** — Agent gathers evidence, requests customer verification, reassesses, recommends actions
4. **2:30–3:30** — Show completed case result: evidence, SAR, actions comparison, graph
5. **3:30–4:00** — Show a customer_report case for contrast
6. **4:00–4:30** — Show approval queue, approve an L1 action
7. **4:30–5:00** — Architecture overview, case memory demonstration

## Screens NOT Needed for Hackathon

- User authentication / login
- Admin settings
- Notification center
- Full case management CRUD
- Report builder
- Detailed analytics dashboard
- User management

## Cross-References

- API endpoints consumed: [[API]]
- Evidence sources: [[Agent-Workflow]]
- Actions/approvals: [[Policy-Engine]]
