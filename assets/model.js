// Shared by the browser and the CLI. Markdown is data, never executable HTML.
export const isDate = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
export const isUrl = value => { try { return ['https:', 'http:'].includes(new URL(value).protocol); } catch { return false; } };
const requireThat = (condition, message) => { if (!condition) throw new Error(message); };

function table(text) {
  const lines = text.split('\n').filter(l => l.trim().startsWith('|'));
  if (!lines.length) return [];
  const split = l => l.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim());
  const headers = split(lines[0]);
  requireThat(lines.length >= 2 && split(lines[1]).every(c => /^:?-{3,}:?$/.test(c)), '表格缺少 --- 分隔行');
  return lines.slice(2).map((line, i) => {
    const cells = split(line);
    requireThat(cells.length === headers.length, `表格第 ${i + 3} 行列数不匹配`);
    return Object.fromEntries(headers.map((h, n) => [h, cells[n]]));
  });
}

export function parseReport(markdown) {
  markdown = markdown.replace(/^\uFEFF/, '').replace(/\r\n/g, '\n');
  const block = markdown.match(/^```json\s*\n([\s\S]*?)\n```/m);
  requireThat(block, '缺少开头的 JSON 配置代码块');
  let meta;
  try { meta = JSON.parse(block[1]); } catch (error) { throw new Error(`配置 JSON 无效：${error.message}`); }
  requireThat(meta.schemaVersion === 1, 'schemaVersion 必须是 1');
  for (const key of ['title', 'id', 'call', 'summary', 'priceBasis', 'priceSource', 'priceSourceUrl']) requireThat(typeof meta[key] === 'string' && meta[key].trim(), `配置缺少 ${key}`);
  requireThat(isDate(meta.updated) && isDate(meta.asOf) && meta.updated >= meta.asOf, 'updated / asOf 必须是有效日期，且 updated 不早于 asOf');
  requireThat(['verified', 'partial', 'unverified'].includes(meta.status), 'status 必须是 verified / partial / unverified');
  requireThat(isUrl(meta.priceSourceUrl), 'priceSourceUrl 必须是 http(s) URL');
  requireThat(Array.isArray(meta.proxies) && meta.proxies.length >= 2, '至少需要一个 main 和一个 benchmark');
  const symbols = new Set();
  for (const p of meta.proxies) {
    requireThat(p && typeof p.symbol === 'string' && p.symbol && !symbols.has(p.symbol), 'proxy symbol 缺失或重复');
    requireThat(['main', 'benchmark', 'support'].includes(p.role) && typeof p.name === 'string' && p.name && typeof p.currency === 'string' && p.currency, `${p.symbol} 缺少合法 role、name 或 currency`);
    symbols.add(p.symbol);
  }
  for (const role of ['main', 'benchmark']) requireThat(meta.proxies.filter(p => p.role === role).length === 1, `必须恰好有一个 ${role}`);
  const sections = markdown.slice(block.index + block[0].length).split(/^## /m).slice(1).map(chunk => {
    const newline = chunk.indexOf('\n');
    return { title: (newline < 0 ? chunk : chunk.slice(0, newline)).trim(), body: newline < 0 ? '' : chunk.slice(newline + 1).trim() };
  });
  requireThat(new Set(sections.map(s => s.title)).size === sections.length, '二级标题不能重复');
  const get = title => sections.find(s => s.title === title)?.body || '';
  const rows = table(get('行情'));
  requireThat(rows.length > 0, '行情表不能为空');
  const prices = Object.fromEntries(meta.proxies.map(p => [p.symbol, []]));
  let previous = '';
  for (const row of rows) {
    requireThat(isDate(row.date) && row.date > previous && row.date <= meta.asOf, `行情日期无效、重复、未升序或晚于 asOf：${row.date}`);
    previous = row.date;
    for (const symbol of symbols) {
      requireThat(symbol in row, `行情表缺少 ${symbol} 列`);
      const value = row[symbol];
      if (value === '—' || value === '-') continue;
      requireThat(value !== '' && Number.isFinite(Number(value)) && Number(value) > 0, `${row.date} ${symbol} 价格必须为正数，缺失请写 —`);
      prices[symbol].push({ d: row.date, c: Number(value) });
    }
  }
  for (const symbol of symbols) requireThat(prices[symbol].length >= 1, `${symbol} 至少需要一个有效价格`);
  const events = get('事件').split(/^### /m).slice(1).map(chunk => {
    const lines = chunk.trim().split('\n');
    const heading = lines.shift().match(/^(\d{4}-\d{2}-\d{2})\s*\|\s*(.+)$/);
    requireThat(heading && isDate(heading[1]) && heading[1] <= meta.asOf, '事件标题格式应为 YYYY-MM-DD | 标题，且日期不晚于 asOf');
    const fields = {};
    const body = [];
    for (const line of lines) {
      const field = line.match(/^- (impact|direction|category|verification):\s*(.+)$/);
      if (field) fields[field[1]] = field[2].trim(); else body.push(line);
    }
    requireThat(['high', 'medium', 'low'].includes(fields.impact), `${heading[1]} impact 无效`);
    requireThat(['positive', 'negative', 'mixed'].includes(fields.direction), `${heading[1]} direction 无效`);
    requireThat(['verified', 'unverified'].includes(fields.verification), `${heading[1]} verification 无效`);
    const sources = [...body.join('\n').matchAll(/\[([^\]]+)\]\(([^\s)]+)\)/g)].map(m => ({ label: m[1], url: m[2] }));
    requireThat(sources.length && sources.every(s => isUrl(s.url)), `${heading[1]} 需要有效的 http(s) 来源链接`);
    const text = body.filter(l => !/^来源[：:]/.test(l)).join('\n').trim();
    requireThat(text, `${heading[1]} 事件正文不能为空`);
    return { date: heading[1], title: heading[2], ...fields, body: text, sources };
  });
  requireThat(new Set(events.map(e => e.date + e.title)).size === events.length, '事件日期 + 标题重复');
  const catalysts = table(get('催化日历')).map(row => {
    requireThat(isDate(row.date) && row.title && row.watch && ['confirmed', 'tentative', 'unverified'].includes(row.status), '催化日历需要有效 date、title、watch、status');
    requireThat(row.source === '—' || isUrl(row.source), '催化日历 source 需要 http(s) URL 或 —');
    requireThat(row.status !== 'confirmed' || isUrl(row.source), '已确认的催化日历必须有来源');
    return row;
  }).sort((a, b) => a.date.localeCompare(b.date));
  requireThat(meta.status !== 'verified' || events.every(e => e.verification === 'verified'), '报告 verified 时不能包含未核验事件');
  const warnings = [];
  if (meta.status !== 'verified') warnings.push(meta.qualityNote || '资料尚未全部核验，请查看来源后使用。');
  for (const p of meta.proxies) if (prices[p.symbol].at(-1).d < meta.asOf) warnings.push(`${p.symbol} 行情仅截至 ${prices[p.symbol].at(-1).d}`);
  return { meta, prices, events: events.sort((a, b) => b.date.localeCompare(a.date)), catalysts, research: sections.filter(s => !['行情', '事件', '催化日历'].includes(s.title)), warnings };
}

export const percent = (last, first) => (last / first - 1) * 100;
export function windowData(report, range = '3M') {
  const { meta, prices } = report;
  const main = meta.proxies.find(p => p.role === 'main');
  const benchmark = meta.proxies.find(p => p.role === 'benchmark');
  const cutoff = new Date(`${meta.asOf}T00:00:00Z`);
  if (range !== 'ALL') cutoff.setUTCDate(cutoff.getUTCDate() - (range === '1M' ? 30 : 90));
  const start = range === 'ALL' ? '0000-00-00' : cutoff.toISOString().slice(0, 10);
  const bm = new Map(prices[benchmark.symbol].map(p => [p.d, p.c]));
  const common = prices[main.symbol].filter(p => p.d >= start && bm.has(p.d));
  const first = common[0], last = common.at(-1);
  const series = Object.fromEntries(meta.proxies.map(p => [p.symbol, prices[p.symbol].filter(r => first && r.d >= first.d && r.d <= last.d)]));
  return { main, benchmark, first, last, series, mainReturn: common.length >= 2 ? percent(last.c, first.c) : null, benchmarkReturn: common.length >= 2 ? percent(bm.get(last.d), bm.get(first.d)) : null };
}

export function eventPrice(report, date) {
  const symbol = report.meta.proxies.find(p => p.role === 'main').symbol;
  const rows = report.prices[symbol];
  const index = rows.findIndex(r => r.d === date);
  return index < 0 ? null : { close: rows[index].c, move: index > 0 ? percent(rows[index].c, rows[index - 1].c) : null };
}
