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
