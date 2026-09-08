// One-time migration. Refuses to overwrite the daily report.
import { readFile, writeFile } from 'node:fs/promises';
const readLegacy = async (file, name) => JSON.parse((await readFile(file, 'utf8')).replace(new RegExp(`^window\\.${name}\\s*=\\s*`), '').replace(/;\s*$/, ''));
const theme = await readLegacy('data/theme-canadian-banks.js', 'THEME');
const prices = await readLegacy('data/prices.js', 'PRICES');
const proxies = [ { ...theme.mainProxy, role: 'main', currency: 'CAD' }, { ...theme.benchmark, role: 'benchmark', currency: 'USD' }, ...theme.supportProxies.map(p => ({ ...p, role: 'support', currency: 'CAD' })) ];
const meta = { schemaVersion: 1, id: theme.id, title: theme.title, subtitle: 'CANADIAN BANKS · THEMATIC RESEARCH', updated: theme.updated, asOf: theme.snapshot.asOf, status: 'unverified', call: '观察 · 等待证据确认', summary: '利差、信贷成本与非息收入，是观察加拿大银行业的三条主线。下方保留原有研究记录；观点与事件需逐项核验后再形成新的判断。', priceBasis: '原始收盘价 · 不含分红 · 各自本币', priceSource: 'Yahoo Finance（原项目记录，未重新核验）', priceSourceUrl: 'https://finance.yahoo.com/', qualityNote: '历史资料迁移：行情、事件及预告沿用旧版记录，尚未逐项核验；来源页面与事件日期需复核。跨币种对比未做汇率换算。', proxies };
const dates = [...new Set(Object.values(prices).flatMap(rows => rows.map(r => r.d)))].sort();
let md = `# ${theme.title} · 每日研究\n\n\`\`\`json\n${JSON.stringify(meta, null, 2)}\n\`\`\`\n\n`;
for (const [title, key] of [['收益归因', 'whyUpDown'], ['相对表现', 'vsBenchmark'], ['主题优势', 'edge'], ['后续观察', 'nextCatalyst']]) md += `## ${title}\n\n> 原有研究观点，待核验。\n\n${theme.snapshot[key]}\n\n`;
md += '## 催化日历\n\n| date | title | watch | status | source |\n| --- | --- | --- | --- | --- |\n| 2026-10-28 | BoC 利率决议与 MPR | 政策路径、利差与信贷展望；旧版预告日期待核验 | unverified | https://www.bankofcanada.ca/ |\n\n';
md += `## 行情\n\n| date | ${proxies.map(p => p.symbol).join(' | ')} |\n| --- | ${proxies.map(() => '---').join(' | ')} |\n`;
for (const date of dates) md += `| ${date} | ${proxies.map(p => prices[p.symbol].find(r => r.d === date)?.c.toFixed(2) ?? '—').join(' | ')} |\n`;
md += '\n## 事件\n\n';
for (const event of theme.events) md += `### ${event.date} | ${event.title}\n\n- impact: ${event.impact}\n- direction: ${event.direction}\n- category: ${/财报/.test(event.title) ? '公司财报' : /BoC/.test(event.title) ? '货币政策' : '宏观环境'}\n- verification: unverified\n\n${event.body}\n\n来源：${event.sources.map((url, i) => `[来源 ${i + 1}](${url})`).join(' · ')}\n\n`;
await writeFile('data/daily.md', md, { flag: 'wx' });
console.log('Created data/daily.md; original files preserved.');
