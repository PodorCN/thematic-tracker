import { readFile } from 'node:fs/promises';
import { parseReport, windowData } from '../assets/model.js';
try {
  const file = process.argv[2] || 'data/daily.md';
  const report = parseReport(await readFile(file, 'utf8'));
  const data = windowData(report, 'ALL');
  if (data.mainReturn === null) throw new Error('主标的与基准至少需要两个共同交易日');
  console.log(`PASS ${file}: ${report.meta.proxies.length} proxies, ${report.events.length} events, ${report.research.length} research sections`);
  for (const warning of report.warnings) console.warn(`WARNING: ${warning}`);
  console.log(`Common window: ${data.first.d} → ${data.last.d}; excess ${(data.mainReturn - data.benchmarkReturn).toFixed(2)} pp`);
} catch (error) { console.error(`FAIL: ${error.message}`); process.exitCode = 1; }
