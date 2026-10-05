# Thematic Tracker — PRD

> Version: v1.0 · Status: Scaffold landed · Original Plan: [thematic-tracker-plan.md](./thematic-tracker-plan.md)

## 1. Product in One Line

A **theme-first site for PMs**: what are the most important market themes right now? How are they performing? What tracks them? Why did they form? What catalyst do they depend on? What changed yesterday vs today? Theme or noise?

Understand a theme in 5 minutes, decide without reading the explainer, dig deeper when you want to.

## 2. Users & Pain Points

Portfolio Managers, before the open / ahead of the weekly meeting, want to answer:

1. **What matters now?** Top 5 themes, new themes, whether yesterday's themes died or continued.
2. **How is it performing?** 1W / 1M / YTD performance and excess vs benchmarks (SPX / NDX / TSX Composite).
3. **How to track it?** Tradable, trackable, liquid proxies.
4. **Why now?** What re-priced? Which news / event triggered it? Timing + source are mandatory.
5. **What does it depend on?** Next checkpoint and falsification conditions.
6. **Theme or Noise?** Distilled from Weekly Commentary, not copied.

## 3. Product Principles

1. **Decision-first, not news-first**: every theme must answer So What + What Next.
2. **5-min rule**: a single theme's body reads in < 5min (~500 English words); explainers are folded by default and don't count.
3. **Timing is everything**: every news/event carries `UTC time + Source + Link`; no time or no source = unpublishable.
4. **Frontend/backend separation**: agents only touch `data/`, never frontend code. Separated by API contract + schema version.
5. **Dual-agent rule**: a second agent playing PM Reviewer must sign off before publish, hunting data errors and contradictions.
6. **English-only**: all content, prompts, docs, and UI strings are English. No Chinese characters in content, code, or docs (ASCII punctuation preferred; the em-dash and arrows used by the house style are allowed).

## 4. Information Architecture

- **Home / Today**
  - Market Regime in one line (risk-on/off + 3 keywords)
  - Active Themes (3–7), status = New / Continuing / Fading / Dead
  - Yesterday's Themes tracker: continued? strengthened? falsified?
  - Benchmark strip: SPX, NDX, TSX, 10Y, USD/CAD, Oil, Gold
- **Theme detail page** (fixed template; agents must not invent structure)
  1. Title + Status + Conviction (High/Med/Low) + Horizon (Tactical 2–8w / Cyclical 3–12m)
  2. Performance vs Benchmark (chart + table)
  3. Proxy to Track (1–3)
  4. Why Now / Thesis (re-pricing logic)
  5. Key Events / News Timeline
  6. Depends On / What to Watch (Next Catalyst + Bear case)
  7. Theme vs Noise verdict
  8. Explainer (expandable): terms, methods, data conventions
- **Archive / Weekly Commentary Digests**: the source library, fully traceable.

## 5. Technical Architecture

> Landed adjustment: frontend stack changed from the Plan's Next.js to **Vite + React + TypeScript + Tailwind + shadcn/ui** (local environment standard); the API contract is unchanged and the frontend still only reads `/api/*`. A static `index.html` renderer (same data via `data/latest.json`) serves the GitHub Pages edition.

```
general-theme-tracker/
├── PRD.md
├── thematic-tracker-plan.md      # original Plan
├── prompts/                      # versioned agent prompts
│   ├── theme_writer.md
│   ├── pm_reviewer.md
│   └── frontend_builder.md
├── data/                         # the agent's only writable area
│   ├── schema/theme.schema.yaml  # schema_v1
│   ├── themes/2026-W41/*.yaml    # weekly theme content
│   ├── market/snapshot_*.yaml    # Regime + Benchmark strip
│   ├── commentary/2026-W41.yaml  # Weekly Commentary source library
│   ├── archive/<YYYY-MM-DD>.json # published frozen snapshots
│   ├── latest.json               # latest published bundle (static renderer reads this)
│   └── reviews/*.yaml            # legacy reviewer reports (history only)
├── backend/                      # read-only API (Node, no framework)
│   ├── server.js
│   └── validate.js               # schema checks (CI)
├── index.html                    # static renderer for GitHub Pages (frozen; reads ./data/latest.json)
└── frontend/                     # Vite React, agents keep out
```

### API Contract (frontend-locked)

| Endpoint | Description |
|---|---|
| `GET /api/themes/active?date=YYYY-MM-DD` | Current Active Themes (excl. Dead) |
| `GET /api/themes/:id` | Full detail of one theme |
| `GET /api/themes/history?theme_id=` | Cross-week snapshots of a theme |
| `GET /api/market/snapshot` | Regime + Benchmark strip |
| `GET /api/commentary?week=2026-W41` | Commentary source library (Archive page) |

### Agent Update Flow

Only new `content_version` PRs into `data/` (yaml) are allowed; run `node backend/validate.js` for schema checks — merge only after they pass and the Reviewer signs PASS. The frontend re-renders automatically, no code changes.

## 6. Typography & Reading Rules (strict three tiers)

| Tier | Spec | Use |
|---|---|---|
| Title | 20–22px / 700 | One-line theme + status tag |
| Body | 15–16px / 400 / 1.6 line height | All decision content; over ~500 words gets sent back |
| Explainer | 13px / `#6B7280` / folded `<details>` by default | Conventions, terms, calculation details |

News timestamps use Monospace 13px inline in the timeline (not a new tier). Before publish, compute `word_count / 200wpm`; bodies over 5min auto-FAIL.

## 7. Performance vs Benchmark Rules

- Benchmark choice: US theme → SPX, Tech → SPX spread (QQQ vs SPX), Canada → S&P/TSX Composite; always state why.
- Windows: 1W / 1M / YTD + Since inception.
- Fields: `proxy_price, as_of_UTC, source, excess_return`.
- Chart: proxy vs benchmark rebased to 100.
- Forbidden: passing intraday prices off as closes; mixing Total Return / Price Return without labeling.
- Return conventions (documented in each theme's explainer): 1W = vs same-weekday prior-week close; 1M = vs same-date prior-month adjusted close; YTD = vs prior Dec 30 adjusted close (ETFs) / raw close (indexes). Price Return on Yahoo Finance closes.

## 8. Proxy Selection Rules

1–3 proxies per theme, prioritized: liquid ETF > Index > Basket (3–5 leaders with weights stated). Must include: ticker, fee, AUM/average volume, why it represents the theme, tracking flaws.

## 9. Why Now + Depends On Rules

**Why Now must answer the three re-pricing questions**: what was priced in before? Which event is the trigger? Consensus vs the marginal change?

**Depends On table**: next checkpoint / date (UTC) / why it matters / bull signal / bear falsification signal. A theme with no Next Catalyst is demoted to Noise.

## 10. Theme vs Noise Filter (a Theme needs ≥3)

1. Persistence > 2 weeks or cited across 2+ independent Commentaries
2. Breadth: ≥3 stocks / ≥2 sub-industries moving together
3. Price-volume confirmation: proxy excess + expanding volume
4. A falsifiable catalyst exists
5. Re-pricing logic, not a single-headline spike

State machine: `Emerging -> New -> Continuing -> Fading -> Dead`, with a one-line reason for every status change.

## 11. Dual-Agent Workflow

- **Agent A — Theme Writer**: runs weekly/daily, reads Commentary + market data, writes `data/themes/*.yaml` per schema_v1. Prompt: `prompts/theme_writer.md`.
- **Agent B — PM Reviewer (Gatekeeper)**: mandatory before publish; a harsh, skeptical PM persona that trusts only numbers and logic. Checklist: data accuracy / internal consistency / complete Timing+Source / 5-min readability / Theme-Noise calls / proxy tradability. Outputs `PASS / FAIL + issue list`; FAIL returns to Writer for at most 2 rounds, then demotes to Draft. Prompt: `prompts/pm_reviewer.md`; reports archived under `review/<date>/`.

## 12. Definition of Done

- Home reads in 5min: all Active Theme headlines + conclusions
- Single theme body < 5min, explainer folded but complete
- Every event click-traces to source with correct UTC time
- Frontend changes fully decoupled from data updates: agent PRs only touch `/data/`
- Reviewer reports archived and queryable; FAIL rate and edit history visible
- Daily Yesterday-vs-Today diff: added / continued / faded at a glance
- English-only: no non-English strings anywhere in content, UI, or docs

## 13. Local Run

```bash
npm install            # backend deps (frontend deps install separately inside frontend/)
npm run dev            # backend (:8787) + frontend (Vite) together
npm run validate       # check all theme YAMLs under data/ against schema_v1
```
