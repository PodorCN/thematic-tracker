#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { randomUUID } from "node:crypto";

const aliases = new Map([
  ["no change", "hold"], ["25 bps increase", "hike25"],
  ["50+ bps increase", "hike50"], ["25 bps decrease", "cut25"],
  ["50+ bps decrease", "cut50"],
]);
function price(value) {
  if ((typeof value !== "number" && typeof value !== "string") ||
      (typeof value === "string" && value.trim() === "")) throw new Error("Missing price");
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0 || n > 1) throw new Error("Price outside [0,1]");
  return n;
}
function array(value) {
  const result = typeof value === "string" ? JSON.parse(value) : value;
  if (!Array.isArray(result)) throw new Error("Expected array");
  return result;
}
function timestamp(value) {
  if (typeof value !== "string" || !/(Z|[+-]\d{2}:\d{2})$/.test(value))
    throw new Error("Source timestamp requires timezone");
  const n = Date.parse(value);
  if (!Number.isFinite(n)) throw new Error("Invalid source timestamp");
  return n;
}
function torontoDate(value) {
  const parts = new Intl.DateTimeFormat("en-CA", {timeZone: "America/Toronto",
    year: "numeric", month: "2-digit", day: "2-digit"}).formatToParts(new Date(value));
  const p = Object.fromEntries(parts.map(x => [x.type, x.value]));
  return `${p.year}-${p.month}-${p.day}`;
}
export function normalizeProbs(cut, hold, hike) {
  if (![cut, hold, hike].every(n => Number.isFinite(n) && n >= 0))
    throw new Error("Invalid probability ladder");
  const total = cut + hold + hike;
  if (!(total > 0) || !Number.isFinite(total)) throw new Error("Empty or nonfinite probability ladder");
  const exact = [cut, hold, hike].map(n => n / total * 100);
  const units = exact.map(Math.floor);
  const order = [0, 1, 2].sort((a, b) => (exact[b] - units[b]) - (exact[a] - units[a]) || a - b);
  for (let i = 0, remaining = 100 - units.reduce((a, b) => a + b, 0); i < remaining; i++)
    units[order[i % 3]]++;
  return {cut: units[0] / 100, hold: units[1] / 100, hike: units[2] / 100};
}
export function configuredMarket(doc, bank) {
  const rows = (doc.betting?.[bank] ?? []).filter(x => x.platform === "Polymarket");
  if (rows.length !== 1 || !/^[a-z0-9-]+$/.test(rows[0].event_slug ?? ""))
    throw new Error(`Exactly one configured Polymarket slug required for ${bank}`);
  const meeting = doc.meetings?.[bank]?.next_meeting?.datetime_toronto;
  const meetingMs = timestamp(meeting);
  return {slug: rows[0].event_slug, meetingDate: torontoDate(meetingMs), meetingDatetime: meeting};
}
export function parsePolymarket(payload, {slug, meetingDate, meetingDatetime, now = Date.now()}) {
  const events = Array.isArray(payload) ? payload : [payload];
  if (events.length !== 1) throw new Error("Expected exactly one event");
  const ev = events[0];
  if (!ev || ev.slug !== slug || !Array.isArray(ev.markets)) throw new Error("Event identity mismatch");
  if (ev.closed !== false || ev.active === false || ev.archived === true)
    throw new Error("Event closed, archived, or not verified open");
  const end = timestamp(ev.endDate);
  // Gamma's settlement endDate is coarse metadata, not a central-bank announcement
  // time: current Fed closes at 23:59 Toronto, while BoC uses midnight UTC.
  // Require the configured meeting date in either representation; preserve the
  // actual announcement clock from separately verified official meeting data.
  const meetingMs = timestamp(meetingDatetime);
  if (torontoDate(meetingMs) !== meetingDate || meetingMs <= now ||
      ![torontoDate(end), new Date(end).toISOString().slice(0, 10)].includes(meetingDate))
    throw new Error("Event is not the upcoming meeting");
  const sourceTime = timestamp(ev.updatedAt);
  if (sourceTime > now + 5 * 60000 || now - sourceTime > 90 * 60000)
    throw new Error("Source timestamp stale or in the future");
  const legs = new Map();
  let priceAsOf = ev.updatedAt, priceTime = sourceTime;
  for (const m of ev.markets) {
    const key = aliases.get(String(m.groupItemTitle ?? "").normalize("NFKC").trim().replace(/\s+/g, " ").toLowerCase());
    if (!key) throw new Error("Unrecognized rate leg");
    if (legs.has(key)) throw new Error("Duplicate normalized rate leg");
    if (m.closed === true || m.active === false) throw new Error("Closed rate leg");
    const legTime = timestamp(m.updatedAt);
    if (legTime > now + 5 * 60000 || now - legTime > 90 * 60000)
      throw new Error("Rate leg timestamp stale or in the future");
    if (legTime < priceTime) { priceTime = legTime; priceAsOf = m.updatedAt; }
    // outcomePrices follows outcomes order; never assume Yes is the first element.
    const outcomes = array(m.outcomes), prices = array(m.outcomePrices);
    const yes = outcomes.map(x => String(x).trim().toLowerCase());
    if (outcomes.length !== 2 || prices.length !== 2 ||
        yes.filter(x => x === "yes").length !== 1 || yes.filter(x => x === "no").length !== 1)
      throw new Error("Ambiguous binary outcome mapping");
    const numericPrices = prices.map(price);
    if (Math.abs(numericPrices[0] + numericPrices[1] - 1) > .02)
      throw new Error("Binary outcome prices do not sum to one within 2 percentage points");
    // Preserve the established outcome-price basis; do not silently switch to bid/ask.
    legs.set(key, numericPrices[yes.indexOf("yes")]);
  }
  for (const key of aliases.values()) if (!legs.has(key)) throw new Error(`Missing rate leg: ${key}`);
  const rawTotal = [...legs.values()].reduce((a, b) => a + b, 0);
  if (Math.abs(rawTotal - 1) > .10) throw new Error("Mutually exclusive rate ladder deviates from one by more than 10 percentage points");
  const probabilities = normalizeProbs(legs.get("cut25") + legs.get("cut50"),
    legs.get("hold"), legs.get("hike25") + legs.get("hike50"));
  return {platform: "Polymarket", event_slug: slug,
    event_url: `https://polymarket.com/event/${slug}`, probabilities,
    status: "available", as_of: priceAsOf,
    volume: money(ev.volume), liquidity: money(ev.liquidity ?? ev.liquidityClob),
    note: `Outcome-price basis; oldest venue price timestamp ${priceAsOf}; event updatedAt ${ev.updatedAt}; not an order-book midpoint. ` +
      `Event settlement date checked in UTC/Toronto; settlement time is not the policy announcement time. ` +
      `Raw five-leg sum ${rawTotal.toFixed(6)} before normalization. ` +
      `Hold ${Math.round(probabilities.hold * 100)}%, Hike ${Math.round(probabilities.hike * 100)}%, Cut ${Math.round(probabilities.cut * 100)}%.`};
}
function money(value) {
  const n = Number(value);
  if (value == null || !Number.isFinite(n) || n < 0) return "unverified";
  return n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `$${(n / 1e3).toFixed(1)}k` : `$${Math.round(n)}`;
}
export async function fetchPolymarket(config, {fetchImpl = globalThis.fetch, now = Date.now()} = {}) {
  const url = `https://gamma-api.polymarket.com/events?slug=${encodeURIComponent(config.slug)}`;
  const res = await fetchImpl(url, {headers: {"User-Agent": "RatesDecisions/1.0"},
    signal: AbortSignal.timeout(20000)});
  if (!res.ok) throw new Error(`Polymarket HTTP ${res.status}`);
  return parsePolymarket(await res.json(), {...config, now});
}
export function mergeResults(doc, results) {
  if (!results.fed || !results.boc) throw new Error("Both banks required; refusing partial update");
  const next = structuredClone(doc);
  for (const bank of ["fed", "boc"]) {
    const config = configuredMarket(doc, bank);
    if (results[bank].event_slug !== config.slug) throw new Error("Result slug mismatch");
    next.betting[bank] = doc.betting[bank].map(x => x.platform === "Polymarket" ? results[bank] : x);
  }
  return next;
}
export function writeCandidate(candidatePath, doc, {write = fs.writeFileSync} = {}) {
  const temporary = path.join(path.dirname(candidatePath), `.betting-${randomUUID()}.tmp`);
  const contents = JSON.stringify(doc, null, 2) + "\n";
  let fd;
  try {
    fd = fs.openSync(temporary, "wx", 0o600);
    write(fd, contents); fs.fsyncSync(fd); fs.closeSync(fd); fd = undefined;
    if (fs.readFileSync(temporary, "utf8") !== contents) throw new Error("Candidate readback failed");
    // Link only completely written bytes; unlike rename, this refuses an
    // existing destination atomically. Unsupported filesystems fail closed.
    fs.linkSync(temporary, candidatePath);
  } finally {
    if (fd !== undefined) fs.closeSync(fd);
    if (fs.existsSync(temporary)) fs.unlinkSync(temporary);
  }
}
async function main() {
  if (process.argv.includes("--write")) throw new Error("Direct --write removed: use --candidate, then the independently reviewed operator workflow");
  if (process.argv.slice(2).some(x => x !== "--candidate")) throw new Error("Unsupported argument");
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
  const currentPath = path.join(root, "data", "current.json");
  const original = fs.readFileSync(currentPath, "utf8"), doc = JSON.parse(original), results = {};
  for (const bank of ["fed", "boc"]) results[bank] = await fetchPolymarket(configuredMarket(doc, bank));
  const next = mergeResults(doc, results);
  if (process.argv.includes("--candidate")) {
    // Arbitrary operator writers do not share an ownership protocol. A separate
    // candidate avoids racing or truncating current.json; promotion stays gated.
    const candidatePath = path.join(root, "data", "betting-candidate.json");
    writeCandidate(candidatePath, next);
    console.log(`Candidate saved to ${candidatePath}; current.json unchanged; independent operator review required.`);
  }
  console.log(JSON.stringify({mode: process.argv.includes("--candidate") ? "candidate_only_current_unchanged" : "read_only", betting: results}, null, 2));
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href)
  main().catch(err => {console.error(`Fatal: ${err.message}`); process.exitCode = 1;});
