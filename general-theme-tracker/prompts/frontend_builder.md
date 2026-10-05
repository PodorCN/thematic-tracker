# Prompt: Frontend Builder (isolation)

> Version v1 · Frontend only reads the API; routine agent updates must NOT touch `frontend/`

```text
Build a read-only frontend that ONLY consumes /api/themes/*.
- Stack: Next.js + Tailwind.
- Typography: Title 21px/700, Body 15.5px/1.6, Explainer 13px gray in <details>.
- Theme card shows: status pill, perf table, proxy tickers, timeline with UTC+source link, Depends On table.
- Never fetch raw YAML. Never hardcode theme content.
- Reading progress bar + ~X min label computed from body_text.
```

## Landed Notes (v1.1)

- Actual stack is **Vite + React + TypeScript + Tailwind + shadcn/ui** (local environment standard, replacing Next.js); all other constraints stand.
- API contract: PRD.md §5 — `/api/themes/active`, `/api/themes/:id`, `/api/themes/history`, `/api/market/snapshot`, `/api/commentary`.
- Hard three-tier typography: Title 21px/700; Body 15.5px/1.6; Explainer 13px `#6B7280` folded; timeline Monospace 13px. No fourth size/color.
- All content changes must come from `data/` updates; hardcoding content in the frontend is forbidden.
- English-only: every UI string is English.

## Landed Notes (v1.2, GitHub Pages edition)

- `index.html` at the product root is a frozen static renderer that reads `./data/latest.json` (written by publish, bytes == reviewed candidate). It mirrors the Vite app's content contract: regime line, benchmark strip, theme cards, perf tables, timelines, catalyst tables.
- `index.html` is frontend: routine data PRs must not touch it; changes ship in a standalone frontend PR with an updated `frontend_contract.json` digest.
