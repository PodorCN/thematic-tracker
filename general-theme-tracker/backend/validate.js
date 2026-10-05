// Schema v1 校验器 — Agent PR 合并前必跑（CI gate）
// 用法：node backend/validate.js
// 退出码：0 = 全部通过；1 = 有 FAIL

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

function cnLen(s) {
  // 粗略：CJK 字符按 1 计，其余按英文单词折算（200wpm 规则的前置粗检）
  const cjk = (s.match(/[一-鿿]/g) || []).length;
  const words = (s.replace(/[一-鿿]/g, ' ').match(/\S+/g) || []).length;
  return { cjk, words };
}

function validateTheme(file, t) {
  const name = path.basename(file);
  const req = ['schema_v', 'id', 'week', 'title', 'status', 'status_note', 'conviction', 'horizon', 'created_at', 'updated_at', 'data_quality', 'body_text', 'performance', 'series', 'proxies', 'events', 'depends_on', 'theme_vs_noise'];
  for (const k of req) if (t[k] === undefined) fail(name, `missing required field: ${k}`);

  if (t.schema_v !== 1) fail(name, `schema_v must be 1, got ${t.schema_v}`);
  if (t.id && !/^[a-z0-9-]+$/.test(t.id)) fail(name, `id must be slug: ${t.id}`);
  if (t.week && !/^\d{4}-W\d{2}$/.test(t.week)) fail(name, `week format: ${t.week}`);
  if (t.status && !STATUS.includes(t.status)) fail(name, `bad status: ${t.status}`);
  if (t.conviction && !CONVICTION.includes(t.conviction)) fail(name, `bad conviction: ${t.conviction}`);
  if (t.horizon && !HORIZON.includes(t.horizon)) fail(name, `bad horizon: ${t.horizon}`);

  // 5-min rule
  if (t.body_text) {
    const { cjk, words } = cnLen(t.body_text);
    if (cjk > 900) fail(name, `body_text CJK chars ${cjk} > 900 (>5min)`);
    if (words > 500) fail(name, `body_text EN words ${words} > 500 (>5min)`);
  }

  // performance & excess 复核（Reviewer 规则：误差 >0.2pp 打回）
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

  // proxies 1-3，ETF 必须有费率
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

  // events 必须有 UTC + source + url（无时间无源 = 不可发布）
  if (Array.isArray(t.events)) {
    if (t.events.length < 1) fail(name, 'events empty');
    t.events.forEach((ev, i) => {
      if (!ev.event_time_utc) fail(name, `events[${i}] missing event_time_utc — UNPUBLISHABLE`);
      if (!ev.source) fail(name, `events[${i}] missing source — UNPUBLISHABLE`);
      if (!ev.url) fail(name, `events[${i}] missing url — UNPUBLISHABLE`);
      if (ev.type && !EVENT_TYPES.includes(ev.type)) fail(name, `events[${i}].type bad: ${ev.type}`);
    });
  }

  // 没有 Next Catalyst 降级 Noise
  if (!Array.isArray(t.depends_on) || t.depends_on.length < 1) {
    fail(name, 'depends_on empty — no next catalyst, demote to Noise');
  } else {
    t.depends_on.forEach((d, i) => {
      for (const k of ['event_name', 'due_date', 'why_matters', 'if_bull', 'if_bear']) {
        if (!d[k]) fail(name, `depends_on[${i}].${k} missing`);
      }
    });
  }

  // Theme vs Noise：score 必须等于 true 计数
  const vn = t.theme_vs_noise;
  if (vn) {
    const keys = ['persistence', 'breadth', 'volume_confirm', 'falsifiable_catalyst', 'repricing_logic'];
    const count = keys.filter((k) => vn[k] === true).length;
    if (vn.score !== count) fail(name, `theme_vs_noise.score=${vn.score} but true-count=${count}`);
    if (count < 3 && t.status !== 'Dead') console.warn(`  ! [${name}] noise score ${count} < 3 — 应降级不上首页`);
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
