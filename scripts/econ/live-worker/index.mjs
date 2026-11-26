const scheduleUrl = 'https://raw.githubusercontent.com/PodorCN/thematic-tracker/main/economic-calendar/data/latest.json';
const detailUrl = 'https://calendar-api.fxstreet.com/en/api/v1/eventDates/';
const minute = 60_000;
const day = 24 * 60 * minute;
const scheduleInterval = 15 * minute;
const releaseWindow = 30 * minute;
const dataRetention = 3 * day;
const uuidPattern = /^[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}$/i;
const responseHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Cache-Control': 'no-store',
};

function releaseTime(value) {
  if (typeof value !== 'string') return NaN;
  return Date.parse(/[zZ]$|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`);
}

async function fetchJSON(url, headers) {
  const response = await fetch(url, {headers, signal: AbortSignal.timeout(8_000), cache: 'no-store'});
  if (!response.ok) throw new Error(`${new URL(url).hostname} HTTP ${response.status}`);
  return response.json();
}

async function getSchedule(db, now, cached) {
  if (cached && now - cached.checked_at < scheduleInterval) return JSON.parse(cached.events);
  try {
    const snapshot = await fetchJSON(scheduleUrl);
    if (!Array.isArray(snapshot.events) || snapshot.count !== snapshot.events.length) {
      throw new Error('Invalid daily calendar snapshot');
    }
    const events = snapshot.events
      .filter(event => event.source === 'fxstreet' && (event.country === 'US' || event.country === 'CA') &&
        event.impact === 'HIGH' && uuidPattern.test(event.id))
      .map(event => ({id: event.id, releaseAt: releaseTime(event.datetime_utc)}))
      .filter(event => Number.isFinite(event.releaseAt));
    // The fallback feed has different IDs. Keep FxStreet IDs during a temporary fallback.
    if (snapshot.source !== 'fxstreet' && cached) return JSON.parse(cached.events);
    await db.batch([
      db.prepare(`INSERT INTO calendar_schedule (id, checked_at, events) VALUES (1, ?, ?)
        ON CONFLICT (id) DO UPDATE SET checked_at = excluded.checked_at, events = excluded.events
        WHERE excluded.checked_at > calendar_schedule.checked_at`).bind(now, JSON.stringify(events)),
      db.prepare('DELETE FROM calendar_releases WHERE release_at < ?').bind(now - dataRetention),
    ]);
    return events;
  } catch (error) {
    if (!cached) throw error;
    console.warn('Calendar schedule refresh failed:', error.message);
    return JSON.parse(cached.events);
  }
}

async function fetchRelease(event) {
  const detail = await fetchJSON(`${detailUrl}${event.id}`, {
    Accept: 'application/json',
    Referer: 'https://www.fxstreet.com/',
  });
  if (detail.id !== event.id || releaseTime(detail.dateUtc) !== event.releaseAt) return null;
  if (!Number.isFinite(detail.actual)) return null;
  return {
    actual: detail.actual,
    forecast: Number.isFinite(detail.consensus) ? detail.consensus : null,
    previous: Number.isFinite(detail.previous) ? detail.previous : null,
    unit: typeof detail.unit === 'string' ? detail.unit : null,
  };
}

export async function refreshReleases(db, now) {
  const cached = await db.prepare('SELECT checked_at, events FROM calendar_schedule WHERE id = 1').first();
  const schedule = await getSchedule(db, now, cached);
  // On initial setup, include recent releases so the first run can populate the feed.
  const window = cached ? releaseWindow : day;
  const due = schedule.filter(event => event.releaseAt <= now && event.releaseAt >= now - window)
    .sort((a, b) => b.releaseAt - a.releaseAt).slice(0, 30);
  const writes = [];
  for (let offset = 0; offset < due.length; offset += 5) {
    const batch = due.slice(offset, offset + 5);
    const results = await Promise.allSettled(batch.map(fetchRelease));
    for (const [index, result] of results.entries()) {
      const event = batch[index];
      if (result.status === 'rejected') {
        console.warn('Calendar release lookup failed:', event.id, result.reason.message);
      } else if (result.value) {
        writes.push(db.prepare(`INSERT INTO calendar_releases (id, release_at, checked_at, details) VALUES (?, ?, ?, ?)
          ON CONFLICT (id) DO UPDATE SET release_at = excluded.release_at, checked_at = excluded.checked_at,
            details = excluded.details WHERE excluded.checked_at > calendar_releases.checked_at`)
          .bind(event.id, event.releaseAt, now, JSON.stringify(result.value)));
      }
    }
  }
  if (writes.length) await db.batch(writes);
}

export default {
  async scheduled(controller, env) {
    await refreshReleases(env.DB, controller.scheduledTime);
  },

  async fetch(request, env) {
    if (request.method !== 'GET' || new URL(request.url).pathname !== '/live.json') {
      return new Response('Not found', {status: 404, headers: responseHeaders});
    }
    const now = Date.now();
    const schedule = await env.DB.prepare('SELECT checked_at FROM calendar_schedule WHERE id = 1').first();
    if (!schedule || now - schedule.checked_at > 3 * scheduleInterval) {
      return Response.json({error: 'Schedule unavailable'}, {status: 503, headers: responseHeaders});
    }
    const {results} = await env.DB.prepare('SELECT * FROM calendar_releases WHERE release_at >= ?')
      .bind(now - dataRetention).all();
    const events = results.map(row => ({
      id: row.id,
      datetime_utc: new Date(row.release_at).toISOString(),
      checked_at: new Date(row.checked_at).toISOString(),
      ...JSON.parse(row.details),
    }));
    return Response.json({events}, {headers: responseHeaders});
  },
};
