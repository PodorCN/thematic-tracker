// Build a weekly review candidate JSON from data/themes/<week>/*.yaml.
// Usage: node scripts/build_candidate.mjs --week 2026-W40 --snapshot-date 2026-10-04 [--out PATH]
// Defaults: --week = latest in data/themes, --snapshot-date = today Toronto, --out = stdout.
// Output: {snapshot_date, week, themes[], market_snapshot?, commentary?}
// Freeze/publish compare canonical(shared freeze) bytes, so key order here does not matter.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const yaml = require("js-yaml");

function arg(name, def = null) {
  const i = process.argv.indexOf(name);
  return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : def;
}

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DATA = path.join(ROOT, "data");

function torontoToday() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Toronto", year: "numeric", month: "2-digit", day: "2-digit",
  }).format(new Date());
}

function latestWeek() {
  const dir = path.join(DATA, "themes");
  if (!fs.existsSync(dir)) return null;
  const weeks = fs.readdirSync(dir).filter((d) => /^\d{4}-W\d{2}$/.test(d)).sort();
  return weeks.length ? weeks[weeks.length - 1] : null;
}

function loadYaml(file) {
  return yaml.load(fs.readFileSync(file, "utf8"));
}

const week = arg("--week", latestWeek());
const snapshotDate = arg("--snapshot-date", torontoToday());
const out = arg("--out", null);

if (!week || !/^\d{4}-W\d{2}$/.test(week)) {
  console.error(`✗ --week must be YYYY-Www (got ${week})`);
  process.exit(1);
}
if (!/^\d{4}-\d{2}-\d{2}$/.test(snapshotDate || "")) {
  console.error(`✗ --snapshot-date must be YYYY-MM-DD (got ${snapshotDate})`);
  process.exit(1);
}

const themesDir = path.join(DATA, "themes", week);
if (!fs.existsSync(themesDir)) {
  console.error(`✗ themes dir missing: data/themes/${week}/`);
  process.exit(1);
}
const themes = fs.readdirSync(themesDir)
  .filter((f) => f.endsWith(".yaml"))
  .sort()
  .map((f) => loadYaml(path.join(themesDir, f)));

let market_snapshot = null;
const snapFile = path.join(DATA, "market", `snapshot_${week}.yaml`);
if (fs.existsSync(snapFile)) market_snapshot = loadYaml(snapFile);

let commentary = null;
const commFile = path.join(DATA, "commentary", `${week}.yaml`);
if (fs.existsSync(commFile)) commentary = loadYaml(commFile);

const candidate = { snapshot_date: snapshotDate, week, themes, market_snapshot, commentary };
const payload = JSON.stringify(candidate, null, 2) + "\n";
if (out) {
  fs.writeFileSync(out, payload, "utf8");
  console.error(`✓ built candidate week=${week} themes=${themes.length} snapshot_date=${snapshotDate} -> ${out}`);
} else {
  process.stdout.write(payload);
}
