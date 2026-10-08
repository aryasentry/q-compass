# Additive Next.js interface

Approved intent: the user asked to create a separate Next.js frontend and route it to the existing engine. The existing Streamlit application must not be deleted or edited.

## Architecture

- Keep `app/` and `.streamlit/` byte-for-byte unchanged; Streamlit remains at 127.0.0.1:8501.
- Add `frontend/` as a standalone Next.js App Router / TypeScript application at 127.0.0.1:3000.
- Add `src/qcompass/api/` as a thin FastAPI service at 127.0.0.1:8000. It uses the existing snapshot loaders, result checksum verification, RunConfig and JobStore/worker.
- Route same-origin `/api/*` requests through a constrained Next.js route handler to FastAPI. Do not expose arbitrary upstream URLs, filesystem paths, shell commands, trading or raw data downloads.
- New and old interfaces share the existing SQLite queue and exclusive worker lock. Mutations require an explicit UI action, idempotency key and same-origin/custom-header checks. GET never starts a simulation or download.

## Product

Routes: `/` overview of latest saved optimization run; `/experiments` saved runs and queue; `/experiments/new` configuration; `/experiments/[id]` results, controller evidence and run record; `/data` snapshot audit; `/methodology` beginner explanation and limitations. The sidebar also links to the untouched Streamlit UI.

All numerical content comes from verified local snapshots or saved real runs. Empty, offline, corrupted and failed states show explicit explanations, never substitute demo results. Dataset provenance identifies Yahoo as secondary and the official NSE cross-check as single-session only. Selection and allocation feasibility stay separate. Historical membership and market-aware training limitations remain visible.

## Design

Use the built-in image-generated reference at `docs/design/nextjs/concept.png`; it is a visual reference only, never shipped as interactive UI. Main background #f8faf9, forest navigation #172c25, ink #17241f, lime accent #c5eb9b, subtle borders #dde5df. Native concept is 1505x1045. Approximate 252px sidebar with remaining area for open metrics, solver table and allocation. Manrope-style sans typography, 38–44px heading, 14–15px body and table, 12px captions, modest 10px corners. Lucide outline icons only for real navigation/actions. No gradients or decorative finance imagery. Bar charts are code-native with actual weights, accessible labels and non-color equivalents.

Allowed primary copy: Q-Compass; Workspace / Overview; Local engine; Experiment overview; Real market data. Reproducible quantum experiments.; New experiment; Overview; Experiments; Data sources; Methodology; Open Streamlit; Simulation only; Stock histories; Validated daily records; Candidates → holdings; Solver comparison; Investment allocation; The adaptive decision; View evidence; Download CSV; Research, not a quantum-advantage claim. Dynamic dates, seed, run identifiers and values must be actual API data. Necessary deviations: real validity split into selection and weights; functional run selector/details tabs; no unimplemented settings gear. Mobile uses top navigation, single-column content and horizontally scrollable tables.

## Acceptance

Both services and Streamlit remain healthy. New interface loads authentic counts, opens real saved runs, displays weights/controller decisions, submits a real 8-stock job, reports terminal state, supports cancellation, and replays without duplicate submission. Export verifies source result checksum first. Invalid inputs, missing/corrupt data, idempotency conflicts and cross-origin writes are rejected. API tests and existing Python suite pass; TypeScript checks and production Next build pass; desktop/mobile browser inspection and interaction tests pass. Record before/after Streamlit SHA256.
