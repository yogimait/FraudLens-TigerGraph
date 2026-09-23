# UI — Analyst Dashboard

> [[Home]] · [[API]] · [[Architecture]]

## Design Goal

A fraud analyst dashboard that makes the agent's investigation **visible, understandable, and actionable**. It is designed with a Bloomberg-terminal aesthetic, prioritizing data density, dark mode, high-contrast indicators, and futuristic typography (`Space Grotesk`). 

## Application Pages & Routing

The application is built using Next.js App Router with the following structure:

### 1. Case Dashboard (`/`)

**Purpose**: Central hub and overview of all investigations.
- **Key Features**: 
  - Real-time KPIs (Total Cases, In Progress, Awaiting Approval, Uncertain, Closed Fraud, Closed Legitimate) — no fabricated trend percentages.
  - Trend charts and Case outcome donut (using `recharts`), donut segments filtered to non-zero real stats (includes Uncertain).
  - "Agent Activity" card with honest aggregates computed from case metadata (avg `duration_seconds`, total `tool_calls`) or an em-dash when no data.
  - Searchable, filterable data table of all cases showing Fraud Probability, Exposure, and Status.
  - "New Investigation" manual trigger modal for testing arbitrary transactions.

### 2. Investigation View (`/cases/:id`)
**Purpose**: Detailed view of a single case investigation and the agent's findings.
- **Layout**: Tabbed interface to organize dense information:
  - **Overview**: Core case metadata (first suspicious txn, tool calls/tokens, written-to-graph + `graph_case_id`), exposure, Jev classification, verdict chip (fraud = red, legitimate = emerald, **uncertain = purple with an "uncertain is a valid verdict" tag**), plus chips for `connected_card_ids`, `connected_device_profiles`, and `similar_prior_cases` (linked).
  - **Graph View**: Interactive node-link visualization of the transaction's neighborhood (Card, Device, other Transactions) using custom styled `@xyflow/react` nodes.
  - **Evidence & Analysis**: Synthesis summary plus citation cards for each evidence item — source badge with icon (graph=`Network`, document=`FileText`, customer=`User`, external=`Globe`), claim text, `ref` as mono chip, `entity_ids` as small chips — and an evidence-requests timeline (`type`, `asked_after_step`, `assumed_response`).
  - **Policy Actions**: Initial vs final actions with route badges (auto=green `AUTO`, L1=amber, L2=red), reason shown, `auto`-routed actions marked "Executed by agent", and the `what_changed` comparison line.
  - **SAR Report**: If the policy engine files a SAR, shows reason, subjects, `total_amount_usd`, `activity_dates`, and the drafted narrative.

### 3. Global Graph Explorer (`/graph`)
**Purpose**: Macro-level view of the entire financial network across all loaded benchmark cases.
- **Key Features**: Renders the complete node/edge dataset fetched from TigerGraph. Uses a hierarchical grouping layout (clustering transactions under cards) to prevent visual chaos, featuring interactive custom nodes, smoothstep edges, and a comprehensive legend.

### 4. Approvals Queue (`/approvals`)
**Purpose**: Dedicated workspace for analysts to review L1/L2 escalated actions.
- **Layout**: Two-pane split:
  - **Queue (Left)**: Scrollable list of cases requiring manual sign-off, each showing the derived required level (`L1` amber / `L2` red).
  - **Detail (Right)**: Context on why execution halted, proposed final actions with route badges, and input for Analyst Justification notes.
- **Behavior**: Submits the case's required approval level (derived from final actions — same rule as backend `requiredApprovalLevel`); backend rejects lower-level approvals with 409. Empty state shown when nothing is awaiting approval.

### 5. Analytics & Reports (`/analytics`, `/reports`)
**Purpose**: High-level operational intelligence.
- **Analytics**: Deep dive into agent performance, resolution times, accuracy metrics, and time-series charts.
- **Reports**: Downloadable SARs. "Export All" downloads every SAR narrative as a single `.txt` (dead Filter button removed).

### 6. Investigation Archive (`/memory`)
**Purpose**: Honest search over case memory (client-side over `GET /cases`).
- Retitled from "Case Memory" to "Investigation Archive" (no fabricated GraphRAG/semantic-search claim).
- Keyword search with pattern/summary/verdict filters; each result shows the matched field instead of fabricated relevance scores, plus `similar_prior_cases` chips when present.

## Component Hierarchy

```
App (layout.tsx)
├── Sidebar (Global Navigation)
└── Main Content Area
    ├── Page: Dashboard (/)
    │   ├── KPI Cards
    │   ├── Recharts (LineChart, PieChart)
    │   └── Case Table
    ├── Page: Investigation View (/cases/[id])
    │   ├── Case Header (Status Badges, Metadata)
    │   └── Tabs
    │       ├── OverviewTab
    │       ├── GraphViewTab (EvidenceGraph)
    │       ├── EvidenceTab
    │       ├── PolicyActionsTab
    │       └── SARTab
    ├── Page: Graph Explorer (/graph)
    │   └── EvidenceGraph (Custom React Flow)
    ├── Page: Approvals (/approvals)
    │   ├── QueueList
    │   └── DetailPane (Approval/Reject actions)
    └── Page: Analytics (/analytics)
```

> Sidebar identity is generic ("Analyst / Fraud Investigation") — no fictional user persona. Settings persist TigerGraph host/graph name and policy thresholds to `localStorage` and load them on mount.

## Visualization Libraries

| Need | Library | Rationale |
|---|---|---|
| **Graph Visualization** | `@xyflow/react` (React Flow) | Provides robust interactive node rendering, custom node types, drag/drop physics, minimaps, and zooming. Far superior for structured, labeled entity graphs than raw force-directed layouts. |
| **Charts/Gauges** | `recharts` | Clean, composable React components for SVG charts (Line, Pie, Bar). |
| **Icons** | `lucide-react` | Consistent, modern, stroke-based iconography used across the app. |
| **Styling** | `TailwindCSS` | Rapid styling with custom tokens (e.g., `bg-background`, `text-primary`) supporting native dark mode. |
| **Animations** | `framer-motion` | Page transitions, staggering list animations, and micro-interactions. |

## Aesthetic Principles

- **Bloomberg Style**: Dense data presentation without sacrificing readability.
- **Vibrant Signifiers**: Statuses use highly distinct colors (Emerald for Legitimate, Red for Fraud, Amber for Investigating, Purple for Awaiting Approval) on top of a dark, low-contrast background (`#0A0D14`).
- **Micro-Animations**: Hover states, list item staggers, and button interactions provide immediate tactile feedback.

## Cross-References
- API endpoints and case schema: [[API]]
- Evidence sources: [[Agent-Workflow]]
- Actions/approvals: [[Policy-Engine]]

## Graph Visualization v2 (Obsidian-style)

The EvidenceGraph component ([[UI]] ? Graph Explorer and case detail) was rewritten from a hand-rolled card grid to an Obsidian-style force-directed graph view.

### Layout
- Node positions are computed with a synchronous d3-force simulation (run once per data change inside useMemo, 300 ticks, deterministic � no animation loop):
  - orceLink distance 120, orceManyBody charge -300, orceCenter, gentle orceCollide (radius + 8). No X/Y pinning, so connected entities cluster naturally.
- Nodes are capped at 300; overflow shows a "+N more nodes hidden" note (bottom-left panel).

### Node Rendering
- Circular nodes sized by importance: transactions scale with amount (sqrt), cards/devices render larger.
- Color by type: card = sky blue, transaction = emerald green, high-value transaction (> \,000) = red, device = amber, case memory = violet.
- Labels render under nodes, truncated to 14 characters.

### Interactions
- Hover: active node gets a colored ring/glow, neighbors stay full opacity, all others fade to 15%, connected edges highlight.
- Click pins the selection and opens a detail panel (top-right) with label, type, and amount; click background or X to clear.
- React Flow Controls (zoom/fit), dark dotted Background, pan/zoom via drag and scroll.

### Dependencies
| Package | Purpose |
|---|---|
| d3-force (+ @types/d3-force dev) | Deterministic force-directed layout calculation |
| @xyflow/react | Renderer: pan/zoom, controls, edges, background |

---

## Stitch Design Concept � "Ops Terminal" (2026-09-23)

A modern redesign proposal was generated in Stitch (project: **FraudLens � Fraud Investigation Ops Intelligence**, id 11901817799930596120) as the target direction for the next UI iteration. It is NOT yet implemented in the Next.js app; the current app remains as described above.

### Design direction (Bloomberg terminal � Linear)

- Canvas #0A0D14, panels #10151F, hairline borders, flat, 8px radius, accent #38BDF8.
- Semantic colors, one meaning one color: emerald = legitimate/AUTO, red = fraud/L2, amber = L1/investigating, violet = uncertain/awaiting approval/case memory.
- Space Grotesk display numbers, Inter body, JetBrains Mono for IDs/amounts/rule citations.
- **Calibration bars**: every fraud probability rendered with policy threshold ticks at 0.30 (case) and 0.70 (block) � makes the deterministic policy thresholds legible in the UI.
- **Verdict chips** treat UNCERTAIN as a first-class valid verdict (violet glow).
- **Route badges** AUTO/L1/L2 always visible on action rows.
- **Evidence provenance icons** (graph/document/customer/external) per citation.
- Empty chart states show a faint grid + label, never blank.

### Stitch screens generated (desktop)

| Screen | Purpose |
|---|---|
| Command Center | KPI strip (Total, In Progress, Awaiting Approval, Uncertain, Closed Fraud), Triage Queue table with calibration bars + route badges, verdict distribution, agent activity feed |
| Case Investigation (3 variants) | 3-pane: case facts + case memory � agentic investigation timeline (trigger ? MCP tool calls ? evidence with provenance ? evidence request ? reassessment ? policy) � decision panel with UNCERTAIN verdict, calibration bar, initial vs final actions, what_changed |

Pending in the Stitch queue at time of writing: Graph Explorer (Obsidian-style), Approvals Center, SAR view. Screens can be regenerated or refined on request.

See [[Demo-Video]] for the narrated walkthrough that pairs with these screens.
