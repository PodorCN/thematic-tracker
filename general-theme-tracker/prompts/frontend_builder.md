# Prompt: Frontend Builder（隔离用）

> 版本 v1 · 前端只读 API，Agent 日常更新**禁止**改动 `frontend/`

```text
Build a read-only frontend that ONLY consumes /api/themes/*.
- Stack: Next.js + Tailwind.
- Typography: Title 21px/700, Body 15.5px/1.6, Explainer 13px gray in <details>.
- Theme card shows: status pill, perf table, proxy tickers, timeline with UTC+source link, Depends On table.
- Never fetch raw YAML. Never hardcode theme content.
- Reading progress bar + ~X min label computed from body_text.
```

## 落地说明（v1.1）

- 实际栈为 **Vite + React + TypeScript + Tailwind + shadcn/ui**（本地环境规范，替代 Next.js）；其余约束不变。
- API contract 见 `PRD.md` 第 5 节：`/api/themes/active`、`/api/themes/:id`、`/api/themes/history`、`/api/market/snapshot`、`/api/commentary`。
- 三档字体硬约束：Title 21px/700；Body 15.5px/1.6；Explainer 13px `#6B7280` 折叠；时间轴 Monospace 13px。禁止第四种 size/颜色。
- 任何内容类改动必须来自 `data/` 更新，不允许在前端 hardcode。
