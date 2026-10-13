// Schema v1 validator — agents must run it before merging a PR (CI gate)
// Usage: node backend/validate.js
// Exit code: 0 = all pass; 1 = any FAIL

const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

const DATA_DIR = path.join(__dirname, '..', 'data');
const STATUS = ['Emerging', 'New', 'Continuing', 'Fading', 'Dead'];
const CONVICTION = ['High', 'Med', 'Low'];
const HORIZON = ['Tactical 2-8w', 'Cyclical 3-12m'];
const EVENT_TYPES = ['macro', 'earnings', 'policy', 'geopolitics'];
const PROXY_TYPES = ['ETF', 'Index', 'Basket'];

let failures = 0;

function fail(file, msg) {
  failures++;
  console.error(`  ✗ [${file}] ${msg}`);
}
function ok(file, msg) {
  console.log(`  ✓ [${file}] ${msg}`);
}

function bodyStats(s) {
  // English-only product: any CJK char is a blocking violation; legacy caliber 500 words = 5min (100wpm), so 200 words = 2min core
  const cjk = (s.match(/[一-鿿]/g) || []).length;
  const words = (s.replace(/[一-鿿]/g, ' ').match(/\S+/g) || []).length;
  return { cjk, words };
}

function validateTheme(file, t) {
  const name = path.basename(file);
  const req = ['schema_v', 'id', 'week', 'title', 'status', 'status_note', 'conviction', 'horizon', 'created_at', 'updated_at', 'data_quality', 'summary', 'chain', 'body_text', 'performance', 'series', 'proxies', 'events', 'depends_on', 'theme_vs_noise'];
  for (const k of req) if (t[k] === undefined) fail(name, `missing required field: ${k}`);

  if (t.schema_v !== 1) fail(name, `schema_v must be 1, got ${t.schema_v}`);
  if (t.id && !/^[a-z0-9-]+$/.test(t.id)) fail(name, `id must be slug: ${t.id}`);
  if (t.week && !/^\d{4}-W\d{2}$/.test(t.week)) fail(name, `week format: ${t.week}`);
  if (t.status && !STATUS.includes(t.status)) fail(name, `bad status: ${t.status}`);
  if (t.conviction && !CONVICTION.includes(t.conviction)) fail(name, `bad conviction: ${t.conviction}`);
  if (t.horizon && !HORIZON.includes(t.horizon)) fail(name, `bad horizon: ${t.horizon}`);

  // chain: formation arc for Home cards (3-5 steps, label <=12w + plain-English detail <=30w, no new claims)
  if (Array.isArray(t.chain)) {
    if (t.chain.length < 3 || t.chain.length > 5) fail(name, `chain count ${t.chain.length} not in 3-5`);
    t.chain.forEach((s, i) => {
      if (!s || typeof s.label !== 'string' || !s.label.trim()) fail(name, `chain[${i}].label missing`);
      else {
        const w = (s.label.replace(/[一-鿿]/g, ' ').match(/\S+/g) || []).length;
        if (/[一-鿿]/.test(s.label)) fail(name, `chain[${i}].label has non-English char(s) — English-only`);
        if (w > 12) fail(name, `chain[${i}].label ${w} words > 12`);
      }
      // when: short human date for the step (<=20 chars), so the chain reads as a timeline
      if (!s || typeof s.when !== 'string' || !s.when.trim()) fail(name, `chain[${i}].when missing`);
      else {
        if (/[一-鿿]/.test(s.when)) fail(name, `chain[${i}].when has non-English char(s) — English-only`);
        if (s.when.length > 20) fail(name, `chain[${i}].when ${s.when.length} chars > 20`);
      }
      // detail: the plain-English sentence under each step (<=30w)
      if (!s || typeof s.detail !== 'string' || !s.detail.trim()) fail(name, `chain[${i}].detail missing`);
      else {
        const dw = (s.detail.replace(/[一-鿿]/g, ' ').match(/\S+/g) || []).length;
        if (/[一-鿿]/.test(s.detail)) fail(name, `chain[${i}].detail has non-English char(s) — English-only`);
        if (dw > 30) fail(name, `chain[${i}].detail ${dw} words > 30`);
      }
    });
  }
  // summary: pre-click overview (<=100w, must carry the proxy vs benchmark picture)
  if (t.summary !== undefined) {
    const { cjk: scjk, words: swords } = bodyStats(String(t.summary));
    if (scjk > 0) fail(name, `summary has ${scjk} non-English char(s) — English-only`);
    if (swords > 100) fail(name, `summary ${swords} words > 100 (pre-click overview budget)`);
  }
  // 2-min core (<=200w) + up to 5min folded (body+explainer <=500w) + English-only
  if (t.body_text) {
    const { cjk, words } = bodyStats(t.body_text);
    if (cjk > 0) fail(name, `body_text has ${cjk} non-English char(s) — English-only`);
    if (words > 200) fail(name, `body_text ${words} words > 200 (>2min core)`);
    const expl = typeof t.explainer === 'string' ? t.explainer : '';
    const explWords = (expl.replace(/[一-鿿]/g, ' ').match(/\S+/g) || []).length;
    if (words + explWords > 500) fail(name, `body+explainer ${words + explWords} words > 500 (>5min total)`);
    if (!/what happened|so what|gained|fell|rose|surged|dropped|closed|record|down|up\b/i.test(t.body_text) && words > 0) {
      // soft hint only — reviewer enforces what-happened; machine does not block on phrasing
    }
  }
  for (const k of ['title', 'status_note', 'summary', 'explainer']) {
    if (typeof t[k] === 'string' && /[一-鿿]/.test(t[k])) fail(name, `${k} has non-English char(s) — English-only`);
  }

  // performance & excess recheck (reviewer rule: mismatch >0.2pp sent back)
  const p = t.performance;
  if (p) {
    for (const k of ['ret_1w', 'ret_1m', 'ret_ytd', 'benchmark_ret_1w', 'benchmark_ret_1m', 'benchmark_ret_ytd', 'excess_1w', 'excess_1m', 'excess_ytd', 'proxy_price']) {
      if (typeof p[k] !== 'number') fail(name, `performance.${k} must be number`);
    }
    for (const [excess, ret, bret] of [['excess_1w', 'ret_1w', 'benchmark_ret_1w'], ['excess_1m', 'ret_1m', 'benchmark_ret_1m'], ['excess_ytd', 'ret_ytd', 'benchmark_ret_ytd']]) {
      if (typeof p[excess] === 'number' && typeof p[ret] === 'number' && typeof p[bret] === 'number') {
        const diff = Math.abs(p[excess] - (p[ret] - p[bret]));
        if (diff > 0.2) fail(name, `excess mismatch: ${excess}=${p[excess]} vs ${ret}-${bret}=${(p[ret] - p[bret]).toFixed(2)} (>0.2pp)`);
      }
    }
    if (!p.as_of_utc) fail(name, 'performance.as_of_utc missing');
    if (!p.source) fail(name, 'performance.source missing');
    if (!p.benchmark_rationale) fail(name, 'performance.benchmark_rationale missing');
  }

  if (Array.isArray(t.series) && t.series.length < 2) fail(name, 'series needs >= 2 points');

  // proxies 1-3, ETFs must state fees
  if (Array.isArray(t.proxies)) {
    if (t.proxies.length < 1 || t.proxies.length > 3) fail(name, `proxies count ${t.proxies.length} not in 1-3`);
    t.proxies.forEach((px, i) => {
      for (const k of ['ticker', 'name', 'type', 'region', 'liquidity_note', 'why_represents', 'tracking_gap']) {
        if (!px[k]) fail(name, `proxies[${i}].${k} missing`);
      }
      if (px.type && !PROXY_TYPES.includes(px.type)) fail(name, `proxies[${i}].type bad: ${px.type}`);
      if (px.type === 'ETF' && !px.expense) fail(name, `proxies[${i}].expense required for ETF`);
    });
  }

  // events must carry UTC + source + url (no time or no source = unpublishable)
  // proxy_ret / benchmark_ret / return_window are required going forward (reviewer flag if missing);
  // machine only type-checks when present so existing bundles stay green (no fabricated backfill).
  if (Array.isArray(t.events)) {
    if (t.events.length < 1) fail(name, 'events empty');
    t.events.forEach((ev, i) => {
      if (!ev.event_time_utc) fail(name, `events[${i}] missing event_time_utc — UNPUBLISHABLE`);
      if (!ev.source) fail(name, `events[${i}] missing source — UNPUBLISHABLE`);
      if (!ev.url) fail(name, `events[${i}] missing url — UNPUBLISHABLE`);
      if (ev.type && !EVENT_TYPES.includes(ev.type)) fail(name, `events[${i}].type bad: ${ev.type}`);
      for (const k of ['proxy_ret', 'benchmark_ret']) {
        if (ev[k] !== undefined && typeof ev[k] !== 'number') fail(name, `events[${i}].${k} must be number (pct)`);
      }
      if ((ev.proxy_ret !== undefined || ev.benchmark_ret !== undefined) && !ev.return_window) {
        fail(name, `events[${i}].return_window required when returns are given (e.g. event-day, T+1D)`);
      }
    });
  }

  // no Next Catalyst means demote to Noise
  if (!Array.isArray(t.depends_on) || t.depends_on.length < 1) {
    fail(name, 'depends_on empty — no next catalyst, demote to Noise');
  } else {
    t.depends_on.forEach((d, i) => {
      for (const k of ['event_name', 'due_date', 'why_matters', 'if_bull', 'if_bear']) {
        if (!d[k]) fail(name, `depends_on[${i}].${k} missing`);
      }
    });
  }

  // Theme vs Noise: score must equal the true-count
  const vn = t.theme_vs_noise;
  if (vn) {
    const keys = ['persistence', 'breadth', 'volume_confirm', 'falsifiable_catalyst', 'repricing_logic'];
    const count = keys.filter((k) => vn[k] === true).length;
    if (vn.score !== count) fail(name, `theme_vs_noise.score=${vn.score} but true-count=${count}`);
    if (count < 3 && t.status !== 'Dead') console.warn(`  ! [${name}] noise score ${count} < 3 — demote off the homepage`);
  }
}

const themesDir = path.join(DATA_DIR, 'themes');
if (!fs.existsSync(themesDir)) {
  console.error('no data/themes directory');
  process.exit(1);
}

let checked = 0;
for (const week of fs.readdirSync(themesDir).filter((d) => /^\d{4}-W\d{2}$/.test(d))) {
  const dir = path.join(themesDir, week);
  for (const f of fs.readdirSync(dir).filter((f) => f.endsWith('.yaml'))) {
    checked++;
    const before = failures;
    try {
      validateTheme(path.join(dir, f), yaml.load(fs.readFileSync(path.join(dir, f), 'utf8')));
      if (failures === before) ok(f, 'schema_v1 PASS');
    } catch (e) {
      fail(f, `YAML parse error: ${e.message}`);
    }
  }
}

console.log(`\nvalidated ${checked} theme file(s), ${failures} failure(s)`);
process.exit(failures ? 1 : 0);
