# AGENT.md — Global Economic Calendar（全球经济日历）

> 本文件夹**不走**根目录 `AGENT.md` 的每日 theme SOP（没有 `theme.md`、proxy 或 VALIDITY 灯）。
> 它是自动发布 JSON、由浏览器渲染的静态宏观页；与根 `AGENT.md` 的数据-only 契约一致。发布路径与校验见 `docs/MACRO_DATA_OPERATIONS.md`。

## 文件与发布契约

```text
economic-calendar/
  index.html              稳定前端：手工改版才修改；每日流水线绝不覆盖
  data/
    latest.json           最新已发布 JSON（原子复制最新 archive）
    dates.json            {"latest": "YYYY-MM-DD", "dates": [日期降序]}
    archive/<date>.json   日期对应的完整、可回看 JSON 快照
  raw/<date>/economic_calendar.json   当日抓取产物/发布输入
  archive/<date>.html     旧版历史页面，只读遗留文件；不再新增或更新
```

`index.html` 加载 `data/dates.json`，默认读取 `data/latest.json`；日期选择器切换到 `data/archive/<date>.json`，地址变为 `?date=<date>`，浏览器返回/前进也恢复选择。日期、指标、图表、时间线和过滤选项以所选 JSON 为基础。默认视图额外读取盘中公布值，带 `?date=` 的历史视图只显示所选快照。快照解析或 HTTP 出错时清空旧内容并显示错误。前端不直连 FxStreet/Investing.com。历史旧 HTML 保留，但新的日期只提供 JSON；不能再链接到不存在的新版 `archive/<date>.html`。

## 美加盘中更新

`scripts/econ/live-worker/` 的 Cloudflare Worker 每分钟执行一次，使用公开日更快照识别美国和加拿大的高影响 FxStreet 事件，并在计划公布后的 30 分钟内查询对应事件的公布值。D1 保存最近三天的结果，`/live.json` 将它们提供给日历。默认视图可见时每 30 秒查询，按事件 ID 和公布时间匹配，只使用比所选快照更新的结果。盘中接口失败时，页面显示状态并保留已显示的数值。

从仓库根目录执行以下命令可更新配置和部署。数据库绑定在 `scripts/econ/live-worker/wrangler.toml` 指定，建表操作可重复执行。部署后检查 `https://economic-calendar-live.zixiao-cab.workers.dev/live.json`，并在下一次重要发布时对照 FxStreet 的公布值与页面更新时间。

```bash
cd scripts/econ/live-worker
npx wrangler d1 execute economic-calendar-live --remote --file schema.sql
npx wrangler deploy
```

## 每日流程

`.github/workflows/macro-pages-daily.yml` 每天 13:10 UTC 抓取并发布：

```bash
python scripts/econ/fetch_calendar.py --date <date> --days 7 \
  --countries US,CA,EMU,DE,FR,IT,ES,UK,CH --impacts HIGH,MEDIUM \
  --with-history --history-events 15 --history-limit 12
python scripts/econ/render_calendar.py --date <date>
```

`render_calendar.py` 只检查抓取 JSON 的 `count` 与 `events` 数量，再写 `data/archive/<date>.json`，按档案日期重算 `data/latest.json`、`data/dates.json`。不会生成 raw HTML、archive HTML 或重写 `index.html`；已发布的旧 HTML 原样保留。手工重跑指定日期只更新该日期 JSON；除修复错误数据外，不要回填已发布日期。`--input` 可指定 JSON 输入，`--date` 指定发布归档日期；不再提供 `--output` / `--docs` HTML 输出选项。

## 数据与验证

- 主源 FxStreet 日历 API；失败时回退 ForexFactory HTML。抓取实现在 `scripts/econ/core.py`，`source` 标识来源。
- 对外时间用 `America/Toronto`（浏览器 `Intl.DateTimeFormat`）；旧 FxStreet `datetime_utc` 若无 offset，按 UTC 解释。时间线并排显示美国和其他地区，MoM/YoY 同时同名发布可合并显示，趋势图按主题分类；日期、币种、重要性和搜索过滤仍在客户端完成。
- 保留 `data/archive/` 日期 JSON，`data/latest.json` 始终与最新日期档案一致；抓取失败时保留上一个成功快照。不要在报错时展示 HTML 嵌入的旧数值。
- 本地校验：`uv run --isolated --python 3.11 --with-requirements requirements.txt python -m pytest tests/test_econ_render.py -q`，并用本地 HTTP 服务器打开 `economic-calendar/`，检查最新/历史选取、时间线、趋势图、过滤和错误状态。不要用 `file://` 测试 fetch。
- 每次只暂存本日 `raw/<date>/economic_calendar.json` 与三个 data JSON，运行 `python scripts/econ/verify_data_only_changes.py --product economic-calendar --staged`；如果路径、固定页面 SHA 或数据校验失败，不得提交/推送。禁止 `git add economic-calendar/`。
- 前端改版必须单独 PR，更新 `scripts/econ/frontend_contract.json`，跑桌面和手机真浏览器验收及独立代码审核；日更任务没有改网页的权限。
