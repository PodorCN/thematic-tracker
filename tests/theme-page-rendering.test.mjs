import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';
import { test } from 'node:test';

const root = fileURLToPath(new URL('../', import.meta.url));
const themes = [
  { dir: 'ai-software', stat: 'WINDOW RETURN', value: '+0.79%', tone: 'up' },
  { dir: 'canadian-banks', stat: '3M RETURN', value: '-0.50%', tone: 'dn' },
];

function stagedTheme(dir) {
  return execFileSync('git', ['show', `:${dir}/theme.txt`], { cwd: root, encoding: 'utf8' });
}

function eventPreambleRemoved(markdown) {
  return markdown.replace(
    /(^## EVENTS\r?\n)\r?\nEarlier events are consolidated[^\r\n]*\r?\n\r?\n(?=### #01\s*\|)/m,
    '$1\n',
  );
}

function inlinePageScript(html) {
  const script = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)]
    .map(match => match[1])
    .find(source => source.includes('function parseTheme') && source.includes('function render('));
  assert.ok(script, 'page must contain its actual theme parser and renderer');
  return script;
}

async function renderPage(dir, response) {
  const html = readFileSync(`${root}/${dir}/index.html`, 'utf8');
  const app = { innerHTML: '' };
  const metaBar = { innerHTML: '' };
  const body = { dataset: {} };
  const nodes = { app, metaBar };
  const document = {
    body,
    getElementById(id) { return nodes[id] || (nodes[id] = { innerHTML: '', scrollIntoView() {} }); },
    querySelectorAll() { return []; },
  };
  class IntersectionObserver {
    observe() {}
    unobserve() {}
  }
  const sandbox = {
    document,
    fetch: () => typeof response === 'function' ? response() : response,
    IntersectionObserver,
    Plotly: { newPlot() {}, restyle() {} },
  };
  vm.runInNewContext(inlinePageScript(html), sandbox, { timeout: 1500 });
  await new Promise(resolve => setImmediate(resolve));
  return { app, body, metaBar };
}

function successfulResponse(markdown) {
  return Promise.resolve({ ok: true, text: () => Promise.resolve(markdown) });
}

function csvRows(path) {
  return readFileSync(`${root}/${path}`, 'utf8').trim().split(/\r?\n/).slice(1)
    .map(line => line.split(','))
    .map(([date, close, dailyReturn, volume]) => ({
      date,
      close: Number(close),
      dailyReturn: Number(dailyReturn),
      volume: Number(volume),
    }));
}

function countEventCards(html) {
  return (html.match(/<div class="ev(?:\s|\")/g) || []).length;
}

function statCard(html, label) {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = html.match(new RegExp(
    `<div class="stat"><div class="k">${escaped}</div><div class="v ([^\"]*) mono-num">([^<]*)<\\/div>`,
  ));
  return match && { classes: match[1].split(/\s+/), value: match[2] };
}

for (const theme of themes) {
  test(`${theme.dir}: staged theme renders only its numbered event cards`, async () => {
    const markdown = stagedTheme(theme.dir);
    const expectedEvents = (markdown.match(/^### #\d+\s*\|/gm) || []).length;
    const { app, body } = await renderPage(theme.dir, successfulResponse(markdown));

    assert.equal(body.dataset.themeError, undefined, 'valid staged theme must render without parser failure');
    assert.equal(countEventCards(app.innerHTML), expectedEvents);
    assert.equal(expectedEvents, 15);
    assert.doesNotMatch(app.innerHTML, /Earlier events are consolidated/);
  });

  test(`${theme.dir}: STATS schema values and tones appear in their proper cards`, async () => {
    const markdown = eventPreambleRemoved(stagedTheme(theme.dir));
    const { app, body } = await renderPage(theme.dir, successfulResponse(markdown));
    const card = statCard(app.innerHTML, theme.stat);

    assert.equal(body.dataset.themeError, undefined);
    assert.ok(card, `expected a rendered ${theme.stat} card`);
    assert.equal(card.value, theme.value);
    assert.ok(card.classes.includes(theme.tone), `expected ${theme.tone} class, got ${card.classes.join(' ')}`);
  });
}

test('missing theme.txt shows a visible error instead of stale embedded data', async () => {
  const { app } = await renderPage('ai-software', Promise.resolve({ ok: false, status: 404 }));

  assert.match(app.innerHTML, /role="alert"/);
  assert.match(app.innerHTML, /Theme data unavailable/i);
  assert.doesNotMatch(app.innerHTML, /AI-Beaten Software/);
});

test('invalid theme.txt parse shows a visible error instead of rendering blank or embedded data', async () => {
  const { app } = await renderPage('canadian-banks', successfulResponse('not a valid theme document'));

  assert.match(app.innerHTML, /role="alert"/);
  assert.match(app.innerHTML, /Theme data unavailable/i);
  assert.doesNotMatch(app.innerHTML, /Canadian Banks/);
});

test('AI Sep 21 QQQ return and IGV volume match recomputation from adjusted market data', () => {
  const qqqRows = csvRows('ai-software/tracker_data/refresh-2026-09-23-pm/QQQ.derived.csv');
  const igvRows = csvRows('ai-software/tracker_data/refresh-2026-09-23-pm/IGV.derived.csv');
  const qqqSep18 = qqqRows.find(row => row.date === '2026-09-18');
  const qqqSep21 = qqqRows.find(row => row.date === '2026-09-21');
  const igvSep21 = igvRows.find(row => row.date === '2026-09-21');
  const qqqReturn = ((qqqSep21.close / qqqSep18.close) - 1) * 100;
  const recentVolumes = igvRows.filter(row => row.date <= '2026-09-21').slice(-20).map(row => row.volume);
  const igvVolumeRatio = igvSep21.volume / (recentVolumes.reduce((sum, volume) => sum + volume, 0) / recentVolumes.length);
  const event = stagedTheme('ai-software').match(/^### #13 \| 2026-09-21[\s\S]*?(?=^### |\Z)/m)?.[0];

  assert.ok(qqqSep18 && qqqSep21 && igvSep21 && event, 'expected Sep 21 adjusted observations and event');
  assert.equal(qqqReturn.toFixed(2), '2.88');
  assert.equal(igvVolumeRatio.toFixed(2), '0.85');
  assert.match(event, /QQQ=\+2\.88%/);
  assert.match(event, /VOL=0\.85x/);
});

test('AI CATALYSTS repeats the recomputed QQQ return, not the stale value', () => {
  const markdown = stagedTheme('ai-software');
  const catalysts = markdown.split(/^## CATALYSTS\s*$/m).at(-1);

  assert.ok(catalysts, 'expected a CATALYSTS section');
  assert.match(catalysts, /QQQ.s stronger \+2\.88%/);
  assert.doesNotMatch(catalysts, /QQQ.s stronger \+2\.77%/);
});
