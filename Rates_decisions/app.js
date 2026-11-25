/* The Rate Decision Journal — compact 30s brief / 2m drivers / <10m audit */
"use strict";

const TZ = "America/Toronto";
const $ = (s) => document.querySelector(s);
const FLAGS = { USD: "🇺🇸", CAD: "🇨🇦" };

const state = {
  data: null,
  isDraft: false,
  bankFilter: "both",
  expandAllAudit: false,
  showExtraCal: false,
};

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
  return `${p.year}-${p.month}-${p.day} ${p.hour}:${p.minute} ET`;
}

function fmtCalTime(e) {
  if (e.date_only) return `${esc(e.date_toronto)} <span class="cal-muted">TBA</span>`;
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: TZ, month: "short", day: "2-digit",
    hour: "2-digit", minute: "2-digit", hour12: false,
  }).formatToParts(new Date(e.datetime_utc));
  const p = Object.fromEntries(parts.map((x) => [x.type, x.value]));
  return `${p.month} ${p.day}, ${p.hour}:${p.minute}`;
}

function torontoDay(val) {
  const s = String(val ?? "").trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
  const d = new Date(s);
  if (isNaN(d)) return "";
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(d);
  const p = Object.fromEntries(parts.map((x) => [x.type, x.value]));
  return `${p.year}-${p.month}-${p.day}`;
}

function calendarDaysBetween(a, b) {
  const da = torontoDay(a), db = torontoDay(b);
  if (!da || !db) return 0;
  return Math.round((Date.parse(db + "T00:00:00Z") - Date.parse(da + "T00:00:00Z")) / 86400000);
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
  const age = calendarDaysBetween(publishedAt, asOf);
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

function fmtScore(x) {
  const r = Math.round(x * 100) / 100;
  return `${r > 0 ? "+" : ""}${r}`;
}

function cleanVal(v) {
  if (v === null || v === undefined) return "";
  const s = String(v).trim();
  if (!s || s === "unverified" || s === "n/a") return "";
  return s;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function srcLink(label, url) {
  return url ? `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(label)}</a>` : esc(label);
}

function shortSource(label) {
  const s = String(label ?? "").trim();
  if (s.length <= 56) return s;
  const cut = s.split(/[;,()]/)[0].trim();
  return cut.length >= 10 && cut.length <= 56 ? cut : s.slice(0, 52).trim() + "…";
}

function importanceDots(n) {
  const on = Math.max(0, Math.min(3, n ?? 0));
  return `<span class="imp" title="Importance ${on}/3">${"●".repeat(on)}<span class="off">${"●".repeat(3 - on)}</span></span>`;
}

/* ---------- validation (audit lint) ---------- */

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
        if (d.weight >= 7 && (!d.market_validation || d.market_validation === "unverified"))
          warns.push(`${bank.toUpperCase()} driver ${d.id}: weight ${d.weight} missing market validation`);
        wSum += Math.abs(d.weight);
        signed += d.direction * d.weight;
      }
      if (all.length && wSum / all.length > 5) {
        warns.push(`${bank.toUpperCase()} mean |weight| ${(wSum / all.length).toFixed(1)} > 5 → inflation flag`);
      }
      const declared = data.total_score?.[bank]?.base_total;
      const clamped = Math.max(-10, Math.min(10, signed));
      if (declared !== undefined && declared !== clamped)
        warns.push(`${bank.toUpperCase()} base_total ${declared} ≠ recomputed ${clamped}`);
    }
  }
  return warns;
}

/* ---------- computations ---------- */

function computeScore(data, bank) {
  const dr = data.drivers[bank];
  const all = [...dr.hawkish, ...dr.dovish];
  const baseRaw = all.reduce((a, d) => a + d.direction * d.weight, 0);
  const base = Math.max(-10, Math.min(10, baseRaw));
  const effRaw = Math.round(all.reduce((a, d) => a + d.direction * d.weight * decayFactor(d.published_at, data.as_of), 0) * 100) / 100;
  const eff = Math.max(-10, Math.min(10, effRaw));
  const band = bandFor(Math.round(eff * 2) / 2);

  let divergence = "";
  const probs = data.meetings[bank].pricing?.probabilities;
  if (probs) {
    const leader = Object.entries(probs).sort((a, b) => b[1] - a[1])[0][0];
    const aligned =
      (leader === "hike" && eff > 3) ||
      (leader === "cut" && eff < -3) ||
      (leader === "hold" && Math.abs(eff) <= 3);
    if (!aligned) divergence = leader;
  }

  return {
    base,
    baseRaw,
    eff,
    effRaw,
    band,
    divergence,
    markerPct: ((eff + 10) / 20) * 100,
    hawkCount: dr.hawkish.length,
    doveCount: dr.dovish.length,
  };
}

function resolveBetUrl(b) {
  if (!b) return "";
  if (b.event_url && b.event_url !== "https://polymarket.com") return b.event_url;
  if (b.platform === "Polymarket") {
    return b.event_slug ? `https://polymarket.com/event/${b.event_slug}` : "https://polymarket.com";
  }
  return b.event_url || "";
}

function staleBadge(asOf, snapDate) {
  if (!asOf) return "";
  const age = calendarDaysBetween(asOf, snapDate);
  if (age > 4) return `<span class="badge warn">stale ${Math.round(age)}d</span>`;
  return "";
}

/* ---------- renderers ---------- */

function renderHeader(data, warns) {
  const fed = data.meetings.fed, boc = data.meetings.boc;
  const draftBadge = state.isDraft ? `<span class="badge warn">draft · unpublished</span>` : "";
  $("#masthead-date").innerHTML = `${esc(data.snapshot_date || fmtToronto(data.as_of).slice(0, 10))}${draftBadge}`;
  $("#hdr-meta").innerHTML =
    `As of <strong>${fmtToronto(data.as_of)}</strong><br>` +
    `Next: <strong>Fed ${esc(fed.next_meeting.date_label)}</strong> (${countdown(fed.next_meeting.datetime_utc)}) · ` +
    `<strong>BOC ${esc(boc.next_meeting.date_label)}</strong> (${countdown(boc.next_meeting.datetime_utc)})`;

  $("#warnings-slot").innerHTML = warns.length
    ? `<details class="lint-pill"><summary>⚠ ${warns.length} check${warns.length > 1 ? "s" : ""}</summary>` +
      `<div class="lint-popover">${warns.map((w) => `<div>${esc(w)}</div>`).join("")}</div></details>`
    : "";
}

function probBars(mProbs, polyProbs) {
  const rows = [["hike", "Hike 25bp"], ["hold", "Hold"], ["cut", "Cut 25bp"]];
  const hasPoly = Boolean(polyProbs);
  const head = `<div class="bars-head">
    <span class="bars-title">Market pricing</span>
    ${hasPoly ? `<div class="bars-legend">
      <span class="legend-item"><span class="legend-swatch mkt"></span>Market</span>
      <span class="legend-item"><span class="legend-swatch poly"></span>Polymarket</span>
    </div>` : ""}
  </div>`;

  return `<div class="bars">${head}${rows.map(([k, label]) => {
    const mVal = mProbs?.[k] ?? 0;
    const mPct = (mVal * 100).toFixed(1);
    const pVal = polyProbs?.[k];
    const hasP = pVal !== undefined && pVal !== null;
    const pPct = hasP ? (pVal * 100).toFixed(1) : null;

    return `<div class="bar-row">
      <div class="bar-label">${label}</div>
      <div class="bar-track">
        <div class="bar-fill ${k}" style="width:${mPct}%"></div>
        ${hasP ? `<div class="bar-poly-overlay" style="width:${pPct}%"><div class="poly-needle" title="Polymarket: ${pct(pVal)}"></div></div>` : ""}
      </div>
      <div class="bar-pcts">
        <span class="pct-mkt" title="Market implied">${pct(mVal)}</span>
        ${hasP ? `<span class="pct-poly" title="Polymarket">${pct(pVal)}</span>` : ""}
      </div>
    </div>`;
  }).join("")}</div>`;
}

function renderExpectations(data) {
  $("#expectations").innerHTML = ["fed", "boc"].map((bank) => {
    const m = data.meetings[bank];
    const p = m.pricing;
    const poly = data.betting?.[bank]?.find((b) => b.platform === "Polymarket");
    const polyProbs = poly?.probabilities ?? null;
    const sc = computeScore(data, bank);
    const numCls = sc.eff > 0 ? "pos" : sc.eff < 0 ? "neg" : "zero";

    let pricingBody;
    if (p.probability_status === "unavailable" || !p.probabilities) {
      const proxy = p.observable_proxy;
      pricingBody = `<div class="implied-line">Probability distribution <span class="badge na">unavailable</span></div>
        <div class="S">${proxy
          ? `Observable proxy: ${esc(proxy.instrument)} @ ${esc(proxy.price)} (${esc(proxy.tenor)})`
          : "No single-meeting distribution available."}</div>`;
    } else {
      pricingBody = probBars(p.probabilities, polyProbs) +
        `<div class="implied-line">Implied rate: ${p.implied_rate_before}% → <strong>${p.implied_rate_after}%</strong></div>`;
    }

    const polyStatus = poly?.status === "live"
      ? `<span class="badge ok">live</span>`
      : poly?.status === "stale" ? `<span class="badge warn">stale</span>` : "";
    const polyVol = cleanVal(poly?.volume);
    const polySnippet = poly
      ? `<span>${srcLink("Polymarket", resolveBetUrl(poly))}${polyStatus}${polyVol ? ` (${esc(polyVol)})` : ""}</span>`
      : "";
    const shortSrc = shortSource(p.source);
    const pDate = torontoDay(p.as_of) || esc(p.as_of ?? "n/a");
    const longMethod = (String(p.source || "").length > 56 ? p.source : "") +
      (poly?.note && String(poly.note).length > 90 ? (String(p.source || "").length > 56 ? "\n" : "") + "Polymarket: " + poly.note : "");

    return `<article class="brief-card">
      <div>
        <div class="brief-top">
          <h3 class="brief-bank">${esc(m.label)}${staleBadge(p.as_of, data.snapshot_date)}</h3>
          <span class="brief-meeting">Next: ${esc(m.next_meeting.date_label)} · ${countdown(m.next_meeting.datetime_utc)}</span>
        </div>
        <div class="brief-last">Last (${esc(m.last_meeting.date)}): ${esc(m.last_meeting.decision)}</div>
      </div>

      ${pricingBody}

      <div class="brief-score">
        <div class="score-head">
          <div class="score-left">
            <span class="score-kicker">Driver Score</span>
            <span class="score-num ${numCls}">${fmtScore(sc.eff)}</span>
            <span class="score-band">${esc(sc.band)}</span>
            ${sc.divergence ? `<span class="badge warn">⚠ diverges vs ${esc(sc.divergence)}</span>` : ""}
          </div>
          <span class="score-sub">base ${fmtScore(sc.base)} · ${sc.doveCount}D / ${sc.hawkCount}H</span>
        </div>
        <div class="gauge">
          <div class="gauge-center"></div>
          <div class="gauge-marker" style="left:${sc.markerPct}%"></div>
        </div>
        <div class="gauge-ticks S"><span>−10 cut</span><span>0</span><span>+10 hike</span></div>
      </div>

      <div class="brief-foot">
        <span>Pricing: ${srcLink(shortSrc, p.source_url)} (${esc(pDate)})</span>
        ${polySnippet ? `<span>·</span>${polySnippet}` : ""}
        ${longMethod ? `<button type="button" class="audit-btn method-btn" aria-expanded="false">Method ▸</button>` : ""}
      </div>
      ${longMethod ? `<div class="driver-audit brief-method" hidden>${esc(longMethod).replace(/\n/g, "<br>")}</div>` : ""}
    </article>`;
  }).join("");
}

function driverCard(d, side, asOf) {
  const f = decayFactor(d.published_at, asOf);
  const eff = d.direction * d.weight * f;
  const signCls = d.direction > 0 ? "pos" : "neg";
  const baseLbl = `${d.direction > 0 ? "+" : "−"}${d.weight}`;
  const effTag = f < 1 ? `<span class="w-eff" title="Age-decayed ×${f}">eff ${fmtScore(eff)}</span>` : "";

  const actual = cleanVal(d.data?.actual);
  const forecast = cleanVal(d.data?.forecast);
  const prev = cleanVal(d.data?.previous);
  const delta = cleanVal(d.data?.delta_label);
  const dataParts = [];
  if (actual) dataParts.push(forecast ? `${actual} vs ${forecast} exp` : actual);
  if (prev) dataParts.push(`prev ${prev}`);
  if (delta) dataParts.push(delta);

  const mv = cleanVal(d.market_validation);
  const wb = d.weight_breakdown || {};
  const isOpen = state.expandAllAudit;
  const isMinor = Math.abs(eff) <= 1.5;

  return `<div class="driver ${side}${isMinor ? " is-minor" : ""}">
    <div class="driver-head">
      <span class="driver-title">${esc(d.title)}</span>
      <span class="w-wrap">${effTag}<span class="w-badge ${signCls}">${baseLbl}</span></span>
    </div>
    <div class="driver-summary">${esc(d.summary)}</div>
    <div class="driver-foot">
      <span>${srcLink(d.source, d.source_url)} · ${esc(d.published_at)}</span>
      <button type="button" class="audit-btn" aria-expanded="${isOpen}">${isOpen ? "Hide ▾" : "Audit ▸"}</button>
    </div>
    <div class="driver-audit"${isOpen ? "" : " hidden"}>
      ${dataParts.length ? `<div class="audit-row"><span class="audit-label">Data:</span>${esc(dataParts.join(" · "))}</div>` : ""}
      ${d.reason ? `<div class="audit-row"><span class="audit-label">Why:</span>${esc(d.reason)}</div>` : ""}
      ${mv ? `<div class="audit-row"><span class="audit-label">Market:</span>${esc(mv)}</div>` : ""}
      <div class="audit-row"><span class="audit-label">Weight:</span>base ${baseLbl}${f < 1 ? ` × ${f} age = ${fmtScore(eff)}` : ""} (dev ${esc(wb.deviation)} / imp ${esc(wb.importance)} / surp ${esc(wb.surprise)})</div>
    </div>
  </div>`;
}

function renderDrivers(data) {
  const banks = state.bankFilter === "both" ? ["fed", "boc"] : [state.bankFilter];
  const sortEff = (arr) => [...arr].sort((a, b) => {
    const ea = Math.abs(a.weight * decayFactor(a.published_at, data.as_of));
    const eb = Math.abs(b.weight * decayFactor(b.published_at, data.as_of));
    if (eb !== ea) return eb - ea;
    if (b.weight !== a.weight) return b.weight - a.weight;
    return String(b.published_at).localeCompare(String(a.published_at));
  });

  $("#drivers").innerHTML = banks.map((bank) => {
    const dr = data.drivers[bank];
    const sc = computeScore(data, bank);
    const doveList = sortEff(dr.dovish);
    const hawkList = sortEff(dr.hawkish);

    return `<div class="bank-block">
      <div class="bank-bar">
        <h3 class="bank-name">${esc(data.meetings[bank].label)} — since ${esc(data.meetings[bank].last_meeting.date)}</h3>
        <span class="bank-score-pill">Net ${fmtScore(sc.eff)} (${esc(sc.band)}) · base ${fmtScore(sc.base)}</span>
      </div>
      <div class="driver-cols">
        <div class="driver-col dovish">
          <h4>◀ Dovish (${doveList.length})</h4>
          ${doveList.length ? doveList.map((d) => driverCard(d, "dovish", data.as_of)).join("") : `<div class="S">No dovish drivers recorded.</div>`}
        </div>
        <div class="driver-col hawkish">
          <h4>Hawkish (${hawkList.length}) ▶</h4>
          ${hawkList.length ? hawkList.map((d) => driverCard(d, "hawkish", data.as_of)).join("") : `<div class="S">No hawkish drivers recorded.</div>`}
        </div>
      </div>
    </div>`;
  }).join("");
}

function renderCalendar(data) {
  const asOf = new Date(data.as_of);
  const upcoming = (data.calendar || [])
    .filter((e) => e.date_only ? new Date(e.date_toronto + "T23:59:59") >= asOf : new Date(e.datetime_utc) >= asOf)
    .sort((a, b) => new Date(a.datetime_utc || a.date_toronto) - new Date(b.datetime_utc || b.date_toronto));

  const meetingDates = [data.meetings.fed?.next_meeting?.datetime_utc, data.meetings.boc?.next_meeting?.datetime_utc]
    .filter(Boolean)
    .map((u) => new Date(u).getTime());
  const cutoffMs = meetingDates.length ? Math.max(...meetingDates) : Infinity;

  const isPrimary = (e) => {
    const ts = e.date_only ? new Date(e.date_toronto + "T23:59:59").getTime() : new Date(e.datetime_utc).getTime();
    return e.impact === "HIGH" && ts <= cutoffMs;
  };

  let primary = upcoming.filter(isPrimary);
  let secondary = upcoming.filter((e) => !isPrimary(e));
  if (!primary.length) {
    primary = upcoming;
    secondary = [];
  }

  $("#calendar-controls").innerHTML = secondary.length
    ? `<button type="button" id="toggle-extra-cal" class="ctrl-btn" aria-pressed="${state.showExtraCal}">${state.showExtraCal ? "Hide extra catalysts" : `+${secondary.length} medium / post-meeting`}</button>`
    : "";

  const rows = state.showExtraCal ? [...primary, ...secondary] : primary;
  if (!rows.length) {
    $("#calendar").innerHTML = `<div class="S">No upcoming releases after ${esc(data.snapshot_date)}.</div>`;
    return;
  }

  const hasForecast = rows.some((e) => cleanVal(e.forecast));
  $("#calendar").innerHTML = `<table class="cal">
    <thead><tr>
      <th>Date (ET)</th><th></th><th>Event</th><th>Imp.</th>${hasForecast ? "<th>Forecast</th>" : ""}<th>Previous</th>
    </tr></thead>
    <tbody>${rows.map((e) => {
      const secCls = isPrimary(e) ? "" : " is-secondary";
      const meetCls = /\b(rate decision|fomc|boc rate)\b/i.test(e.event || "") ? " is-meeting" : "";
      const fc = cleanVal(e.forecast) || "—";
      const prev = cleanVal(e.previous) || "—";
      return `<tr class="${meetCls}${secCls}">
        <td style="white-space:nowrap">${fmtCalTime(e)}</td>
        <td class="flag">${FLAGS[e.currency] ?? esc(e.currency)}</td>
        <td>${srcLink(e.event, e.source_url)}</td>
        <td>${importanceDots(e.importance)}</td>
        ${hasForecast ? `<td${fc === "—" ? ' class="cal-muted"' : ""}>${esc(fc)}</td>` : ""}
        <td${prev === "—" ? ' class="cal-muted"' : ""}>${esc(prev)}</td>
      </tr>`;
    }).join("")}</tbody>
  </table>`;
}

function renderSnapshot(data) {
  state.data = data;
  const warns = validate(data);
  renderHeader(data, warns);
  renderExpectations(data);
  renderDrivers(data);
  renderCalendar(data);
}

/* ---------- live odds & events ---------- */

async function fetchLiveOdds(data) {
  let changed = false;
  for (const bank of ["fed", "boc"]) {
    const meetingUtc = data.meetings?.[bank]?.next_meeting?.datetime_utc;
    if (meetingUtc && new Date(meetingUtc).getTime() <= Date.now()) continue;
    const poly = data.betting?.[bank]?.find((b) => b.platform === "Polymarket" && b.event_slug);
    if (!poly) continue;
    try {
      const res = await fetch(`https://gamma-api.polymarket.com/events?slug=${encodeURIComponent(poly.event_slug)}`, { cache: "no-store" });
      if (!res.ok) continue;
      const evs = await res.json();
      const ev = Array.isArray(evs) ? evs[0] : evs;
      if (!ev || !Array.isArray(ev.markets)) continue;
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
        poly.volume = v >= 1e6 ? "$" + (v / 1e6).toFixed(1) + "M" : v >= 1e3 ? "$" + (v / 1e3).toFixed(1) + "k" : "$" + Math.round(v);
      }
      poly.as_of = fmtToronto(new Date().toISOString());
      changed = true;
    } catch {
      // keep snapshot odds on network failure
    }
  }
  if (changed && state.data === data) {
    renderExpectations(data);
  }
}

function wireInteractions() {
  document.addEventListener("click", (ev) => {
    const seg = ev.target.closest(".seg-btn");
    if (seg && state.data) {
      state.bankFilter = seg.dataset.bank || "both";
      document.querySelectorAll(".seg-btn").forEach((b) => {
        const on = b === seg;
        b.classList.toggle("active", on);
        b.setAttribute("aria-selected", String(on));
      });
      renderDrivers(state.data);
      return;
    }

    if (ev.target.closest("#toggle-all-audit") && state.data) {
      state.expandAllAudit = !state.expandAllAudit;
      const btn = $("#toggle-all-audit");
      btn.setAttribute("aria-pressed", String(state.expandAllAudit));
      btn.textContent = state.expandAllAudit ? "Collapse all audit" : "Expand all audit";
      renderDrivers(state.data);
      return;
    }

    const auditBtn = ev.target.closest(".audit-btn");
    if (auditBtn) {
      const card = auditBtn.closest(".driver, .brief-card");
      const drawer = card?.querySelector(".driver-audit");
      if (!drawer) return;
      const open = drawer.hasAttribute("hidden");
      if (open) drawer.removeAttribute("hidden");
      else drawer.setAttribute("hidden", "");
      auditBtn.setAttribute("aria-expanded", String(open));
      const baseTxt = auditBtn.classList.contains("method-btn") ? "Method ▸" : "Audit ▸";
      auditBtn.textContent = open ? "Hide ▾" : baseTxt;
      return;
    }

    if (ev.target.closest("#toggle-extra-cal") && state.data) {
      state.showExtraCal = !state.showExtraCal;
      renderCalendar(state.data);
    }
  });
}

async function boot() {
  wireInteractions();
  const picker = $("#date-picker");
  const isLocal = location.hostname === "127.0.0.1" || location.hostname === "localhost";
  const wantParam = new URLSearchParams(location.search).get("snapshot");
  let dates = { latest: null, dates: [] };
  try { dates = await loadJSON("data/dates.json"); } catch {}

  let draftSnap = null, latestSnap = null;
  if (isLocal || wantParam === "current") {
    try { draftSnap = await loadJSON("data/current.json"); } catch {}
    try { latestSnap = await loadJSON("data/latest.json"); } catch {}
  }

  const draftTs = Date.parse(draftSnap?.as_of || "");
  const latestTs = Date.parse(latestSnap?.as_of || "");
  const hasNewerDraft = Boolean(
    draftSnap && (
      !dates.latest ||
      String(draftSnap.snapshot_date || "") > String(dates.latest) ||
      (Number.isFinite(draftTs) && Number.isFinite(latestTs) && draftTs > latestTs)
    )
  );
  const opts = [];
  if (draftSnap && (hasNewerDraft || wantParam === "current")) {
    opts.push(`<option value="current">draft (${esc(draftSnap.snapshot_date || "current")})</option>`);
  }
  opts.push(`<option value="latest">latest (${esc(dates.latest ?? "current")})</option>`);
  for (const d of (dates.dates ?? [])) {
    opts.push(`<option value="${esc(d)}">${esc(d)}</option>`);
  }
  picker.innerHTML = opts.join("");

  async function show(val) {
    try {
      state.isDraft = val === "current";
      const url = val === "current"
        ? "data/current.json"
        : val === "latest" ? "data/latest.json" : `data/archive/${encodeURIComponent(val)}.json`;
      const data = val === "current" && draftSnap
        ? draftSnap
        : val === "latest" && latestSnap ? latestSnap : await loadJSON(url);
      renderSnapshot(data);
      if (val === "latest" || val === "current") fetchLiveOdds(data);
    } catch (e) {
      document.querySelector("main").innerHTML =
        `<div class="err">Could not load snapshot: ${esc(e.message)}.<br>
         Serve this folder over HTTP (e.g. <code>npm run dev</code>) — fetch() does not work from file://.</div>`;
    }
  }
  picker.addEventListener("change", () => show(picker.value));
  const initial = wantParam === "current" && draftSnap
    ? "current"
    : hasNewerDraft ? "current" : "latest";
  picker.value = initial;
  await show(initial);
}

boot();
