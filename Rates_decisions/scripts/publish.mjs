#!/usr/bin/env node
/**
 * publish.mjs — Rates_decisions publish + validation gate.
 *
 *   node scripts/publish.mjs --check   # validate data/current.json only
 *   node scripts/publish.mjs           # validate, then publish snapshot
 *
 * Publish = current.json -> data/archive/<today Toronto>.json + data/latest.json,
 * then update data/dates.json (descending). Today's archive file may be
 * overwritten on same-day re-runs; older archives are never touched.
 *
 * Gate: refuses to publish unless review/<today>.md exists.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dataDir = path.join(root, "data");
const checkOnly = process.argv.includes("--check");

function torontoToday() {
  const p = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Toronto",
    year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date());
  const m = Object.fromEntries(p.map((x) => [x.type, x.value]));
  return `${m.year}-${m.month}-${m.day}`;
}

function fail(msg, errors) {
  errors.push(msg);
  return errors;
}

function validate(doc) {
  const errors = [];
  const text = JSON.stringify(doc);
  if (/NaN|Infinity/.test(text)) fail("JSON contains NaN/Infinity", errors);

  for (const bank of ["fed", "boc"]) {
    const p = doc.meetings?.[bank]?.pricing;
    if (!p) { fail(`meetings.${bank}.pricing missing`, errors); continue; }
    if (p.probabilities !== null) {
      const vals = Object.values(p.probabilities ?? {});
      const sum = vals.reduce((a, b) => a + b, 0);
      if (vals.some((v) => typeof v !== "number" || !isFinite(v) || v < 0 || v > 1))
        fail(`${bank}: probability out of [0,1]`, errors);
      if (sum < 0.99 || sum > 1.01)
        fail(`${bank}: probabilities sum ${sum.toFixed(3)}, must be 0.99-1.01`, errors);
    } else if (p.probability_status !== "unavailable") {
      fail(`${bank}: null probabilities require probability_status "unavailable"`, errors);
    }

    const dr = doc.drivers?.[bank];
    if (!dr) { fail(`drivers.${bank} missing`, errors); continue; }
    const all = [...(dr.hawkish ?? []), ...(dr.dovish ?? [])];
    const ids = new Set();
    let signed = 0, wSum = 0;
    for (const d of all) {
      if (ids.has(d.id)) fail(`${bank}: duplicate driver id "${d.id}"`, errors);
      ids.add(d.id);
      if (d.direction !== 1 && d.direction !== -1) fail(`${bank}/${d.id}: direction must be ±1`, errors);
      if (!Number.isInteger(d.weight) || d.weight < 1 || d.weight > 10)
        fail(`${bank}/${d.id}: weight must be integer 1-10`, errors);
      if (d.weight >= 7 && (d.market_validation === "unverified" || !d.market_validation))
        fail(`${bank}/${d.id}: weight ≥7 requires market validation evidence`, errors);
      signed += d.direction * d.weight;
      wSum += Math.abs(d.weight);
    }
    if (all.length && wSum / all.length > 5)
      fail(`${bank}: mean |weight| ${(wSum / all.length).toFixed(1)} > 5 → score inflation`, errors);
    const declared = doc.total_score?.[bank]?.base_total;
    const recomputed = Math.max(-10, Math.min(10, signed));
    if (declared !== recomputed)
      fail(`${bank}: total_score.base_total=${declared} but drivers sum to ${recomputed}`, errors);
  }

  for (const e of doc.calendar ?? []) {
    if (e.date_only) {
      if (e.datetime_toronto || e.datetime_utc)
        fail(`calendar "${e.event}": date_only events must set datetimes to null`, errors);
    } else if (!e.datetime_toronto || !e.datetime_utc) {
      fail(`calendar "${e.event}": timed releases require datetime_toronto + datetime_utc`, errors);
    }
  }
  return errors;
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
  if (errors.length) {
    console.error("✗ validation failed:");
    for (const e of errors) console.error(`  - ${e}`);
    process.exit(1);
  }
  console.log("✓ current.json valid");
  if (checkOnly) return;

  const today = torontoToday();
  const reviewPath = path.join(root, "review", `${today}.md`);
  if (!fs.existsSync(reviewPath)) {
    console.error(`✗ reviewer gate: review/${today}.md missing. Write the reviewer report first (see review/TEMPLATE.md).`);
    process.exit(1);
  }
  const verdict = fs.readFileSync(reviewPath, "utf8");
  if (!/verdict:\s*APPROVED/i.test(verdict)) {
    console.error(`✗ reviewer gate: review/${today}.md does not contain "Verdict: APPROVED".`);
    process.exit(1);
  }

  doc.snapshot_date = today;
  const out = JSON.stringify(doc, null, 2) + "\n";
  const archivePath = path.join(dataDir, "archive", `${today}.json`);
  fs.mkdirSync(path.dirname(archivePath), { recursive: true });
  fs.writeFileSync(archivePath, out);
  fs.writeFileSync(path.join(dataDir, "latest.json"), out);

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

  console.log(`✓ published snapshot ${today}`);
  console.log(`  archive/${today}.json, latest.json, dates.json updated`);
}

main();
