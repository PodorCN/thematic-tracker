// Validator for app/theme.md — implements the Step 5 checklist in agent.md.
// Usage: node scripts/validate-theme.mjs [path/to/theme.md]
// Exit 0 = PASS (warnings allowed), 1 = FAIL.
import { readFile } from 'node:fs/promises';

const file = process.argv[2] || 'app/theme.md';
const errors = [];
const warnings = [];
const err = m => errors.push(m);
const warn = m => warnings.push(m);

const raw = await readFile(file, 'utf8').catch(() => null);
if (!raw) { console.error(`FAIL: cannot read ${file}`); process.exit(1); }
// Normalize: theme.md is often edited on Windows (CRLF) — the renderer tolerates it, so must we.
const md = raw.replace(/^\uFEFF/, '').replace(/\r\n/g, '\n');

// ---------- frontmatter ----------
const fm = md.match(/^---\r?\n([\s\S]*?)\r?\n---/);
if (!fm) err('missing frontmatter block');
const meta = {};
if (fm) for (const line of fm[1].split('\n')) {
  const m = line.match(/^(\w+):\s*(.+)$/);
  if (m) meta[m[1]] = m[2].trim();
}
for (const k of ['theme_cn', 'theme_en', 'updated', 'window', 'currency'])
  if (!meta[k]) err(`frontmatter missing ${k}`);
if (meta.updated && !/^\d{4}-\d{2}-\d{2}$/.test(meta.updated)) err(`updated not YYYY-MM-DD: ${meta.updated}`);

// ---------- sections ----------
const chunks = md.split(/^## /m).slice(1).map(c => {
  const nl = c.indexOf('\n');
  return { title: c.slice(0, nl).trim(), body: c.slice(nl + 1).trim() };
});
for (const s of ['PROXIES', 'STATS', 'VERDICT', 'EVENTS', 'CATALYSTS', 'CHARTDATA'])
  if (!chunks.some(c => c.title === s)) err(`missing ## ${s} section`);
const get = t => chunks.find(c => c.title === t)?.body || '';

const tableRows = body => body.split('\n')
  .filter(l => l.trim().startsWith('|'))
  .slice(2)
  .map(l => l.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim()));

// ---------- CHARTDATA ----------
let cd = null;
const m = get('CHARTDATA').match(/```json\s*\n([\s\S]*?)\n```/);
if (!m) err('CHARTDATA missing ```json block');
else try { cd = JSON.parse(m[1]); } catch (e) { err(`CHARTDATA JSON invalid: ${e.message}`); }

let normLen = 0;
if (cd) {
  const { dates } = cd;
  if (!Array.isArray(dates) || !dates.length) err('CHARTDATA.dates empty');
  else {
    for (let i = 1; i < dates.length; i++)
      if (dates[i] <= dates[i - 1]) { err(`dates not ascending at ${dates[i]}`); break; }
    normLen = dates.length;
    for (const k of ['zeb_norm', 'tsx_norm', 'bank_norm', 'hfin_norm', 'volume', 'zeb_ret']) {
      if (!Array.isArray(cd[k])) err(`CHARTDATA.${k} missing`);
      else if (cd[k].length !== normLen) err(`CHARTDATA.${k} length ${cd[k].length} != dates ${normLen}`);
    }
    if (cd.zeb_norm?.[0] !== 100) err(`zeb_norm[0] should be 100, got ${cd.zeb_norm?.[0]}`);
    if (cd.zeb_ret?.[0] !== null) err('zeb_ret[0] should be null');
    if (!Array.isArray(cd.spx_dates) || !Array.isArray(cd.spx_norm) || cd.spx_dates.length !== cd.spx_norm.length)
      err('spx_dates/spx_norm missing or length mismatch');
  }
}
const dateSet = new Set(cd?.dates || []);

// ---------- EVENTS ----------
const KNOWN_TAGS = new Set(['Earnings', 'Monetary Policy', 'Geopolitics', 'Macro Data', 'Valuation & Sentiment']);
const blocks = get('EVENTS').split(/^### /m).slice(1);
if (!blocks.length) err('EVENTS has no event blocks');
blocks.forEach((b, i) => {
  const lines = b.trim().split('\n');
  const h = lines.shift().match(/^#(\d+)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*ZEB\s*([+-]?\d+(?:\.\d+)?%)\s*\|\s*(.+)$/);
  if (!h) { err(`event #${i + 1} heading malformed: ${lines[0] || ''}`.slice(0, 120)); return; }
  const [, num, date, move, tag] = h;
  if (Number(num) !== i + 1) err(`event numbering broken: expected #${String(i + 1).padStart(2, '0')}, got #${num}`);
  if (!dateSet.has(date)) err(`event ${date} is not a ZEB trading day in CHARTDATA.dates`);
  if (date > (meta.updated || '9999')) err(`event ${date} later than updated ${meta.updated}`);
  if (!KNOWN_TAGS.has(tag.trim())) warn(`event ${date} has non-standard tag: ${tag.trim()}`);
  const moves = lines.find(l => l.startsWith('MOVES:'));
  const src = lines.find(l => l.startsWith('SRC:'));
  if (!moves) err(`event ${date} missing MOVES line`);
  else {
    const v = moves.match(/([+-]?\d+(?:\.\d+)?)%/);
    if (!v) err(`event ${date} MOVES has no % value`);
    else if ((v[1].startsWith('-')) !== (move.startsWith('-'))) warn(`event ${date} heading ${move} vs MOVES ${v[0]} sign differs`);
  }
  if (!src || src.replace(/^SRC:\s*/, '').trim() === '') err(`event ${date} missing SRC line`);
  else if (!/https?:\/\//.test(src) && !/\d{4}/.test(src)) warn(`event ${date} SRC has no URL or date: ${src.slice(0, 80)}`);
});
if (blocks.length > 15) warn(`event count ${blocks.length} > 15, consider merging old ones`);

// ---------- PROXIES cross-check vs CHARTDATA ----------
if (cd && normLen) {
  const end = k => cd[k][cd[k].length - 1] - 100;
  const expect = { 'ZEB.TO': end('zeb_norm'), 'BANK.TO': end('bank_norm'), 'HFIN.TO': end('hfin_norm'), '^GSPTSE': end('tsx_norm'), '^GSPC': cd.spx_norm[cd.spx_norm.length - 1] - 100 };
  for (const row of tableRows(get('PROXIES'))) {
    const [role, ticker, , ret] = row;
    if (/EXCESS/.test(role)) {
      const v = parseFloat(ret);
      const calc = expect['ZEB.TO'] - expect['^GSPTSE'];
      if (Number.isFinite(v) && Math.abs(v - calc) > 0.06) err(`EXCESS row ${ret} != ZEB-TSX ${calc.toFixed(2)}pp`);
      continue;
    }
    if (!(ticker in expect)) continue;
    const v = parseFloat(ret);
    if (!Number.isFinite(v)) { err(`PROXIES ${ticker} ret3m not a number: ${ret}`); continue; }
    if (Math.abs(v - expect[ticker]) > 0.06) err(`PROXIES ${ticker} ret3m ${ret} != chartdata ${expect[ticker].toFixed(2)}%`);
  }
}

// ---------- CATALYSTS ----------
const hot = (get('CATALYSTS').match(/\|\s*hot\s*\|/g) || []).length;
if (!hot) warn('no catalyst marked hot');

// ---------- report ----------
for (const w of warnings) console.warn(`WARNING: ${w}`);
if (errors.length) {
  for (const e of errors) console.error(`ERROR: ${e}`);
  console.error(`FAIL ${file}: ${errors.length} error(s), ${warnings.length} warning(s)`);
  process.exit(1);
}
console.log(`PASS ${file}: ${blocks.length} events, dates ${cd.dates[0]} → ${cd.dates[cd.dates.length - 1]}, ${warnings.length} warning(s)`);
