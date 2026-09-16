# AGENT.md — Global Economic Calendar（全球经济日历）

> ⚠️ 本文件夹**不走**根目录 `agent.md` 的每日 theme SOP（没有 `theme.md`、没有 proxy、没有 VALIDITY 灯）。
> 这是一个由 Python 抓取 + 渲染的宏观数据页，每天由 GitHub Actions 自动发布。
> 运维手册见 [`../docs/MACRO_DATA_OPERATIONS.md`](../docs/MACRO_DATA_OPERATIONS.md)，
> 发布契约见 [`../docs/PUBLIC_PAGES_BACKEND_SPEC.md`](../docs/PUBLIC_PAGES_BACKEND_SPEC.md)，
> 数据 schema 见 [`../docs/ECON_CALENDAR_API_SPEC.md`](../docs/ECON_CALENDAR_API_SPEC.md)。

## 文件夹结构

```
economic-calendar/
  index.html              最新一天的完整页面（由渲染器覆盖，不要手改）
  archive/<date>.html     每日不可变页面快照，日期选择器直接切过去
  data/
    latest.json           最新快照，页面默认读取
    dates.json            日期清单 {"latest": ..., "dates": [...]}
    archive/<date>.json   每日不可变数据快照
  raw/<date>/             抓取阶段原始产物（fetch 的 JSON + 当日渲染的 HTML）
```

页面是纯静态的，**前端不直连 FxStreet / Investing.com**，只 `fetch()` 本文件夹下的 JSON。

## 每日流程（已自动化）

`.github/workflows/macro-pages-daily.yml` 每天 13:10 UTC（多伦多 09:10 EDT / 08:10 EST）跑：

```bash
python scripts/econ/fetch_calendar.py --date <date> --days 7 \
  --countries US,CA,EMU,DE,FR,IT,ES,UK,CH --impacts HIGH,MEDIUM \
  --with-history --history-events 15 --history-limit 12
python scripts/econ/render_calendar.py --date <date>
```

`render_calendar.py` 一步完成校验 + 发布：写 `data/archive/<date>.json`、`archive/<date>.html`，
重算 `data/dates.json`，再把最新一天复制成 `data/latest.json` 和 `index.html`。

手工补跑某一天，直接跑上面两条命令即可（幂等，全量覆盖）。

## 数据源

- 主源：FxStreet 日历 API（无需 key，无 Cloudflare）
- 备源：ForexFactory HTML（`cloudscraper` + `bs4`），主源失败时自动回退
- 抓取实现见 `scripts/econ/core.py`，源标记在 `cal.source_used`

## 红线

- **不要手改 `index.html` 和 `archive/*.html`**：它们由 `scripts/econ/template_calendar.html.j2` 渲染，
  手改会在下一次跑流水线时被覆盖。要改版式就改模板。
- **归档不可变**：`archive/` 和 `data/archive/` 里已发布的日期不回填、不重绘，回看才不会被最新数据污染。
- **时区**：所有对外显示时间一律 `America/Toronto`；源时间戳必须保留显式 UTC offset。
- 接口失败当日跳过，下一交易日全量重拉。
