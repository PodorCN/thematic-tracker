# AGENT.md — General Theme Tracker（PM 向主题站）专属指令

> 本产品走全仓共享 gate（`scripts/review/`：冻结字节、SHA 绑定、verdict 自洽），
> **blocking 强卡点**：无 APPROVED 的 `pm-review.json` 就拒发。
> 通用信条见 [`scripts/review/REVIEWER_AGENT.md`](../scripts/review/REVIEWER_AGENT.md)，
> 本文件只保留 Theme 特有的结构校验、打分规则与源规则。

## 1. 角色与定位

Theme 第一视角站：现在市场最重要的 Theme 是什么？表现如何？用什么 track？
为什么形成？依赖什么 catalyst？昨天 vs 今天有何变化？是 Theme 还是 Noise？
5 分钟读懂一个 Theme（正文 <900 中字 / <500 英词，解释折叠）。

## 2. 文件结构与契约

```text
general-theme-tracker/
  backend/server.js            只读 API（Node，无框架；日常绝不改）
  backend/validate.js          YAML schema 校验（npm run validate；CI 用）
  data/
    themes/<YYYY-Www>/theme_*.yaml   Agent 唯一可写区（每周 3-7 个 Theme）
    market/snapshot_<YYYY-Www>.yaml  Regime + Benchmark 条
    commentary/<YYYY-Www>.yaml       Weekly Commentary 来源库
    archive/<YYYY-MM-DD>.json        已发布冻结快照（publish 原子写入，勿手改）
    schema/theme.schema.yaml         schema_v1（开发变更，不走数据 PR）
  review/
    REVIEWER_AGENT.md       本产品审阅附录（六个 checks + Theme 打分/源规则）
    TEMPLATE.md             本产品命令速查
    <YYYY-MM-DD>/           当日冻结包（缺一不可，否则拒发）：
      candidate.json          整周打包 JSON（build_candidate.mjs 生成后冻结）
      candidate.sha256        候选字节 SHA-256
      structural-flags.json   机器旗标（reviewer 必须逐条 disposition）
      pm-review.json          独立审阅结论（SHA 绑定，six checks 全 pass 方可 APPROVED）
      review.md               人类可读版（可选，需与 json verdict 一致）
  scripts/
    build_candidate.mjs     整周 YAML -> candidate JSON（周包唯一入口）
    freeze.py               冻结包装器（调用共享 freeze + 本产品 flags 插件）
    publish.py              结构校验 + reviewer 门禁 + 归档（调用共享层）
    check_review.py         审阅预检包装器
```

## 3. 维护流程（SOP，blocking）

```bash
# 1. 编辑数据：只碰 data/themes/<week>/*.yaml + market/snapshot_<week>.yaml + commentary/<week>.yaml
#    snapshot_date 由 freeze 按多伦多当日自动注入（YAML 里不手写 snapshot_date）。

# 2. 机器数据校验（结构错误直接拦；结构旗标 warn，需 reviewer 逐条 disposition）
npm run validate                       # YAML schema_v1（backend/validate.js）
python3 scripts/publish.py --check     # 整周 bundle 结构 + 旗标预览

# 3. 冻结候选（冻结后 data/ 任何改动都会让审阅作废）
npm run freeze
# -> review/<today>/candidate.json + candidate.sha256 + structural-flags.json

# 4. 独立 PM 审阅（reviewer 必须与 operator 不同人/模型，禁 self）
#    reviewer 按 structural-flags.json 逐条写 review/<today>/pm-review.json：
#    candidate_sha256 绑定、六个 checks、findings（critical/major 拦）、flags_dispositioned 全覆盖
npm run review:check

# 5. 发布归档（publish 会重验：周包重建 bytes == 冻结 bytes + review 结论 + 旗标全覆盖 + 前端干净）
npm run publish
# 机制：
#   - canonical(重建周包) sha == candidate.json sha == pm-review.json candidate_sha256
#   - verdict 必须 APPROVED，且零 critical/major、六个 checks 全 pass
#   - 当前周包的每条结构旗标都必须在 flags_dispositioned 里出现
#   - 工作区里 frontend/src/backend/scripts 有改动则拒发（前端走独立 PR）
#   - 发布字节 == reviewed candidate 字节 -> data/archive/<today>.json
```

## 4. 核心规范与红线（Theme 特有，机器 + reviewer 双拦）

- **严禁修改前端**：`frontend/src`、`backend/`、`scripts/` 在日常更新中绝对禁止修改。
  publish 会检查 git 工作区，脏了就拒发。
- **六个 checks（传给 validator 的 `--checks`，全 pass 方可 APPROVED）**：
  `excess_math` `timing_source` `freshness` `readability` `theme_noise` `proxy_tradability`。
- **excess_math**：`excess = proxy - benchmark`，误差 >0.2pp 打回；禁止盘中价冒充收盘价；
  禁止混用 Total Return / Price Return 不注明。
- **timing_source**：每个 Event 必须 `event_time_UTC + source + https url`，
  无时间无源 = 不可发布；performance 必须 `as_of_UTC + source + benchmark_rationale`。
- **freshness**：`as_of_UTC` 距 snapshot_date >7d 机器直接拦（publish 结构错误）；
  reviewer 按 PRD 48h 理想值从严（>48h 必须 major 起）。
- **readability**：正文 >900 中字 / >500 英词直接拦（>5min）；术语无 explainer 打回。
- **theme_noise**：`score == 五项 true 计数`，`score>=3` 才是 Theme；
  `score<3` 却标 New/Continuing 上首页直接拦（应降级 Noise/Draft，Fading/Dead 除外）。
- **proxy_tradability**：每 Theme 1–3 个 Proxy；ETF 必须有费率；
  必须有 `liquidity_note + why_represents + tracking_gap`；流动性太差打回。
- **冻结后不可变**：`review/<date>/candidate.json` 冻结后字节不可变；
  `data/` 再改就 re-freeze（旧 review 自动作废）。
- **角色分离**：operator 与 reviewer 必须不同名（禁 `self/me`），reviewer 不改 candidate；
  approval 只绑定一个 sha。
- **无 APPROVED 绝不发布**：publish 要求冻结包四件套齐全 + sha 三方一致 +
  零 critical/major + 六个 checks 全 pass + 结构旗标全覆盖。
