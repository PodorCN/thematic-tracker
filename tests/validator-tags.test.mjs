import assert from 'node:assert/strict';
import { readFileSync, writeFileSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { test } from 'node:test';

const root = new URL('../', import.meta.url);

test('AI theme-specific event tags are accepted by the publishing validator', () => {
  const document = readFileSync(new URL('ai-software/theme.md', root), 'utf8');
  assert.match(document, /\| AI Disruption\s*$/m);
  assert.match(document, /\| AI Monetization\s*$/m);

  const result = spawnSync(process.execPath, ['scripts/validate-theme.mjs', 'ai-software/theme.md'], {
    cwd: root,
    encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr);
  assert.doesNotMatch(result.stderr, /non-standard tag/);
  assert.match(result.stdout, /0 warning\(s\)/);
});

test('AI verdict is scannable and every timeline event has an evidence-grade driver', () => {
  const document = readFileSync(new URL('ai-software/theme.md', root), 'utf8');
  const verdict = document.match(/^## VERDICT\s*\r?\n([\s\S]*?)(?=^## EVENTS)/m)?.[1] || '';
  const lines = verdict.trim().split(/\r?\n/).filter(Boolean);
  assert.equal(lines.length, 3);
  assert.deepEqual(lines.map(line => line.split(':')[0]), ['MARKET', 'THEME', 'WATCH']);
  assert.ok(lines.every(line => line.length < 210), 'each line should fit one glance');
  const events = document.match(/^### #\d+[^\r\n]*[\s\S]*?(?=^### #|^## |$(?![\s\S]))/gm) || [];
  assert.ok(events.length > 0);
  for (const event of events) assert.match(event, /^DRIVER: (MARKET|THEME|UNVERIFIED)\s*$/m);
});

test('validator fails closed if AI classification is missing', () => {
  const original = readFileSync(new URL('ai-software/theme.md', root), 'utf8');
  const mutated = original.replace(/^DRIVER: (MARKET|THEME|UNVERIFIED)\r?\n/m, '');
  assert.notEqual(original, mutated);
  const dir = mkdtempSync(join(tmpdir(), 'theme-driver-'));
  try {
    for (const name of ['theme.md', 'theme.txt']) writeFileSync(join(dir, name), mutated);
    const result = spawnSync(process.execPath, ['scripts/validate-theme.mjs', join(dir, 'theme.md')], {
      cwd: root, encoding: 'utf8',
    });
    assert.equal(result.status, 1);
    assert.match(result.stderr, /missing DRIVER/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('AI Q3 catalyst calendar separates NOW October from fiscal-quarter CRM/WDAY', () => {
  const markdown = readFileSync(new URL('ai-software/theme.md', root), 'utf8');
  const catalysts = markdown.split(/^## CATALYSTS\s*$/m)[1].split(/^## CHARTDATA\s*$/m)[0];
  assert.match(catalysts, /^### Late Oct 2026[^\r\n]*\| hot \| ServiceNow calendar Q3/m);
  assert.match(catalysts, /^### Late Nov–early Dec 2026[^\r\n]*\| Earnings \| CRM \/ WDAY fiscal Q3/m);
  assert.doesNotMatch(catalysts, /Q3 earnings: CRM \/ NOW \/ WDAY/);
  assert.match(catalysts, /date is NOT confirmed/);
});

test('AI November Workday event keeps the official guide direction and cautious attribution', () => {
  const markdown = readFileSync(new URL('ai-software/theme.md', root), 'utf8');
  const event = markdown.match(/^### #01 \| 2025-11-28[\s\S]*?(?=^### #02)/m)?.[0];
  assert.ok(event);
  assert.match(event, /raised full-year subscription revenue guidance to \$8\.828B from the \$8\.815B/);
  assert.match(event, /DRIVER: UNVERIFIED/);
  assert.match(event, /investor\.workday\.com\/news-and-events\/press-releases/);
  assert.doesNotMatch(event, /trimmed subscription outlook|guides down|proves AI disruption/i);
});

test('AI historical risk and launch dates follow issuer records', () => {
  const markdown = readFileSync(new URL('ai-software/theme.md', root), 'utf8');
  assert.match(markdown, /Forbes, Feb 4; updated Feb 5/);
  assert.match(markdown, /Salesforce's Sep 15 AIforce unveiling/);
  assert.match(markdown, /second trading day after the Fed's Sep 16 hike/);
  assert.doesNotMatch(markdown, /39% to 61% below prior highs|first full week after the Fed's hike/);
  assert.match(markdown, /IBM's separate Jul 14 letter/);
  assert.doesNotMatch(markdown, /Forbes, Feb 6|IBM's Sep 15|same morning's AIforce unveiling|Friday's AIforce unveiling/);
});

test('AI January monthly cause, September rebound, and future catalysts remain qualified', () => {
  const markdown = readFileSync(new URL('ai-software/theme.md', root), 'utf8');
  const jan = markdown.match(/^### #02 \| 2026-01-30[\s\S]*?(?=^### #03)/m)?.[0];
  assert.ok(jan);
  assert.match(jan, /DRIVER: UNVERIFIED/);
  assert.match(jan, /investing\.com\/news\/stock-market-news\/us-software-stocks/);
  assert.doesNotMatch(jan, /pure derating, zero macro cover/i);
  assert.match(markdown, /not proof that multiple names have reclaimed prior highs/);
  assert.match(markdown, /CRM -2\.00%, NOW -1\.47%, WDAY -1\.53%, ADBE -2\.82%, INTU -3\.38%/);
  assert.match(markdown, /Late Oct 2026 \(est\.; confirm with IR\) \| AI Capex/);
  assert.doesNotMatch(markdown, /selling concentrated in speculative small caps rather than the enterprise cohort|MSFT\/GOOGL\/AMZN\/META report late October/);
});

test('validator rejects a percentage-point label for the AI normalized-point lamp', () => {
  const original = readFileSync(new URL('ai-software/theme.md', root), 'utf8');
  const mutated = original.replace(/(CALL: green[^\r\n]*?[+]\d+\.\d+) normalized points/, '$1pp');
  assert.notEqual(original, mutated);
  const dir = mkdtempSync(join(tmpdir(), 'theme-unit-'));
  try {
    for (const name of ['theme.md', 'theme.txt']) writeFileSync(join(dir, name), mutated);
    const result = spawnSync(process.execPath, ['scripts/validate-theme.mjs', join(dir, 'theme.md')], {
      cwd: root, encoding: 'utf8',
    });
    assert.equal(result.status, 1);
    assert.match(result.stderr, /normalized-point spread/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('publishing validator rejects event prose before first event header', () => {
  const original = readFileSync(new URL('ai-software/theme.md', root), 'utf8');
  const mutated = original.replace(/(^## EVENTS)(\r?\n)(\r?\n)/m,
    (_match, heading, eol1, eol2) => `${heading}${eol1}${eol2}A prose introduction that the browser will misparse.${eol1}${eol2}`);
  assert.notEqual(original, mutated);
  const dir = mkdtempSync(join(tmpdir(), 'theme-events-'));
  try {
    for (const name of ['theme.md', 'theme.txt']) writeFileSync(join(dir, name), mutated);
    const result = spawnSync(process.execPath, ['scripts/validate-theme.mjs', join(dir, 'theme.md')], {
      cwd: root, encoding: 'utf8',
    });
    assert.equal(result.status, 1, 'The browser would parse prose as an event; reject it');
    assert.match(result.stderr, /EVENTS must start with ### #01/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
