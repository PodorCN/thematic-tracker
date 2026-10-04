#!/usr/bin/env node
/**
 * publish.mjs — Rates_decisions structural gate + reviewer gate + publisher.
 *
 *   node scripts/publish.mjs --check   # structural check only (errors fail, flags warn)
 *   node scripts/publish.mjs           # full gate, then publish snapshot
 *
 * New flow (SHA-bound, no self-review):
 *   1. edit data/current.json (snapshot_date = today Toronto)
 *   2. node scripts/freeze.mjs         # -> review/<today>/{candidate.json, candidate.sha256, structural-flags.json}
 *   3. reviewer writes review/<today>/pm-review.json (see review/REVIEWER_AGENT.md)
 *   4. npm run publish                 # validates structure + review + sha binding, then archives
 *
 * Legacy review/<YYYY-MM-DD>.md files are NOT accepted anymore.
 */
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { canonical, structuralFlags } from "./freeze.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dataDir = path.join(root, "data");
const checkOnly = process.argv.includes("--check");

function torontoToday() {
  const p = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Toronto", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date());
  const m = Object.fromEntries(p.map((x) => [x.type, x.value]));
  return `${m.year}-${m.month}-${m.day}`;
}
const shaHex = (s) => crypto.createHash("sha256").update(s).digest("hex");
function torontoDay(s) {
  if (typeof s === "string" && /^\d{4}-\d{2}-\d{2}$/.test(s.trim())) return s.trim(); // date-only = Toronto date as written
  const d = s instanceof Date ? s : new Date(s);
  if (Number.isNaN(d.getTime())) return null;
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Toronto", year: "numeric", month: "2-digit", day: "2-digit" }).format(d);
}
function ageDays(observed, asOf) {
  // Calendar-day difference in Toronto (not millisecond math): a date-only
  // "2026-09-04" means Sep 4 Toronto, so Sep 4 -> Oct 4 is exactly 30d (x0.5),
  // not 30.6d (which would wrongly fall into the >30d bucket).
  const a = torontoDay(observed);
  const b = torontoDay(asOf instanceof Date ? asOf.toISOString() : asOf);
  if (!a || !b) return 0;
  return Math.round((new Date(b + "T12:00:00Z") - new Date(a + "T12:00:00Z")) / 864e5);
}
const decay = (d) => (d <= 7 ? 1 : d <= 14 ? 0.75 : d <= 30 ? 0.5 : 0.25);
const bandOf = (b) =>
  b >= 7 ? "strong hike lean" : b > 3 ? "lean hike" : b >= -3 ? "hold" : b >= -7 ? "lean cut" : "strong cut lean";

function validate(doc) {
  const errors = [];
  const fail = (m) => errors.push(m);
  const text = JSON.stringify(doc);
  if (/NaN|Infinity/.test(text)) fail("JSON contains NaN/Infinity");

  if (!doc.as_of || Number.isNaN(new Date(doc.as_of).getTime())) fail("as_of must be ISO8601 with offset");
  const asOf = new Date(doc.as_of);

  for (const bank of ["fed", "boc"]) {
    const p = doc.meetings?.[bank]?.pricing;
    if (!p) { fail(`meetings.${bank}.pricing missing`); continue; }
    if (p.probabilities !== null) {
      const vals = Object.values(p.probabilities ?? {});
      if (vals.length !== 3) fail(`${bank}: probabilities must have exactly 3 keys (hike/hold/cut)`);
      const sum = vals.reduce((a, b) => a + b, 0);
      if (vals.some((v) => typeof v !== "number" || !isFinite(v) || v < 0 || v > 1))
        fail(`${bank}: probability out of [0,1]`);
      if (sum < 0.99 || sum > 1.01) fail(`${bank}: probabilities sum ${sum.toFixed(3)}, must be 0.99-1.01`);
    } else if (p.probability_status !== "unavailable") {
      fail(`${bank}: null probabilities require probability_status "unavailable"`);
    }
    if (!/^https:\/\//.test(String(p.source_url || ""))) fail(`meetings.${bank}.pricing.source_url must be https://`);

    // betting sums
    for (const b of doc.betting?.[bank] ?? []) {
      if (b.status === "available" && b.probabilities) {
        const s = Object.values(b.probabilities).reduce((a, x) => a + x, 0);
        if (s < 0.99 || s > 1.01) fail(`betting.${bank}.${b.platform}: probabilities sum ${s.toFixed(3)}`);
      }
    }

    const dr = doc.drivers?.[bank];
    if (!dr) { fail(`drivers.${bank} missing`); continue; }
    const sides = [["hawkish", 1], ["dovish", -1]];
    const all = [];
    for (const [side, want] of sides) {
      for (const d of dr[side] ?? []) {
        all.push(d);
        if (d.direction !== want)
          fail(`${bank}/${d.id}: in "${side}" array but direction=${d.direction} (must be ${want > 0 ? "+1" : "-1"})`);
      }
    }
    const ids = new Set();
    let signed = 0, wSum = 0, effSigned = 0;
    for (const d of all) {
      if (!d.id || ids.has(d.id)) fail(`${bank}: duplicate or missing driver id "${d.id}"`);
      ids.add(d.id);
      if (!Number.isInteger(d.weight) || d.weight < 1 || d.weight > 10)
        fail(`${bank}/${d.id}: weight must be integer 1-10`);
      const wb = d.weight_breakdown || {};
      const parts = [wb.deviation, wb.importance, wb.surprise].map(Number);
      if (parts.some((n) => !isFinite(n))) fail(`${bank}/${d.id}: weight_breakdown needs deviation+importance+surprise numbers`);
      else if (Math.abs(parts[0] + parts[1] + parts[2] - d.weight) > 1e-9 || wb.total !== d.weight)
        fail(`${bank}/${d.id}: breakdown (${parts.join("+")}) must sum to weight ${d.weight} (and total=${d.weight})`);
      if (!/^https:\/\//.test(String(d.source_url || ""))) fail(`${bank}/${d.id}: source_url must be https://`);
      if (d.weight >= 7 && (!d.market_validation || d.market_validation === "unverified"))
        fail(`${bank}/${d.id}: weight ≥7 requires market validation evidence`);
      if (!d.observed_at || Number.isNaN(new Date(d.observed_at).getTime()))
        fail(`${bank}/${d.id}: observed_at must be ISO8601`);
      signed += d.direction * d.weight;
      wSum += Math.abs(d.weight);
      effSigned += d.direction * d.weight * decay(ageDays(d.observed_at, asOf));
    }
    if (all.length && wSum / all.length > 5)
      fail(`${bank}: mean |weight| ${(wSum / all.length).toFixed(1)} > 5 → score inflation`);
    const declared = doc.total_score?.[bank]?.base_total;
    const recomputed = Math.max(-10, Math.min(10, signed));
    if (declared !== recomputed) fail(`${bank}: total_score.base_total=${declared} but drivers sum to ${recomputed}`);
    const declEff = doc.total_score?.[bank]?.effective_total;
    if (typeof declEff !== "number" || Math.abs(declEff - Math.round(effSigned * 100) / 100) > 0.06)
      fail(`${bank}: total_score.effective_total=${declEff} but age-decayed recompute is ${(Math.round(effSigned * 100) / 100).toFixed(2)} (decay ≤7d×1 / 8–14d×0.75 / 15–30d×0.5 / >30d×0.25 vs as_of)`);
    const declBand = String(doc.total_score?.[bank]?.band || "");
    if (!declBand.toLowerCase().includes(bandOf(recomputed).split(" ")[0].toLowerCase()) && !(recomputed >= -3 && recomputed <= 3 && declBand.toLowerCase() === "hold"))
      fail(`${bank}: band "${declBand}" does not match base_total ${recomputed} (expected ~"${bandOf(recomputed)}")`);
  }

  // global duplicate ids across banks
  const allIds = [...(doc.drivers?.fed?.hawkish ?? []), ...(doc.drivers?.fed?.dovish ?? []),
    ...(doc.drivers?.boc?.hawkish ?? []), ...(doc.drivers?.boc?.dovish ?? [])].map((d) => d.id);
  if (new Set(allIds).size !== allIds.length) fail("duplicate driver id across fed/boc");

  for (const e of doc.calendar ?? []) {
    if (!e.date_toronto) fail(`calendar "${e.event}": date_toronto required`);
    if (e.date_only) {
      if (e.datetime_toronto || e.datetime_utc)
        fail(`calendar "${e.event}": date_only events must set datetimes to null`);
    } else if (!e.datetime_toronto || !e.datetime_utc) {
      fail(`calendar "${e.event}": timed releases require datetime_toronto + datetime_utc`);
    }
    if (!/^https:\/\//.test(String(e.source_url || ""))) fail(`calendar "${e.event}": source_url must be https://`);
  }
  return errors;
}

function frontendDirty() {
  const watched = ["Rates_decisions/index.html", "Rates_decisions/app.js", "Rates_decisions/styles.css", "Rates_decisions/dev-server.js", "Rates_decisions/scripts/"];
  try {
    const out = execSync("git diff --name-only && git diff --cached --name-only", { cwd: path.resolve(root, ".."), encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
    const files = out.split("\n").map((s) => s.trim()).filter(Boolean);
    return files.filter((f) => watched.some((w) => f === w || f.startsWith(w)));
  } catch { return null; }
}

function main() {
  const currentPath = path.join(dataDir, "current.json");
  let doc;
  try {
    doc = JSON.parse(fs.readFileSync(currentPath, "utf8"));
  } catch (e) {
    console.error(`✗ current.json is not valid JSON: ${e.message}`);
    process.exit(1);
  }

  const errors = validate(doc);
  const flags = structuralFlags(doc);
  if (errors.length) {
    console.error("✗ structural validation failed:");
    for (const e of errors) console.error(`  - ${e}`);
    process.exit(1);
  }
  console.log("✓ structure valid");
  if (flags.length) {
    console.log(`! ${flags.length} structural flag(s) need reviewer disposition:`);
    for (const f of flags) console.log(`  ! [${f.code}] ${f.field}: ${f.message}`);
  } else console.log("✓ no structural flags");
  if (checkOnly) return;

  const today = torontoToday();
  if (doc.snapshot_date !== today) {
    console.error(`✗ snapshot_date is ${doc.snapshot_date || "(missing)"} but today (Toronto) is ${today}.`);
    console.error(`  Set it, re-run freeze (which voids prior review), then publish.`);
    process.exit(1);
  }

  // --- new reviewer gate (legacy .md no longer accepted) ---
  const legacy = path.join(root, "review", `${today}.md`);
  const dir = path.join(root, "review", today);
  const candPath = path.join(dir, "candidate.json");
  const shaPath = path.join(dir, "candidate.sha256");
  const reviewPath = path.join(dir, "pm-review.json");
  const flagsPath = path.join(dir, "structural-flags.json");
  const missing = [candPath, shaPath, reviewPath, flagsPath].filter((p) => !fs.existsSync(p));
  if (missing.length) {
    console.error("✗ reviewer gate: frozen review bundle incomplete.");
    for (const m of missing) console.error(`  - missing ${path.relative(root, m)}`);
    if (fs.existsSync(legacy))
      console.error(`  NOTE: legacy review/${today}.md exists but is NO LONGER accepted (no SHA binding, self-review). Run: node scripts/freeze.mjs`);
    console.error("  Flow: node scripts/freeze.mjs -> reviewer writes pm-review.json (see review/REVIEWER_AGENT.md) -> npm run publish");
    process.exit(1);
  }

  const candBytes = fs.readFileSync(candPath, "utf8");
  const filedSha = fs.readFileSync(shaPath, "utf8").trim();
  if (shaHex(candBytes) !== filedSha) {
    console.error("✗ candidate.sha256 does not match candidate.json bytes — candidate was edited after freezing. Re-freeze.");
    process.exit(1);
  }
  if (shaHex(canonical(doc)) !== filedSha) {
    console.error("✗ data/current.json differs from frozen candidate (canonical sha mismatch).");
    console.error("  Any edit after freeze voids the review — re-run freeze with --force and re-review.");
    process.exit(1);
  }

  // delegate schema/severity/sha/role checks to the validator (with frozen flags for coverage)
  try {
    execSync(`node ${JSON.stringify(path.join(root, "scripts", "validate_pm_review.mjs"))} --candidate ${JSON.stringify(candPath)} --review ${JSON.stringify(reviewPath)} --flags ${JSON.stringify(flagsPath)} --require-approved`, { stdio: "inherit" });
  } catch {
    console.error("✗ reviewer gate: pm-review validation failed (see above).");
    process.exit(1);
  }
  // coverage against CURRENT flags (in case data drifted within same sha — belt and suspenders)
  const disp = JSON.parse(fs.readFileSync(reviewPath, "utf8")).flags_dispositioned || [];
  const uncovered = flags.filter((fl) => !disp.some((d) => d.code === fl.code && d.field === fl.field));
  if (uncovered.length) {
    console.error("✗ reviewer gate: current data has flags the review does not disposition:");
    for (const f of uncovered) console.error(`  - [${f.code}] ${f.field}`);
    process.exit(1);
  }

  const dirty = frontendDirty();
  if (dirty === null) console.warn("  ! git check skipped (not a git repo?) — ensure no frontend changes ride along");
  else if (dirty.length) {
    console.error("✗ data/frontend separation: frontend or scripts changed in working tree:");
    for (const f of dirty) console.error(`  - ${f}`);
    console.error("  Ship frontend in an independent PR; data publish must be data-only.");
    process.exit(1);
  }

  // publish EXACTLY the reviewed bytes
  const archivePath = path.join(dataDir, "archive", `${today}.json`);
  fs.mkdirSync(path.dirname(archivePath), { recursive: true });
  fs.writeFileSync(archivePath, candBytes);
  fs.writeFileSync(path.join(dataDir, "latest.json"), candBytes);
  const datesPath = path.join(dataDir, "dates.json");
  let dates = { latest: today, dates: [] };
  if (fs.existsSync(datesPath)) dates = JSON.parse(fs.readFileSync(datesPath, "utf8"));
  dates.latest = today;
  dates.dates = [...new Set([today, ...(dates.dates ?? [])])].sort().reverse();
  for (const d of dates.dates) {
    if (!fs.existsSync(path.join(dataDir, "archive", `${d}.json`)))
      console.warn(`  ! dates.json lists ${d} but archive/${d}.json is missing`);
  }
  fs.writeFileSync(datesPath, JSON.stringify(dates, null, 2) + "\n");
  console.log(`✓ published snapshot ${today} (bytes == reviewed candidate ${filedSha.slice(0, 12)}…)`);
}

main();
