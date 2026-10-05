# Thematic Tracker: Product Plan + Copy-Paste Prompts

> Role: written for you from a Senior PM + Portfolio Manager double perspective.

## 1. Product in One Line

A **theme-first site for PMs**: what are the most important market themes right now? How are they performing? What tracks them? Why did they form? What catalyst do they depend on? What changed yesterday vs today? Theme or noise?

Understand a theme in 5 minutes, decide without reading the explainer, dig deeper when you want to.

---

## 2. User Stories / PM Pain Points

As a Portfolio Manager, before the open / ahead of the weekly meeting I want to answer:

1. **What matters now?** What are today's Top 5 themes? What's new? Did yesterday's themes die or continue?
2. **How is it performing?** Theme performance over 1W / 1M / YTD? Excess vs benchmarks (SPX / QQQ / TSX Composite)?
3. **How to track it?** What proxies exist? E.g. Canadian financials: `XFN.TO, ZEB.TO, S&P/TSX Capped Financials Index`. Must be tradable, trackable, liquid.
4. **Why now?** What re-priced? What news / event triggered it? Timing + Source are mandatory.
5. **What does it depend on?** What's the next checkpoint? Next Q earnings? Central bank meeting? Election? Data release? What if falsified?
6. **Theme or Noise?** Filter for me. Piles of Weekly Commentary are the best theme source — but distill, don't relay.

---

## 3. Product Principles

1. **Decision-first, not news-first:** every theme must answer So What + What Next, not just what happened.
2. **5-min rule:** a single theme's body reads in <5min (~500 English words). Explainers don't count but stay folded by default.
3. **Timing is everything:** every news/event carries `UTC time + Source + Link`; no time or no source = unpublishable.
4. **Frontend/backend separation:** agents only update `content / data` weekly, never touch `UI code`. Separated by API contract + schema version.
5. **Dual-agent rule:** a second agent playing Portfolio Manager Reviewer must sign off before publish, hunting data errors and contradictions.
6. **English-only:** all content, prompts, docs, and UI strings are English.

---

## 4. Information Architecture (IA)

**Home / Today:**
* Market Regime in one line (risk-on/off, 3 keywords)
* Active Themes (3–7): status = New / Continuing / Fading / Dead
* Yesterday's Themes tracker: continued? strengthened? falsified?
* Benchmark strip: SPX, NDX, TSX, 10Y, USD/CAD, Oil/Gold

**Theme detail page structure (fixed template — agents must not invent their own):**
1. Title + Status + Conviction (High/Med/Low) + Horizon (Tactical 2-8w / Cyclical 3-12m)
2. Performance vs Benchmark (chart + table)
3. Proxy to Track (1–3)
4. Why Now / Thesis (re-pricing logic)
5. Key Events / News Timeline
6. Depends On / What to Watch (Next Catalyst + Bear case)
7. Theme vs Noise verdict
8. Explainer (smaller, expandable): terms, methods, data conventions

**Archive / Weekly Commentary Digests:** the raw source library, traceable.

---

## 5. Backend Design: Keeping Weekly Updates Clean

**Core principle: frontend only reads the API, agents only write the Content DB.**

DB Tables:

```text
themes(id, title, status, conviction, horizon, thesis_summary, created_at, updated_at, schema_v=1)
theme_perf(theme_id, date, ret_1w, ret_1m, ret_ytd, benchmark_ticker, excess_1w, data_as_of_utc)
proxies(id, theme_id, ticker, name, type[ETF/Index/Basket], region, expense, liquidity_note)
events(id, theme_id, event_time_utc, title, source, url, type[macro/earnings/policy/geopolitics])
catalysts(id, theme_id, due_date, event_name, why_matters, if_bull, if_bear)
commentary_sources(id, week, firm, url, key_takeaway)
reviews(theme_id, reviewer_version, pass_fail, issues[])
```

API Contract (frontend-locked):
* `GET /api/themes/active?date=YYYY-MM-DD`
* `GET /api/themes/:id`
* `GET /api/themes/history?theme_id=`

> Agent update flow: only new `content_version` PRs into `data/` (yaml/json) are allowed; CI schema validation must pass plus Reviewer PASS before merge; the frontend re-renders automatically, no code changes.

File separation:
```
/frontend/  # Next.js / React, agents keep out
/backend/   # API + DB
/data/themes/2026-W41/theme_xxx.yaml  # the agent's only writable area
/prompts/   # versioned agent prompts
```

---

## 6. Typography & Reading Rules (strict three tiers)

Only three classes allowed:

* **Title:** 20–22px, 700, one-line theme + status tag. E.g. `Canadian Bank Earnings Momentum [Continuing | High Conviction]`
* **Body:** 15–16px, 400, 1.6 line height. Carries all decision content. Over ~500 words gets sent back.
* **Explainer:** 13px, gray `#6B7280`, folded `<details>` by default. Explains conventions, terms, calculation details. Skippable, but complete when opened.

Body text must not introduce a fourth size/color or abuse bold. News timestamps use `Monospace 13px` inside the body timeline but don't count as a new tier.

Reading-time check: before publish compute `word_count / 200wpm`; bodies over 5min auto-FAIL.

---

## 7. Performance vs Benchmark Rules

Every theme must have:

* Benchmark logic: US theme → SPX, Tech → SPX spread (QQQ vs SPX), Canada → S&P/TSX Composite — always state why.
* Windows: 1W / 1M / YTD + Since theme inception
* Data fields: `Proxy price, as_of_UTC, source (Yahoo/CapitalIQ/Bloomberg), excess return`
* Chart: proxy vs benchmark rebased to 100
* Forbidden: passing intraday prices off as closes; mixing Total Return / Price Return without labeling.

Example: `ZEB.TO +8.2% 1M vs TSX +2.1%, excess +6.1pp, as of 2026-10-03 close, Source: TMX`

---

## 8. Proxy Selection Rules

1–3 proxies per theme, prioritized:
1. Liquid ETF (e.g. Canadian financials `ZEB.TO, XFN.TO`)
2. Index (e.g. `S&P/TSX Capped Financials`)
3. Basket (3–5 leaders with weights stated)

Must include: ticker, fee, AUM/average volume, why it represents this theme, tracking flaws.

---

## 9. Why Now + Depends On Rules

**Why Now must answer the three re-pricing questions:**
* What was priced in before? Why is it wrong now?
* Which event is the trigger (Earnings / Macro / Policy)?
* Consensus vs your marginal change?

**Depends On / What to Watch table:**

| Next checkpoint | Date (UTC) | Why it matters | What bulls see | Bear / falsification signal |
|---|---|---|---|---|
| E.g. RY/BMO Q3 earnings | 2026-XX-XX | NIM/credit losses | ... | ... |

A theme with no Next Catalyst is demoted to Noise.

---

## 10. Theme vs Noise Filter (Reviewer checks hardest)

A theme needs ≥3 of the following, otherwise it's Noise and stays off Home:

1. Persistence > 2 weeks or cited across 2+ independent Commentaries
2. Breadth: ≥3 stocks / ≥2 sub-industries moving together
3. Price-volume confirmation: proxy excess + expanding volume
4. A falsifiable catalyst exists
5. Re-pricing logic, not a single-headline spike

State machine: `Emerging -> New -> Continuing -> Fading -> Dead`, with a one-line reason for every status change.

Weekly Commentary is the main input: Goldman/BofA/MS/JPM/DB + BMO/RBC/TD swept every week — distill the disagreements, don't summarize.

---

## 11. Dual-Agent Workflow (key: prevent data errors)

### Agent A - Theme Writer (Updater)

> Runs weekly/daily, reads Commentary + market data, writes `data/themes/*.yaml` per schema.

### Agent B - Portfolio Manager Reviewer (Gatekeeper)

Must run before publish; no publish without a pass. Reviewer persona: harsh, skeptical PM that trusts only numbers and logic.

**Review checklist (hard):**
1. Data errors? Do prices/dates/gains match the source? Is as_of stale?
2. Contradictions? Thesis says bullish but catalysts read bearish? High conviction on weak proxies?
3. Missing Timing/Source? Every event with UTC + Link?
4. Over 5min? Body too long?
5. Theme/Noise misjudged?
6. Proxy untradable? Thin liquidity gets sent back.

Output: `PASS / FAIL + issue list + fix suggestions`. FAIL returns to Writer for at most 2 rounds; a second-round FAIL demotes to Draft, unpublished.

---

## 12. Copy-Paste Prompts

### Prompt 1: Theme Writer

```text
You are a buy-side Thematic Analyst.

Input: weekly commentaries [links], market data as_of_UTC {date}, existing themes status.

Task: Output 3-7 themes in YAML following schema_v1. Each theme MUST include:
- title, status, conviction, horizon
- performance: proxy_ticker, ret_1w/1m/ytd, benchmark, excess, as_of_UTC, source
- proxies[1-3] with liquidity note
- thesis: priced_in_before vs repricing_now (max 150 words)
- events[]: each with event_time_UTC, source, url
- depends_on[]: next catalyst with due_date, bull/bear case
- theme_vs_noise_score (5 criteria)
- body_text under 500 English words, explainer separate

Constraints:
- 3 font classes only. Body <5min read.
- No event without time+source.
- No forward-looking claim without catalyst.
- Language: English only, concise, PM tone.
```

### Prompt 2: PM Reviewer (Gatekeeper)

```text
You are a skeptical Portfolio Manager reviewer. Your job is to BLOCK bad publishing.

Review the theme YAML. Check:
1. Data accuracy: recalc excess = proxy - benchmark. Flag mismatch >0.2pp. Check as_of freshness <48h.
2. Logic consistency: Does thesis match proxies? Does conviction match evidence? Bull/bear symmetric?
3. Completeness: Every event has event_time_UTC + source URL? Next catalyst dated?
4. Readability: body_text reading time <5min? No jargon without explainer?
5. Theme vs Noise: Does it meet >=3 criteria? If not, suggest demote to Noise.

Output JSON: {verdict: PASS/FAIL, issues: [{severity: blocker/major/minor, location, reason, fix}], summary_1line}
If FAIL blocker exists, DO NOT approve. Be harsh.
```

### Prompt 3: Frontend Builder (isolation)

```text
Build a read-only frontend that ONLY consumes /api/themes/*.
- Stack: Next.js + Tailwind.
- Typography: Title 21px/700, Body 15.5px/1.6, Explainer 13px gray in <details>.
- Theme card shows: status pill, perf table, proxy tickers, timeline with UTC+source link, Depends On table.
- Never fetch raw YAML. Never hardcode theme content.
- Reading progress bar + ~X min label computed from body_text.
```

---

## 13. Definition of Done

* Home reads in 5min: all Active Theme headlines + conclusions
* Single theme body <5min, explainer folded but complete
* Every event click-traces to source with correct UTC time
* Frontend changes fully decoupled from data updates: agent PRs only touch `/data/`
* Reviewer reports archived and queryable; FAIL rate and edit history visible
* Daily Yesterday-vs-Today diff: added/continued/faded at a glance
* English-only output throughout
