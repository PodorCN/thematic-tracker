# AGENT.md — Fed × BOC Watcher（美加央行拔河看板）

> ⚠️ 本文件夹**不走**根目录 `agent.md` 的每日 theme SOP（没有 `theme.md`、没有 proxy、没有 VALIDITY 灯）。
> 更重要的是：**这个页面不能自动发布**，它有一道独立的 PM 审阅闸门。
> 闸门规则见 [`PM_REVIEW_GATE.md`](./PM_REVIEW_GATE.md)（必读），
> 运维手册见 [`../docs/MACRO_DATA_OPERATIONS.md`](../docs/MACRO_DATA_OPERATIONS.md)，
> 数据 schema 见 [`BACKEND_DATA_SPEC.md`](./BACKEND_DATA_SPEC.md)。

## 文件夹结构

```
fed-boc-watcher/
  index.html                 固定前端渲染器；日常只读取 data/latest.json，不参与数据提交
  data/
    dashboard.json           暂存输入：operator 研究后写这里，尚未发布
    dashboard.example.json   精简示例，看字段结构用
    latest.json              已发布的最新看板，页面默认读取。**只有 archive 脚本能写**
    dates.json               日期清单
    archive/<date>.json      每日不可变快照
  review/<date>/iteration-NN/
    candidate.json           冻结的候选载荷（送审后字节不可变）
    candidate.sha256         候选摘要，审阅结论靠它绑定
    pm-review.json           独立 PM 的结构化审阅结论（必须由 reviewer 亲手写）
    pm-handoff.json          交接记录
    evidence/                当次审阅抓取的原始证据（官方声明、CPI/LFS、市场报价等）
```

## 角色分离（不可合并）

| 角色 | 能做 | 不能做 |
|---|---|---|
| Operator | 研究、写 `data/dashboard.json`、冻结 candidate | **不能批准自己的工作** |
| PM Reviewer | 拿冻结的 candidate + evidence 挑刺，只写 `pm-review.json` | 不能改 candidate |
| Publisher | 闸门校验通过后才能 archive / commit / push | 没有 `approved` 就不能发布 |

## 发布流程

```bash
# 0) 结构闸门：退出码非 0 = 不得冻结送审，更不得发布
uv run --isolated --python 3.11 python scripts/econ/structural_gate.py \
  --candidate fed-boc-watcher/review/<date>/iteration-NN/candidate.json \
  --baseline fed-boc-watcher/review/<date>/iteration-(NN-1)/candidate.json \
  --out fed-boc-watcher/review/<date>/iteration-NN/structural-gate.json

# 1) PM 闸门：verdict 必须是 approved，且 sha256 必须对上 candidate 字节
uv run --isolated --python 3.11 --with-requirements requirements.txt \
  python scripts/econ/validate_pm_review.py \
  --candidate fed-boc-watcher/review/<date>/iteration-NN/candidate.json \
  --review   fed-boc-watcher/review/<date>/iteration-NN/pm-review.json \
  --require-approved

# 1.5) 钉选渲染验收：必须钉住本轮冻结 candidate 跑渲染真值测试。
#      未钉选时这些测试按设计 skip —— 不跑等于没验收；candidate 缺 tenor key 时必须 fail 而非 skip。
FED_BOC_RENDER_CANDIDATE="$PWD/fed-boc-watcher/review/<date>/iteration-NN/candidate.json" \
uv run --isolated --python 3.11 --with-requirements requirements.txt \
  python -m pytest tests/test_render_truthfulness.py -q

# 2) 发布
uv run --isolated --python 3.11 --with-requirements requirements.txt \
  python scripts/econ/archive_fed_boc.py \
  --input      fed-boc-watcher/data/dashboard.json \
  --candidate  fed-boc-watcher/review/<date>/iteration-NN/candidate.json \
  --pm-review  fed-boc-watcher/review/<date>/iteration-NN/pm-review.json

# 3) 只 stage 这一轮明确批准的 data JSON 与审阅证据，禁止 git add fed-boc-watcher/ 或 git add .
#    若 index.html、脚本、AGENT.md 或另一产品混入 staged diff，立即中止。
git add fed-boc-watcher/data/latest.json fed-boc-watcher/data/dates.json \
  fed-boc-watcher/data/archive/<date>.json \
  fed-boc-watcher/review/<date>/iteration-NN/candidate.json \
  fed-boc-watcher/review/<date>/iteration-NN/candidate.sha256 \
  fed-boc-watcher/review/<date>/iteration-NN/pm-review.json
python scripts/econ/verify_data_only_changes.py --product fed-boc-watcher --staged
# 检查结果、代码 diff、独立 PM 审阅均通过后才提交；推送前重新核对 exact range。
python scripts/econ/verify_data_only_changes.py --product fed-boc-watcher --range origin/main..HEAD
```

`archive_fed_boc.py` 内部会**再跑一遍**结构闸门和 `driver_quality.check_payload`；
任何一项不一致就**拒绝发布**——`latest.json` 保留上一份自洽快照，页面自己的 `stale`
标记会告诉读者数据没推进。

PM 判 `revise` 时用 `scripts/econ/record_pm_feedback.py` 记录反馈，重开一个 iteration，不要原地改 candidate。

## 机器管结构，PM 管判断（2026-09-28 定）

`scripts/econ/structural_gate.py` 有 13 项检查，**全部不做自然语言匹配**：

`required_containment` `as_of_coherence` `market_close_semantics` `provenance_traceability`
`pricing_honesty` `derived_numbers` `driver_chronology` `driver_side_signs`
`calendar_rendered` `renderer_contract` `evidence_contains_claim`
`published_path_provenance` `price_threshold_arithmetic`

- **机器**只做不需要读英文的检查：哈希、时间戳顺序、概率边界与加总、涨跌幅重算、
  驱动侧别符号、证据里是否真含该数字、阈值算术。
- **PM** 判断两件机器做不了的事：数据是否准确（对着官网核）、结论是否有意义。
- **Operator 不代替 PM 判断**，也不评价 PM 的判断。

⚠️ **绝不要用自然语言规则替 PM 判断**。旧版本曾用星期几配对、动词/名词词表、否定守卫、
文案日期回溯，结果两轮独立 PM 评审用同义词和日期格式就绕过了（`retrieved`→`downloaded`、
`Sep 27`→`27 September`），而且它把 `returned HTTP 403` 里的 `return` 当成行情词，
对**正确**的候选报事实错误的结论。**不要重新实现这一层。**

## 日常数据 / 网页代码分离（必须执行）

- 日常只更新 `data/*.json`、明确批准的候选/审阅证据；`index.html` 是独立前端版本。即便发现字段没显示，也只能先停数据发布、开单独的前端 PR 解决，不得把 JS/CSS 改动偷偷夹在数据提交里。前端 PR 更新 `scripts/econ/frontend_contract.json` 的 SHA-256，并做桌面及手机真实浏览器验收；只有独立代码审阅通过才合并。哈希本身不是审阅证明。
- 数据发布必须运行 `verify_data_only_changes.py --product fed-boc-watcher --staged` 和推送前 `--range origin/main..HEAD`；它比“我检查过 diff”更可靠：不允许把 HTML、Python、文档或别的页面的数据混进来；`latest` 必须等于归档 JSON，且除归档三个字段外与获批候选相同。审阅者身份仍须人工核实，机器不能凭文件名证明是谁写的。
- 新候选已被 PM 判 `revise` 就不能用旧快照冒充当日更新。跨日发布先重查当日已公布的数据、日历状态和可交易结论；过期内容必须重收集/重审，不能只改 `snapshot_date`。浏览器验收包括首屏两张核心卡片是否无需读完长篇报告即可看到、移动端布局，以及未来事件是否已经发生。

## 红线

- **绝不自动发布**：日更 workflow 只发 economic-calendar，Fed/BOC 永远要人过闸门。
- **禁止编造**：政策利率、点阵图、市场定价、驱动数据都必须有来源 URL；搜不到就标注不明，不要填空。
- **candidate 送审后字节冻结**：要改就开新 iteration（`iteration-NN` 递增），旧的保留存证。
- **时区**：对外显示一律 `America/Toronto`，源时间戳保留 UTC offset。

---

# 血的教训（2026-09-28，四轮 PM 评审换来）

下面每一条都对应一次真实事故。写的是**规则**；事故细节在
`review/2026-09-28/iteration-04/verification_note.gate_findings_this_round` 里。

## 1. 改了数字 ≠ 有证据

我把密歇根从初值 47.8 改成终值 48.1，只改了显示字段，**没重新抓证据**。绑定的还是
9/24 那份只含 47.8 的抓取——PM 一 grep 就发现 48.1 出现 0 次。

**规则**：改任何显示值前，先确认绑定证据里真的有这个数。值对了但证据不支持，比值错了
更危险，因为它看起来是对的。`evidence_contains_claim` 会拦，但它的存在不免除你核对的
责任。

## 2. 会误报的闸门比没闸门更危险

我加了个新检查，它报"加拿大零售 +0.6% 无证据"。我照着改了——把那个**本来正确**的数字
改成"无证据"的假声明，页面因此自相矛盾。PM 抓住后我去查，证据一直都在：绑定文件里
钉着一行 `matching_row`，写着 `previous: 0.6`。

根因是匹配器生成了带符号和数字碎片的变体（`+0.6%` → `+0.6`，`0.6%` → `-6`），真实文件里
的 `0.6` 永远匹配不上。

**规则**：闸门报错时，**先去查源头，再决定改不改**。把机器当权威会让你把对的改成错的。
一个会哭狼的闸门会训练所有人忽略它。

## 3. 每次出问题，就在出错的那个地方加检查

页面凭空显示 "Hike 62%" 这个 bug 活在 `index.html` 的 CSS 里（`.bbar` 的 `display:flex`
压过了 `[hidden]` 属性），而我所有的 Python 检查都看不见它——我当时只翻�� decision frame，
没翻上面的 odds 卡片。

**规则**：修完 bug 问"什么东西本可以拦住它"，然后在**那个位置**加检查：

| 事故 | 加在哪 | 检查名 |
|---|---|---|
| 数值无证据 | 数据层 | `evidence_contains_claim` |
| 页面编造数字 | 真实浏览器渲染 | `tests/test_render_truthfulness.py` |
| 阈值算术错 | brief 结构化字段 | `price_threshold_arithmetic` |
| 未批准候选进线上 | 发布路径 | `published_path_provenance` |
| 字段写了没人渲染 | 渲染契约 | `renderer_contract` |

**只做结构检查不够**：Python 看不见 CSS/JS 的 bug，必须有真浏览器渲染测试。

## 4. 每个新检查都要变异测试

写完检查要**关掉它**，确认测试变红。两次空变异教会我的：`problems.append(` 改成
`pass; problems.append(` 根本没断掉 append，测试照样绿；fixture 写得太短，范围窗口
看不见关键信息，测试"通过"的理由是错的。

**规则**：**假绿比没测试更危险**，因为它让我以为有防线。空变异（grep 找不到行、sed
没生效）必须重做到真失败为止。

## 5. 改完必须读回来验证，不能"我认为改好了"

三次同类错，全是"我以为做完了"：
- 冻结时读了旧文件 → 修改没写进去，页面上还是旧值。
- 备份拿晚了 → "还原"等于没还原，是 `git status` 发现的。
- 函数留了两份副本 → 后一份静默盖掉前一份，闸门行为跟预期不符。

**规则**：改完冻结产物**重新读回来**再宣布完成；写之前备份，并**验备份里是不是你以为是
的内容**（我当时备份的是已污染的文件，验 `as_of` 才发现）。`git status` / `git diff`
是最后一道，不是礼节。

## 6. `index.html` 是数据契约的一部分

我把 `trade_status` 写成 "NO TRADE — but for a stated reason"，而渲染器对
`'NO TRADE / NO EDGE'` 做**精确字符串相等**判断，三处 `noEdge` 分支全部失效，银行卡片
会改口打印 "Hawkish +3.0 — data strongly favours tightening"——跟旁边的 NO TRADE 框
自相矛盾。

**规则**：改任何 brief 字段前，先去 `index.html` 看**渲染器实际怎么消费它**：精确 token、
badge map、class 复用都要对上。`renderer_contract` 会检查字段是否被读，但"被读了"不等于
"读对了"。

## 7. brief 必须每次重写，不能继承

历史上 43 个候选里 **41 份没有 `decision_brief`**，31 份 feedback 里 30 份卡在
`decision_usefulness`。reviewer 反复说"不值得一个 PM 花 3.5 分钟"，我反复"改进 brief"
——但问题不是写不好，是**压根没写**。

**规则**：
- 每轮从零写 `decision_brief`，禁止从上一版 candidate / `dashboard.json` / `latest.json`
  继承任何文案。
- 必须包含渲染器 `renderDecisionBrief` 实际读取的字段，否则渲染空白。
- 历史候选只可读两个标量（`as_of` / `snapshot_date`）用于"相对上次"的对照。
- `--baseline` 会让闸门报告 `brief regenerated: True/False`。报 `False` 时你必须能说清
  "哪句结论变了"；说不清就是抄的。
- 内容约束：必须有观点（"不交易"只有写清为什么、什么条件会改变它才算数）、`falsifiers`
  给具体条件和日期、代理合约标注是季度均值而非会议概率。

## 8. 不得手改 `data/latest.json`

`latest.json` 是读者看到的东西，**只有 `archive_fed_boc.py` 能写**，且只写已批准的
candidate。我出过两次：一次为验渲染把候选拷进去、"还原"备份拿晚了等于没还原；一次是
PM reviewer 撞了工具预算没来得及还原。

**规则**：要验渲染就把候选拷进去，**但先备份并验备份**；或者起本地 server 读别处。
事后一律 `git checkout -- fed-boc-watcher/data/latest.json` 并用 `git status --porcelain`
确认干净。`published_path_provenance` 会拦未批准候选，也会拦手改的 `as_of`（跟 git HEAD
有差异且无 archiver 戳）。

## 9. 不得用 review 日志当批准凭证

我派 PM reviewer 走独立进程，它返回 `approved` 但**撞了 60/60 工具预算，文件没落地**。
我照着日志把 `pm-review.json` 转录出来，sha 是**我**绑的不是它绑的。

**规则**：
- `pm-review.json` 必须由 reviewer 亲手写盘并**绑定 candidate 的 sha**。
- reviewer 没落盘 = 这一轮**不算审过**。重新派一轮，或让它续跑把文件写出来。
- 永远不要拿"日志里说过 approved"当批准凭证；发布不可逆。
- 我转录过的那份（`review-artifacts/candidate-2026-09-28-iter04-r2/`）在同目录有
  `transcription-provenance.json` 说明来源，但它不是 reviewer 签的字。

## 10. 给 reviewer 的 prompt 必须能过自己的校验

我给 reviewer 写的 check 键名（`data_accuracy` / `decision_usefulness` /
`digest_verification` / `feedback_resolved`）跟仓库里 `review/pm-review.schema.json` 和
`validate_pm_review.py` 认的六个键（`official_policy` / `pricing` / `drivers` /
`market_validation` / `freshness` / `decision_usefulness`）**不一致**。reviewer 忠实写了我
要求的格式，我的闸门拒了，我还得手工重排键名——**浪费一整轮**。

**规则**：派审前先读 `review/pm-review.schema.json`，prompt 里给的字段名必须和它**一字不差**。
approved 的 review 不许带 `operator_instructions`（校验会拒），需要传达的内容放进
`executive_summary`。

## 11. 上线前必须验真实页面，不能只看仓库

`git push` 成功 ≠ 线上更新了。rebase、CDN 缓存、Pages 构建都可能让线上还是旧的。

**规则**：发布后必须
1. `curl` 线上 `data/latest.json`（带 cache-buster），确认 HTTP 200、`as_of` 是新的、内容与
   已批准 candidate 逐字段一致（archiver 只加 `archived_at`/`snapshot_date`/`stale`）；
2. 浏览器打开真实页面，确认 brief 真渲染出来了（新字段在、假数字不在）。

## 12. 时区和"重新抓"的纪律

跨天跑必须全部重抓，不能复用前一天的 capture。驱动卡的 actual 必须是**最新一次发布**，
不是初值；`published_at_toronto` / `observed_at_toronto` 随之更新。

**规则**：警惕任何"从别处改一个字段"的快捷方式——本轮大部分事故都是"改字段而不是重新
取证"的下场。
