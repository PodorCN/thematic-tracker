/* The Rate Decision Journal — renders data/latest.json (or archive snapshot). No hardcoded data. */
"use strict";

const TZ = "America/Toronto";
const $ = (s) => document.querySelector(s);

/* ---------- helpers ---------- */

async function loadJSON(url) {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return r.json();
}

function fmtToronto(iso) {
  if (!iso) return "date only";
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", hour12: false,
  }).formatToParts(new Date(iso));
  const p = Object.fromEntries(parts.map((x) => [x.type, x.value]));
  return `${p.year}-${p.month}-${p.day} ${p.hour}:${p.minute} Toronto`;
}

function daysBetween(a, b) {
  return (new Date(b) - new Date(a)) / 86400000;
}

function countdown(targetUtc) {
  const ms = new Date(targetUtc) - Date.now();
  if (ms <= 0) return "passed";
  const d = Math.floor(ms / 86400000);
  const h = Math.floor((ms % 86400000) / 3600000);
  return d > 0 ? `in ${d}d ${h}h` : `in ${h}h`;
}

function decayFactor(publishedAt, asOf) {
  const age = daysBetween(publishedAt, asOf);
  if (age <= 7) return 1.0;
  if (age <= 14) return 0.75;
  if (age <= 30) return 0.5;
  return 0.25;
}

function bandFor(t) {
  if (t >= 7) return "strong hike lean";
  if (t > 3) return "lean hike";
  if (t >= -3) return "hold";
  if (t > -7) return "lean cut";
  return "strong cut lean";
}

function pct(x) { return `${Math.round(x * 100)}%`; }

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function srcLink(label, url) {
  return url ? `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(label)}</a>` : esc(label);
}

const FLAGS = { USD: "🇺🇸", CAD: "🇨🇦" };

function importanceDots(n) {
  const on = Math.max(0, Math.min(3, n ?? 0));
  return `<span class="imp">${"●".repeat(on)}<span class="off">${"●".repeat(3 - on)}</span></span>`;
}

/* ---------- validation (audit) ---------- */

function validate(data) {
  const warns = [];
  for (const bank of ["fed", "boc"]) {
    const p = data.meetings?.[bank]?.pricing;
    if (p && p.probabilities) {
      const vals = Object.values(p.probabilities);
      const sum = vals.reduce((a, b) => a + b, 0);
      if (vals.some((v) => typeof v !== "number" || !isFinite(v) || v < 0 || v > 1))
        warns.push(`${bank.toUpperCase()} pricing: probability out of range`);
      if (sum < 0.99 || sum > 1.01)
        warns.push(`${bank.toUpperCase()} pricing: probs sum ${sum.toFixed(3)} ≠ 1`);
    }
    const dr = data.drivers?.[bank];
    if (dr) {
      const all = [...dr.hawkish, ...dr.dovish];
      const ids = new Set();
      let wSum = 0, signed = 0;
      for (const d of all) {
        if (ids.has(d.id)) warns.push(`${bank.toUpperCase()} duplicate driver id ${d.id}`);
        ids.add(d.id);
        if (!Number.isInteger(d.weight) || d.weight < 1 || d.weight > 10)
          warns.push(`${bank.toUpperCase()} driver ${d.id}: weight ${d.weight} not int 1-10`);
        if (d.weight >= 7) warns.push(`${bank.toUpperCase()} driver ${d.id}: weight ${d.weight} requires 2+ sources + market validation`);
        wSum += Math.abs(d.weight);
        signed += d.direction * d.weight;
      }
      if (all.length) {
        const mean = wSum / all.length;
        if (mean > 5) warns.push(`${bank.toUpperCase()} mean |weight| ${mean.toFixed(1)} > 5 → inflation flag`);
      }
      const declared = data.total_score?.[bank]?.base_total;
      const clamped = Math.max(-10, Math.min(10, signed));
      if (declared !== undefined && declared !== clamped)
        warns.push(`${bank.toUpperCase()} total_score.base_total ${declared} ≠ recomputed ${clamped}`);
    }
  }
  return warns;
}

/* ---------- renderers ---------- */

function renderHeader(data) {
  const fed = data.meetings.fed, boc = data.meetings.boc;
  $("#masthead-date").textContent = fmtToronto(data.as_of);
  $("#hdr-meta").innerHTML =
    `As of <strong>${fmtToronto(data.as_of)}</strong> &nbsp;·&nbsp; ` +
    `Next: <strong>Fed ${esc(fed.next_meeting.date_label)}</strong> ${countdown(fed.next_meeting.datetime_utc)} ` +
    `&nbsp;+&nbsp; <strong>BOC ${esc(boc.next_meeting.date_label)}</strong> ${countdown(boc.next_meeting.datetime_utc)}`;
}

function probBars(mProbs, polyProbs) {
  const rows = [["hike", "Hike 25bp"], ["hold", "Hold"], ["cut", "Cut 25bp"]];
  const hasPoly = Boolean(polyProbs);
  const legendHtml = hasPoly
    ? `<div class="bars-legend S">
        <span class="legend-item"><span class="legend-swatch mkt"></span> Market implied</span>
        <span class="legend-item"><span class="legend-swatch poly"></span> Polymarket</span>
      </div>`
    : "";

  return `<div class="bars">` + legendHtml + rows.map(([k, label]) => {
    const mVal = mProbs?.[k] ?? 0;
    const mPct = (mVal * 100).toFixed(1);
    const pVal = polyProbs?.[k];
    const hasP = pVal !== undefined && pVal !== null;
    const pPct = hasP ? (pVal * 100).toFixed(1) : null;

    return `
    <div class="bar-row">
      <div class="bar-label">${label}</div>
      <div class="bar-track">
        <div class="bar-fill ${k}" style="width:${mPct}%"></div>
        ${hasP ? `
        <div class="bar-poly-overlay" style="width:${pPct}%">
          <div class="poly-needle" title="Polymarket: ${pct(pVal)}"></div>
        </div>` : ""}
      </div>
      <div class="bar-pcts">
        <span class="pct-mkt" title="Market implied">${pct(mVal)}</span>
        ${hasP ? `<span class="pct-poly" title="Polymarket">${pct(pVal)}</span>` : ""}
      </div>
    </div>`;
  }).join("") + `</div>`;
}

function staleBadge(asOf, snapDate) {
  if (!asOf) return "";
  const age = daysBetween(asOf, snapDate);
  if (age > 7) return `<span class="badge warn">stale ${Math.round(age)}d</span>`;
  return "";
}

function resolveBetUrl(b) {
  if (!b) return "";
  if (b.event_url && b.event_url !== "https://polymarket.com") {
    return b.event_url;
  }
  if (b.platform === "Polymarket") {
    if (b.event_slug) return `https://polymarket.com/event/${b.event_slug}`;
    return "https://polymarket.com";
  }
  return b.event_url || "";
}

/* Section I: market pricing + betting odds overlay, one card per bank */
function renderExpectations(data) {
  $("#expectations").innerHTML = ["fed", "boc"].map((bank) => {
    const m = data.meetings[bank];
    const p = m.pricing;
    const poly = data.betting?.[bank]?.find((b) => b.platform === "Polymarket");
    const polyProbs = poly?.probabilities ?? null;
    let pricingBody;
    if (p.probability_status === "unavailable" || !p.probabilities) {
      const proxy = p.observable_proxy;
      pricingBody = `<div class="M">Probability distribution <span class="badge na">unavailable</span></div>
        <div class="S meta-line">${proxy
          ? `Observable proxy: ${esc(proxy.instrument)} @ ${esc(proxy.price)} (${esc(proxy.tenor)}) — no single-meeting probability inferred.`
          : "No clean single-meeting distribution; nothing inferred from quarterly contracts."}</div>`;
    } else {
      pricingBody = probBars(p.probabilities, polyProbs) +
        `<div class="S meta-line">Implied rate: ${p.implied_rate_before}% → <strong>${p.implied_rate_after}%</strong> after meeting</div>`;
    }
    return `<div class="card">
      <h3>${esc(m.label)} ${staleBadge(p.as_of, data.snapshot_date)}</h3>
      <h4>Market pricing</h4>
      ${pricingBody}
      <div class="S meta-line">Source: ${srcLink(p.source, p.source_url)} · as of ${esc(p.as_of ?? "n/a")}</div>
      ${poly ? `<div class="S meta-line">Polymarket: ${srcLink("Event contract", resolveBetUrl(poly))}${poly.status === "live" ? ` <span class="badge ok">live</span>` : poly.status === "stale" ? ` <span class="badge warn">stale</span>` : ""} · as of ${esc(poly.as_of ?? "n/a")} · Vol ${esc(poly.volume ?? "n/a")} · Liq ${esc(poly.liquidity ?? "n/a")}</div>` : ""}
      <div class="S meta-line">Last meeting ${esc(m.last_meeting.date)}: ${esc(m.last_meeting.decision)}</div>
    </div>`;
  }).join("");
}

function driverCard(d, side, asOf) {
  const f = decayFactor(d.published_at, asOf);
  const eff = (d.direction * d.weight * f);
  const effTxt = f < 1 ? ` · eff ${eff > 0 ? "+" : ""}${eff.toFixed(1)} (decay ×${f})` : "";
  const sign = d.direction > 0 ? "pos" : "neg";
  const wb = d.weight_breakdown;
  return `<div class="driver ${side}">
    <div class="driver-head">
      <span class="driver-title">${esc(d.title)}</span>
      <span class="w-badge ${sign}">${d.direction > 0 ? "+" : "−"}${d.weight}</span>
    </div>
    <div class="driver-summary">${esc(d.summary)}</div>
    <div class="driver-audit S">
      <div class="kv">${esc(d.data.actual)}${d.data.forecast && d.data.forecast !== "unverified" && d.data.forecast !== "n/a" ? ` vs ${esc(d.data.forecast)} exp` : ""} · prev ${esc(d.data.previous)} · ${esc(d.data.delta_label)}</div>
      <div class="kv">${esc(d.reason)}</div>
      <div class="kv">Market validation: ${esc(d.market_validation)}</div>
      <div class="kv">${srcLink(d.source, d.source_url)} · published ${esc(d.published_at)}${effTxt}</div>
      <div class="chips">
        <span class="chip">deviation ${wb.deviation}</span>
        <span class="chip">importance ${wb.importance}</span>
        <span class="chip">surprise ${wb.surprise}</span>
        <span class="chip">Σ ${wb.total}</span>
      </div>
    </div>
  </div>`;
}

function scoreBlock(data, bank) {
  const dr = data.drivers[bank];
  const all = [...dr.hawkish, ...dr.dovish];
  const base = all.reduce((a, d) => a + d.direction * d.weight, 0);
  const eff = all.reduce((a, d) => a + d.direction * d.weight * decayFactor(d.published_at, data.as_of), 0);
  const clamp = (x) => Math.max(-10, Math.min(10, x));
  const total = clamp(Math.round(eff * 2) / 2);
  const band = bandFor(total);
  const numCls = total > 0 ? "pos" : total < 0 ? "neg" : "zero";
  const markerPct = ((total + 10) / 20) * 100;

  const probs = data.meetings[bank].pricing.probabilities;
  let badge = "";
  if (probs) {
    const leader = Object.entries(probs).sort((a, b) => b[1] - a[1])[0][0];
    const aligned =
      (leader === "hike" && total > 3) ||
      (leader === "cut" && total < -3) ||
      (leader === "hold" && Math.abs(total) <= 3);
    badge = aligned
      ? ""
      : `<span class="badge warn">⚠ divergence vs pricing (${leader})</span>`;
  }

  return `<div class="score-row">
    <div class="score-num ${numCls}">${total > 0 ? "+" : ""}${total}</div>
    <div>
      <div class="score-band">${band}</div>
      ${badge}
    </div>
    <div style="flex:1; min-width:220px">
      <div class="gauge"><div class="gauge-marker" style="left:${markerPct}%"></div></div>
      <div class="gauge-ticks S"><span>−10 cut</span><span>0</span><span>+10 hike</span></div>
    </div>
  </div>`;
}

function renderDrivers(data) {
  $("#drivers").innerHTML = ["fed", "boc"].map((bank) => {
    const dr = data.drivers[bank];
    const sortW = (arr) => [...arr].sort((a, b) => Math.abs(b.weight) - Math.abs(a.weight));
    return `<div class="bank-block">
      <h3 class="bank-name">${esc(data.meetings[bank].label)} — since ${esc(data.meetings[bank].last_meeting.date)}</h3>
      ${scoreBlock(data, bank)}
      <div class="driver-cols">
        <div class="driver-col dovish">
          <h4>◀ Dovish (against hike)</h4>
          ${sortW(dr.dovish).map((d) => driverCard(d, "dovish", data.as_of)).join("")}
        </div>
        <div class="driver-col hawkish">
          <h4>Hawkish (for hike) ▶</h4>
          ${sortW(dr.hawkish).map((d) => driverCard(d, "hawkish", data.as_of)).join("")}
        </div>
      </div>
    </div>`;
  }).join("");
}

function renderCalendar(data) {
  const asOf = new Date(data.as_of);
  const rows = data.calendar
    .filter((e) => e.impact === "HIGH")
    .filter((e) => e.date_only ? new Date(e.date_toronto + "T23:59:59") >= asOf : new Date(e.datetime_utc) >= asOf)
    .sort((a, b) => new Date(a.datetime_utc || a.date_toronto) - new Date(b.datetime_utc || b.date_toronto));
  const hasForecast = rows.some((e) => e.forecast && e.forecast !== "unverified" && e.forecast !== "n/a");
  $("#calendar").innerHTML = `<table class="cal">
    <thead><tr>
      <th>Date (Toronto)</th><th></th><th>Event</th><th>Imp.</th>${hasForecast ? "<th>Forecast</th>" : ""}<th>Previous</th>
    </tr></thead>
    <tbody>${rows.map((e) => {
      const fc = (e.forecast && e.forecast !== "unverified" && e.forecast !== "n/a") ? esc(e.forecast) : "";
      return `<tr>
      <td style="white-space:nowrap">${e.date_only ? esc(e.date_toronto) + " (date only)" : fmtToronto(e.datetime_utc)}</td>
      <td class="flag">${FLAGS[e.currency] ?? esc(e.currency)}</td>
      <td>${esc(e.event)}</td>
      <td>${importanceDots(e.importance)}</td>
      ${hasForecast ? `<td>${fc}</td>` : ""}
      <td>${esc(e.previous ?? "")}</td>
    </tr>`; }).join("")}</tbody>
  </table>`;
}

/* ---------- boot ---------- */

async function fetchLiveOdds(data) {
  let changed = false;

  for (const bank of ["fed", "boc"]) {
    const poly = data.betting?.[bank]?.find((b) => b.platform === "Polymarket" && b.event_slug);
    if (poly) {
      try {
        const res = await fetch(`https://gamma-api.polymarket.com/events?slug=${encodeURIComponent(poly.event_slug)}`, { cache: "no-store" });
        if (res.ok) {
          const evs = await res.json();
          const ev = Array.isArray(evs) ? evs[0] : evs;
          if (ev && Array.isArray(ev.markets)) {
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
            const tot = cut + hold + hike || 1;
            const c = Math.max(0, Math.round((cut / tot) * 100) / 100);
            const hk = Math.max(0, Math.round((hike / tot) * 100) / 100);
            const hd = Math.max(0, Math.round((1 - c - hk) * 100) / 100);
            poly.probabilities = { cut: c, hold: hd, hike: hk };
            poly.status = "live";
            if (ev.volume) {
              const v = Number(ev.volume);
              poly.volume = v >= 1e6 ? "$" + (v / 1e6).toFixed(1) + "M" : "$" + Math.round(v);
            }
            if (ev.liquidity || ev.liquidityClob) {
              const l = Number(ev.liquidity || ev.liquidityClob);
              poly.liquidity = l >= 1e6 ? "$" + (l / 1e6).toFixed(1) + "M" : "$" + Math.round(l);
            }
            poly.as_of = fmtToronto(new Date().toISOString());
            changed = true;
          }
        }
      } catch (e) {
        // offline or network failure: keep current snapshot
      }
    }
  }

  if (changed) {
    renderExpectations(data);
  }
}

async function renderSnapshot(data) {
  const warns = validate(data);
  $("#warnings").innerHTML = warns.map((w) => `<span class="warn">⚠ ${esc(w)}</span>`).join("");
  renderHeader(data);
  renderExpectations(data);
  renderDrivers(data);
  renderCalendar(data);
}

async function boot() {
  const picker = $("#date-picker");
  let dates = { latest: null, dates: [] };
  try { dates = await loadJSON("data/dates.json"); } catch { /* single-snapshot fallback */ }

  const opts = [`<option value="latest">latest (${esc(dates.latest ?? "current")})</option>`]
    .concat((dates.dates ?? []).map((d) => `<option value="${esc(d)}">${esc(d)}</option>`));
  picker.innerHTML = opts.join("");

  async function show(val) {
    try {
      const url = val === "latest" ? "data/latest.json" : `data/archive/${encodeURIComponent(val)}.json`;
      const data = await loadJSON(url);
      renderSnapshot(data);
      if (val === "latest") {
        fetchLiveOdds(data);
      }
    } catch (e) {
      document.querySelector("main").innerHTML =
        `<div class="err">Could not load snapshot: ${esc(e.message)}.<br>
         Serve this folder over HTTP (e.g. <code>npm run dev</code>) — fetch() does not work from file://.</div>`;
    }
  }
  picker.addEventListener("change", () => show(picker.value));
  await show("latest");
}

boot();
