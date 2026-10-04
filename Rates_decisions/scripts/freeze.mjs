#!/usr/bin/env node
/**
 * freeze.mjs — freezes data/current.json into an immutable review candidate.
 *
 *   node scripts/freeze.mjs            # freeze for today (Toronto)
 *   node scripts/freeze.mjs --force    # re-freeze (invalidates prior review)
 *
 * Writes:
 *   review/<today>/candidate.json  (canonical bytes: parsed + 2-space + \n)
 *   review/<today>/candidate.sha256
 *   review/<today>/structural-flags.json (machine flags the reviewer must disposition)
 *
 * Rule: after freeze, ANY edit to data/current.json invalidates the review
 * (publish compares canonical sha). Re-freeze instead of editing the candidate.
 */
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const force = process.argv.includes("--force");

function torontoToday() {
  const p = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Toronto", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date());
  const m = Object.fromEntries(p.map((x) => [x.type, x.value]));
  return `${m.year}-${m.month}-${m.day}`;
}

export function canonical(doc) {
  return JSON.stringify(doc, null, 2) + "\n";
}

// structural flags live here so freeze + publish share one definition.
// Returns flags: [{code, field, message}] — items a human must disposition.
export function structuralFlags(doc) {
  const flags = [];
  const push = (code, field, message) => flags.push({ code, field, message });

  const PRIMARY = [
    [/statistics canada/i, "statcan.gc.ca", "Statistics Canada"],
    [/bank of canada/i, "bankofcanada.ca", "Bank of Canada"],
    [/\bBLS\b|bureau of labor/i, "bls.gov", "BLS"],
    [/\bBEA\b|bureau of economic/i, "bea.gov", "BEA"],
    [/federal reserve|fomc|ny fed|new york fed/i, "federalreserve.gov|newyorkfed.org", "Federal Reserve"],
    [/\bCME\b|fedwatch/i, "cmegroup.com", "CME"],
  ];
  for (const bank of ["fed", "boc"]) {
    const all = [...(doc.drivers?.[bank]?.hawkish ?? []), ...(doc.drivers?.[bank]?.dovish ?? [])];
    for (const d of all) {
      const src = String(d.source || "");
      const url = String(d.source_url || "");
      const m = src.match(/^(.*?)\s*\(via\b/i);
      const claimedPrimary = (m ? m[1] : src).trim();
      for (const [re, domains, label] of PRIMARY) {
        if (re.test(claimedPrimary)) {
          const ok = domains.split("|").some((dom) => url.includes(dom));
          if (!ok) push("primary_source_mismatch", `drivers.${bank}.${d.id}.source_url`,
            `${d.id} claims "${claimedPrimary}" (${label}) but URL is ${url || "(missing)"} — swap to primary or restate source as secondary and down-weight`);
          break;
        }
      }
      if (!/^https:\/\//.test(url)) push("bad_source_url", `drivers.${bank}.${d.id}.source_url`, `${d.id} source_url must be https:// (got "${url}")`);
      if (d.weight >= 5 && (!d.market_validation || d.market_validation === "unverified"))
        push("high_weight_no_validation", `drivers.${bank}.${d.id}.weight`,
          `${d.id} weight=${d.weight} without market validation — need FedWatch pp / 2Y bp repricing number or lower the weight`);
    }
    // same release split across both sides without facet justification
    const byUrl = new Map();
    for (const d of all) {
      const u = String(d.source_url || "");
      if (!u) continue;
      if (!byUrl.has(u)) byUrl.set(u, []);
      byUrl.get(u).push(d);
    }
    for (const [u, ds] of byUrl) {
      const sides = new Set(ds.map((d) => d.direction));
      if (ds.length > 1 && sides.has(1) && sides.has(-1)) {
        const facets = ds.map((d) => d.facet).filter(Boolean);
        const distinct = new Set(facets).size === ds.length && facets.length === ds.length;
        if (!distinct) push("split_release_no_facet", `drivers.${bank}.[${ds.map((d) => d.id).join(",")}]`,
          `same URL ${u} used on BOTH sides (${ds.map((d) => d.id).join(" vs ")}) without distinct facet fields — merge or add facet + separate transmission chains`);
      }
    }
  }
  // pricing freshness + calendar hygiene
  const asOf = doc.as_of ? new Date(doc.as_of) : null;
  for (const bank of ["fed", "boc"]) {
    const pa = doc.meetings?.[bank]?.pricing?.as_of;
    if (pa && asOf && !Number.isNaN(asOf.getTime())) {
      const days = (asOf - new Date(pa)) / 864e5;
      if (days > 4) push("stale_pricing", `meetings.${bank}.pricing.as_of`, `${bank} pricing as_of ${pa} is ${days.toFixed(1)}d older than snapshot as_of — re-pull or mark unavailable`);
    }
  }
  const calUrls = new Map();
  for (const e of doc.calendar ?? []) {
    if (!/^https:\/\//.test(String(e.source_url || ""))) push("bad_source_url", `calendar.${e.event}.source_url`, `calendar "${e.event}" needs an https source_url`);
    if (e.source_url) calUrls.set(e.source_url, [...(calUrls.get(e.source_url) || []), e.event]);
  }
  for (const [u, evs] of calUrls) {
    if (evs.length >= 5 && /economic-calendar\/?$/.test(u))
      push("generic_calendar_source", "calendar.source_url", `${evs.length} rows share generic homepage ${u} — link each row to its consensus row or mark forecast unverified with a named source`);
  }
  return flags;
}

function main() {
  const today = torontoToday();
  const curPath = path.join(root, "data", "current.json");
  const doc = JSON.parse(fs.readFileSync(curPath, "utf8"));
  if (doc.snapshot_date !== today) {
    console.error(`✗ data/current.json snapshot_date is ${doc.snapshot_date || "(missing)"} but today (Toronto) is ${today}.`);
    console.error(`  Set snapshot_date to ${today} before freezing so the hash covers the publish date.`);
    process.exit(1);
  }
  const dir = path.join(root, "review", today);
  fs.mkdirSync(dir, { recursive: true });
  const candPath = path.join(dir, "candidate.json");
  if (fs.existsSync(candPath) && !force) {
    console.error(`✗ ${path.relative(root, candPath)} already exists. Candidate is immutable — edit data/current.json then re-run with --force (old review is void).`);
    process.exit(1);
  }
  const bytes = canonical(doc);
  fs.writeFileSync(candPath, bytes);
  const sha = crypto.createHash("sha256").update(bytes).digest("hex");
  fs.writeFileSync(path.join(dir, "candidate.sha256"), sha + "\n");
  const flags = structuralFlags(doc);
  fs.writeFileSync(path.join(dir, "structural-flags.json"), JSON.stringify(flags, null, 2) + "\n");
  console.log(`✓ froze review/${today}/candidate.json (sha ${sha.slice(0, 12)}…, ${flags.length} structural flag(s))`);
  if (flags.length) for (const f of flags) console.log(`  ! [${f.code}] ${f.field}`);
  console.log(`  next: reviewer writes review/${today}/pm-review.json covering every flag, then npm run publish`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url))) main();
