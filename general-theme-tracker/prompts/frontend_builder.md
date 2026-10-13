# Prompt: Frontend Builder (isolation)

> Version v1 · Frontend only reads the API; routine agent updates must NOT touch `frontend/`

```text
Build a read-only frontend that ONLY consumes /api/themes/*.
- Stack: Next.js + Tailwind.
- Typography: Title 21px/700, Body 15.5px/1.6 (2min core <=200 words), Explainer 13px gray in <details> (up to 5min total folded).
- Date banner at the very top of every page: Week + snapshot_date + data as_of_UTC + Toronto today, with Updated-today / Stale indicator.
- Home shows a Theme Board table (yesterday→today change, proxy, 1W/1M/YTD excess, next checkpoint, noise score), then one identical one-minute card per theme: header (status pill, conviction, horizon, since-date, noise score) + title + one-line status_note; formation chain as numbered boxes joined by arrows (date + plain-English label + one-sentence detail per step) with the last step highlighted as Now; proxy / benchmark / excess table (1W/1M/YTD) + rebased sparkline; next-2-checkpoints table (date / checkpoint / holds if / breaks if); proxy tickers. Summary, thesis, timeline with UTC+source link + proxy return vs benchmark return, and the full Depends On table live in the detail view.
- Never fetch raw YAML. Never hardcode theme content.
- No reading-time labels, no reading progress bar — do not display `~X min` anywhere (the 2min/5min rule is enforced by validation, not shown in UI).
```

## Landed Notes (v1.1)

- Actual stack is **Vite + React + TypeScript + Tailwind + shadcn/ui** (local environment standard, replacing Next.js); all other constraints stand.
- API contract: PRD.md §5 — `/api/themes/active`, `/api/themes/:id`, `/api/themes/history`, `/api/market/snapshot`, `/api/commentary`.
- Hard three-tier typography: Title 21px/700; Body 15.5px/1.6 (2min core); Explainer 13px `#6B7280` folded (up to 5min total); timeline Monospace 13px. No fourth size/color.
- Key Events render proxy return vs benchmark return for the same window; date banner is mandatory at the very top.
- All content changes must come from `data/` updates; hardcoding content in the frontend is forbidden.
- English-only: every UI string is English.

## Landed Notes (v1.2, GitHub Pages edition)

- `index.html` at the product root is a frozen static renderer that reads `./data/latest.json` (written by publish, bytes == reviewed candidate). It mirrors the Vite app's content contract: regime line, benchmark strip, theme cards, perf tables, timelines, catalyst tables.
- `index.html` is frontend: routine data PRs must not touch it; changes ship in a standalone frontend PR with an updated `frontend_contract.json` digest.
