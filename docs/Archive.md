# Archive

Investigation Archive page (`frontend/app/memory/page.tsx`) — searchable case memory over all closed/escalated investigations.

## Behavior

- Default view: **Recent Investigations** — top 6 cases sorted by `updatedAt` descending, shown immediately on load. No search needed to see content.
- Search: filters `allCases` client-side on pattern, summary, pattern_description, case_id; optional verdict filter (fraud/legitimate/uncertain). Each result shows matched field, verdict badge, similar prior cases (clickable, links to `/cases/{id}`).
- Data source: `GET /cases` (backend) → Mongo `investigationcases`.

## Gotchas

- Timestamps come from Mongo `createdAt`/`updatedAt` (Mongoose `timestamps: true`). They only exist when docs are written through the backend. [[sync_mongo_from_answers]] bypasses Mongoose, so after a sync run the dates must be backfilled from `metadata.generated_at` — otherwise cards render "Invalid Date".
- Case cards render defensively when `updatedAt` is missing (date simply omitted).

## Links

- [[Demo-Video]] — Act 5 shows this page (SAR → Archive + live search).
- [[Agent-Workflow]] — investigations write case memory to Mongo and TigerGraph.
