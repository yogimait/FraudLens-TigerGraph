# UI — Analyst Dashboard

> [[Home]] · [[API]] · [[Architecture]]

## Design Goal

A fraud analyst dashboard that makes the agent's investigation **visible, understandable, and actionable**. It is designed with a Bloomberg-terminal aesthetic, prioritizing data density, dark mode, high-contrast indicators, and futuristic typography (`Space Grotesk`). 

## Application Pages & Routing

The application is built using Next.js App Router with the following structure:

### 1. Case Dashboard (`/`)
**Purpose**: Central hub and overview of all investigations.
- **Key Features**: 
  - Real-time KPIs (Total Cases, Pending, Escalated).
  - Trend charts and Case outcome pie charts (using `recharts`).
  - Searchable, filterable data table of all cases showing Fraud Probability, Exposure, and Status.
  - "New Investigation" manual trigger modal for testing arbitrary transactions.

### 2. Investigation View (`/cases/:id`)
**Purpose**: Detailed view of a single case investigation and the agent's findings.
- **Layout**: Tabbed interface to organize dense information:
  - **Overview**: Core case metadata, reasoning summary, exposure, and a breakdown of the Jev classification vs. LLM Assessment.
  - **Graph View**: Interactive node-link visualization of the transaction's neighborhood (Card, Device, other Transactions) using custom styled `@xyflow/react` nodes.
  - **Evidence & Analysis**: The exact facts collected by TigerGraph and evaluated by the LLM.
  - **Policy Actions**: Deterministic output from the Policy Engine, detailing what actions are recommended vs auto-executed.
  - **SAR Report**: If the policy engine determines a Suspicious Activity Report is required, the drafted narrative is displayed here.

### 3. Global Graph Explorer (`/graph`)
**Purpose**: Macro-level view of the entire financial network across all loaded benchmark cases.
- **Key Features**: Renders the complete node/edge dataset fetched from TigerGraph. Uses a hierarchical grouping layout (clustering transactions under cards) to prevent visual chaos, featuring interactive custom nodes, smoothstep edges, and a comprehensive legend.

### 4. Approvals Queue (`/approvals`)
**Purpose**: Dedicated workspace for analysts to review L1/L2 escalated actions.
- **Layout**: Two-pane split:
  - **Queue (Left)**: Scrollable list of cases requiring manual sign-off.
  - **Detail (Right)**: Context on why execution halted, proposed final actions, and input for Analyst Justification notes.

### 5. Analytics & Reports (`/analytics`, `/reports`)
**Purpose**: High-level operational intelligence.
- **Analytics**: Deep dive into agent performance, resolution times, accuracy metrics, and time-series charts.
- **Reports**: Downloadable snapshots of investigations and system throughput.

### 6. Case Memory (`/memory`)
**Purpose**: Transparency into the agent's long-term memory store.
- Displays chronological logs of all completed investigations, allowing analysts to see how past cases influence future LLM reasoning.

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
- API endpoints consumed: [[API]]
- Evidence sources: [[Agent-Workflow]]
- Actions/approvals: [[Policy-Engine]]
