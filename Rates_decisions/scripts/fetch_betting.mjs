#!/usr/bin/env node
/**
 * fetch_betting.mjs — Fetches live prediction market odds from Polymarket & Kalshi.
 *
 * Usage:
 *   node scripts/fetch_betting.mjs          # fetch & print live odds
 *   node scripts/fetch_betting.mjs --write  # fetch, print & update data/current.json
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const currentPath = path.join(root, "data", "current.json");
const shouldWrite = process.argv.includes("--write");

const POLY_SLUGS = {
  fed: "fed-decision-in-october-20260617190323537",
  boc: "bank-of-canada-decision-in-october-20260715203359314",
};

function fmtMoney(n) {
  const val = Number(n);
  if (!Number.isFinite(val) || val < 0) return "unverified";
  if (val >= 1e6) return "$" + (val / 1e6).toFixed(1) + "M";
  if (val >= 1e3) return "$" + (val / 1e3).toFixed(1) + "k";
  return "$" + Math.round(val);
}

function normalizeProbs(cut, hold, hike) {
  const tot = cut + hold + hike || 1;
  const c = Math.max(0, Math.round((cut / tot) * 100) / 100);
  const hk = Math.max(0, Math.round((hike / tot) * 100) / 100);
  const hd = Math.max(0, Math.round((1 - c - hk) * 100) / 100);
  return { cut: c, hold: hd, hike: hk };
}

function torontoToday() {
  const p = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Toronto",
    year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date());
  const m = Object.fromEntries(p.map((x) => [x.type, x.value]));
  return `${m.year}-${m.month}-${m.day}`;
}

async function fetchPolymarket(slug) {
  const url = `https://gamma-api.polymarket.com/events?slug=${encodeURIComponent(slug)}`;
  const res = await fetch(url, { headers: { "User-Agent": "RatesDecisions/1.0" } });
  if (!res.ok) throw new Error(`Polymarket HTTP ${res.status}`);
  const payload = await res.json();
  const ev = Array.isArray(payload) ? payload[0] : payload;
  if (!ev || !Array.isArray(ev.markets)) throw new Error("No markets found in event");

  let cut = 0, hold = 0, hike = 0;
  for (const m of ev.markets) {
    let prices = [];
    try { prices = JSON.parse(m.outcomePrices || "[]"); } catch {}
    const yes = Number(prices[0]) || 0;
    const txt = `${m.groupItemTitle || ""} ${m.question || ""}`.toLowerCase();
    if (/decrease/.test(txt)) cut += yes;
    else if (/no[\s-]?change/.test(txt)) hold += yes;
    else if (/increase/.test(txt)) hike += yes;
  }

  const probs = normalizeProbs(cut, hold, hike);
  const vol = fmtMoney(ev.volume);
  const liq = fmtMoney(ev.liquidity || ev.liquidityClob);
  const asOf = ev.updatedAt ? ev.updatedAt.slice(0, 10) : torontoToday();

  return {
    platform: "Polymarket",
    event_slug: slug,
    event_url: `https://polymarket.com/event/${slug}`,
    probabilities: probs,
    status: "available",
    volume: vol,
    liquidity: liq,
    as_of: asOf,
    note: `Live odds: Hold ${Math.round(probs.hold * 100)}%, Hike ${Math.round(probs.hike * 100)}%, Cut ${Math.round(probs.cut * 100)}%.`,
  };
}

async function main() {
  console.log("Fetching live prediction market odds from Polymarket...\n");

  let fedPoly, bocPoly;

  try {
    fedPoly = await fetchPolymarket(POLY_SLUGS.fed);
    console.log(`✓ Fed Polymarket:   Cut ${(fedPoly.probabilities.cut * 100).toFixed(0)}% · Hold ${(fedPoly.probabilities.hold * 100).toFixed(0)}% · Hike ${(fedPoly.probabilities.hike * 100).toFixed(0)}%  (Vol ${fedPoly.volume}, Liq ${fedPoly.liquidity})`);
  } catch (err) {
    console.warn(`✗ Fed Polymarket failed: ${err.message}`);
  }

  try {
    bocPoly = await fetchPolymarket(POLY_SLUGS.boc);
    console.log(`✓ BOC Polymarket:   Cut ${(bocPoly.probabilities.cut * 100).toFixed(0)}% · Hold ${(bocPoly.probabilities.hold * 100).toFixed(0)}% · Hike ${(bocPoly.probabilities.hike * 100).toFixed(0)}%  (Vol ${bocPoly.volume}, Liq ${bocPoly.liquidity})`);
  } catch (err) {
    console.warn(`✗ BOC Polymarket failed: ${err.message}`);
  }

  if (!shouldWrite) {
    console.log("\nTo write these live odds into data/current.json, run:");
    console.log("  node scripts/fetch_betting.mjs --write");
    return;
  }

  const doc = JSON.parse(fs.readFileSync(currentPath, "utf8"));
  if (!doc.betting) doc.betting = { fed: [], boc: [] };

  if (fedPoly) doc.betting.fed = [fedPoly];
  if (bocPoly) doc.betting.boc = [bocPoly];

  fs.writeFileSync(currentPath, JSON.stringify(doc, null, 2) + "\n");
  console.log(`\n✓ Successfully updated ${currentPath} with live odds!`);
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
