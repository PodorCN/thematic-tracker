// Thematic Tracker — read-only API over data/*.yaml
// 路由（API Contract v1）：
//   GET /api/themes/active?date=YYYY-MM-DD
//   GET /api/themes/:id
//   GET /api/themes/history?theme_id=
//   GET /api/market/snapshot?week=YYYY-Www
//   GET /api/commentary?week=YYYY-Www
// 原则：只读 data/，绝不写。Agent 更新只碰 data/，前端自动反映。

const http = require('http');
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

const DATA_DIR = path.join(__dirname, '..', 'data');
const PORT = process.env.PORT || 8787; // 固定端口；CLI --port 只影响前端

function loadYaml(file) {
  return yaml.load(fs.readFileSync(file, 'utf8'));
}

function listWeeks(subdir) {
  const dir = path.join(DATA_DIR, subdir);
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((d) => /^\d{4}-W\d{2}$/.test(d)).sort();
}

function latestWeek(subdir) {
  const weeks = listWeeks(subdir);
  return weeks.length ? weeks[weeks.length - 1] : null;
}

function loadThemeFile(file) {
  const t = loadYaml(file);
  return t;
}

function loadAllThemes() {
  const out = [];
  for (const week of listWeeks('themes')) {
    const dir = path.join(DATA_DIR, 'themes', week);
    for (const f of fs.readdirSync(dir).filter((f) => f.endsWith('.yaml'))) {
      try {
        out.push(loadThemeFile(path.join(dir, f)));
      } catch (e) {
        console.error(`[api] failed to parse ${f}: ${e.message}`);
      }
    }
  }
  return out;
}

function send(res, code, obj) {
  const body = JSON.stringify(obj, null, 2);
  res.writeHead(code, {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': '*',
    'Cache-Control': 'no-store',
  });
  res.end(body);
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const p = url.pathname;

  try {
    // GET /api/themes/active?date=YYYY-MM-DD
    if (p === '/api/themes/active') {
      const week = latestWeek('themes');
      if (!week) return send(res, 200, { week: null, themes: [] });
      const dir = path.join(DATA_DIR, 'themes', week);
      const themes = fs
        .readdirSync(dir)
        .filter((f) => f.endsWith('.yaml'))
        .map((f) => loadThemeFile(path.join(dir, f)))
        .filter((t) => t.status !== 'Dead');
      return send(res, 200, { week, count: themes.length, themes });
    }

    // GET /api/themes/history?theme_id=
    if (p === '/api/themes/history') {
      const id = url.searchParams.get('theme_id');
      if (!id) return send(res, 400, { error: 'theme_id required' });
      const snaps = loadAllThemes()
        .filter((t) => t.id === id)
        .sort((a, b) => (a.week < b.week ? -1 : 1));
      return send(res, 200, { theme_id: id, count: snaps.length, history: snaps });
    }

    // GET /api/themes/:id
    const m = p.match(/^\/api\/themes\/([a-z0-9-]+)$/);
    if (m) {
      const id = m[1];
      const all = loadAllThemes().filter((t) => t.id === id);
      if (!all.length) return send(res, 404, { error: `theme '${id}' not found` });
      all.sort((a, b) => (a.week < b.week ? -1 : 1));
      return send(res, 200, all[all.length - 1]);
    }

    // GET /api/market/snapshot?week=
    if (p === '/api/market/snapshot') {
      const weeks = listWeeks('themes');
      const week = url.searchParams.get('week') || (weeks.length ? weeks[weeks.length - 1] : null);
      if (!week) return send(res, 404, { error: 'no snapshot' });
      const file = path.join(DATA_DIR, 'market', `snapshot_${week}.yaml`);
      if (!fs.existsSync(file)) return send(res, 404, { error: `snapshot for ${week} not found` });
      return send(res, 200, loadYaml(file));
    }

    // GET /api/commentary?week=
    if (p === '/api/commentary') {
      const weeks = listWeeks('themes');
      const week = url.searchParams.get('week') || (weeks.length ? weeks[weeks.length - 1] : null);
      if (!week) return send(res, 404, { error: 'no commentary' });
      const file = path.join(DATA_DIR, 'commentary', `${week}.yaml`);
      if (!fs.existsSync(file)) return send(res, 404, { error: `commentary for ${week} not found` });
      return send(res, 200, loadYaml(file));
    }

    if (p === '/api/health') return send(res, 200, { ok: true, data_dir: DATA_DIR });

    send(res, 404, { error: 'not found', path: p });
  } catch (e) {
    send(res, 500, { error: e.message });
  }
});

server.listen(PORT, () => {
  console.log(`[thematic-tracker api] listening on http://localhost:${PORT}`);
  console.log(`[thematic-tracker api] data dir: ${DATA_DIR}`);
});
