# AGENT.md — Fed × BOC Watcher（美加央行拔河看板）

> ⚠️ 本文件夹**不走**根目录 `agent.md` 的每日 theme SOP（没有 `theme.md`、没有 proxy、没有 VALIDITY 灯）。
> 更重要的是：**这个页面不能自动发布**，它有一道独立的 PM 审阅闸门。
> 闸门规则见 [`PM_REVIEW_GATE.md`](./PM_REVIEW_GATE.md)（必读），
> 运维手册见 [`../docs/MACRO_DATA_OPERATIONS.md`](../docs/MACRO_DATA_OPERATIONS.md)，
> 数据 schema 见 [`BACKEND_DATA_SPEC.md`](./BACKEND_DATA_SPEC.md)。

## 文件夹结构

```
fed-boc-watcher/
  index.html                 前端页面（只读数据，不为改内容而动它）
  data/
    dashboard.json           暂存输入：operator 研究后写这里，尚未发布
    dashboard.example.json   精简示例，看字段结构用
    latest.json              已发布的最新看板，页面默认读取
    dates.json               日期清单
    archive/<date>.json      每日不可变快照
  review/<date>/iteration-NN/
    candidate.json           冻结的候选载荷（送审后字节不可变）
    candidate.sha256         候选摘要，审阅结论靠它绑定
    pm-review.json           独立 PM 的结构化审阅结论
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
# 闸门校验 + 发布（verdict 必须是 approved，且 sha256 必须对上 candidate 字节）
python scripts/econ/archive_fed_boc.py \
  --input      fed-boc-watcher/data/dashboard.json \
  --candidate  fed-boc-watcher/review/<date>/iteration-NN/candidate.json \
  --pm-review  fed-boc-watcher/review/<date>/iteration-NN/pm-review.json
```

`archive_fed_boc.py` 会先跑 `driver_quality.check_payload`（驱动时间戳一致性），
不一致就**拒绝发布**——`latest.json` 保留上一份自洽快照，页面自己的 `stale` 标记会告诉读者数据没推进。

PM 判 `revise` 时用 `scripts/econ/record_pm_feedback.py` 记录反馈，重开一个 iteration，不要原地改 candidate。

## 红线

- **绝不自动发布**：日更 workflow 只发 economic-calendar，Fed/BOC 永远要人过闸门。
- **禁止编造**：政策利率、点阵图、市场定价、驱动数据都必须有来源 URL；搜不到就标注不明，不要填空。
- **candidate 送审后字节冻结**：要改就开新 iteration（`iteration-NN` 递增），旧的保留存证。
- **时区**：对外显示一律 `America/Toronto`，源时间戳保留 UTC offset。
