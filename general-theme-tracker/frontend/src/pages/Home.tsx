import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { fetchActive, fetchSnapshot, fmtChg, fmtPct, fmtUtc, readingMinutes } from '@/lib/api'
import { ConvictionTag, NoiseScore, StatusTag } from '@/sections/pills'
import type { ActiveResponse, Snapshot, Theme } from '@/types/theme'

const DIFF_COLOR: Record<string, string> = {
  new: '#e51503',
  continuing: '#0a7d44',
  fading: '#b45309',
  dead: '#9ca3af',
}

const STATUS_RANK: Record<string, number> = { New: 0, Emerging: 1, Continuing: 2, Fading: 3, Dead: 4 }

export default function Home() {
  const [active, setActive] = useState<ActiveResponse | null>(null)
  const [snap, setSnap] = useState<Snapshot | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([fetchActive(), fetchSnapshot()])
      .then(([a, s]) => {
        setActive(a)
        setSnap(s)
      })
      .catch((e) => setErr(e.message))
  }, [])

  if (err)
    return (
      <div className="w-full p-8 sm:px-6 lg:px-10">
        <p className="t-body num-down">API 连接失败：{err}。请确认已用 npm run dev 启动（backend :8787）。</p>
      </div>
    )
  if (!active || !snap) return <div className="w-full p-8 t-explainer sm:px-6 lg:px-10">加载中…</div>

  const themes = [...active.themes].sort((a, b) => (STATUS_RANK[a.status] ?? 9) - (STATUS_RANK[b.status] ?? 9))
  const lead: Theme | undefined = themes[0]
  const rest = themes.slice(1)

  return (
    <div className="w-full px-4 sm:px-6 lg:px-10">
      {/* Ticker tape */}
      <div className="rule flex flex-wrap items-baseline gap-x-5 gap-y-1.5 border-b border-gray-200 py-2.5 sm:gap-x-7">
        {snap.benchmarks.map((b) => (
          <span key={b.ticker} className="inline-flex items-baseline gap-1.5 whitespace-nowrap">
            <span className="t-kicker-plain">{b.name}</span>
            <span className="t-time font-semibold text-gray-900">{b.value.toLocaleString()}</span>
            <span className={`t-time font-semibold ${b.chg_1d >= 0 ? 'num-up' : 'num-down'}`}>
              {b.chg_1d >= 0 ? '▲' : '▼'}
              {fmtChg(Math.abs(b.chg_1d), b.chg_unit).replace('+', '')}
            </span>
          </span>
        ))}
        <span className="t-time bb-red ml-auto max-sm:w-full max-sm:text-right">{fmtUtc(snap.as_of_utc)}</span>
      </div>

      {/* 头版头条：Market Regime */}
      <section className="border-b-2 border-black py-7 sm:py-10">
        <div className="flex items-baseline justify-between">
          <p className="t-kicker">Market Regime</p>
          <p className="t-kicker">Week {snap.week}</p>
        </div>
        <h1 className="t-display mt-4 max-w-4xl">{snap.regime.oneliner}</h1>
        <p className="t-dek mt-4">
          <span className="font-bold text-gray-900">{snap.regime.stance}</span>
          {' · '}
          {snap.regime.keywords.join(' · ')}
        </p>
      </section>

      {/* 主打 Theme 特写 */}
      {lead && (
        <section className="border-b border-gray-200 py-8">
          <p className="t-kicker mb-4">Lead Theme</p>
          <div className="grid grid-cols-1 gap-8 md:grid-cols-[1fr_240px]">
            <div>
              <Link to={`/theme/${lead.id}`} className="group">
                <h2 className="t-display-sm group-hover:underline decoration-2 underline-offset-4">{lead.title}</h2>
                <p className="t-dek mt-3 max-w-xl">{lead.status_note}</p>
              </Link>
              <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1">
                <StatusTag status={lead.status} />
                <ConvictionTag conviction={lead.conviction} />
                <span className="t-explainer">{lead.horizon}</span>
                <NoiseScore score={lead.theme_vs_noise.score} />
              </div>
            </div>
            <Link to={`/theme/${lead.id}`} className="block border-l-0 max-md:border-t max-md:border-gray-200 max-md:pt-5 md:border-l md:border-gray-200 md:pl-6">
              <p className="t-kicker">{lead.performance.proxy_ticker} vs {lead.performance.benchmark_name}</p>
              <p className={`t-stat mt-3 ${lead.performance.excess_1m >= 0 ? 'num-up' : 'num-down'}`}>
                {fmtPct(lead.performance.excess_1m, 'pp')}
              </p>
              <p className="t-explainer mt-1.5">1M 超额收益</p>
              <p className="t-time mt-4 text-gray-700">
                1W {fmtPct(lead.performance.excess_1w, 'pp')} · YTD {fmtPct(lead.performance.excess_ytd, 'pp')}
              </p>
              <p className="t-explainer mt-3">~{readingMinutes(lead.body_text)} min read →</p>
            </Link>
          </div>
        </section>
      )}

      {/* Yesterday → Today */}
      <section className="border-b border-gray-200 py-7">
        <p className="t-kicker mb-4">Yesterday → Today</p>
        <div className="grid grid-cols-1 gap-x-10 gap-y-3 sm:grid-cols-2">
          {snap.yesterday_diff.map((d) => {
            const theme = active.themes.find((t) => t.id === d.theme_id)
            return (
              <div key={d.theme_id} className="flex items-baseline gap-3">
                <span className="t-tag shrink-0" style={{ color: DIFF_COLOR[d.change] }}>
                  <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: DIFF_COLOR[d.change] }} />
                  {d.change}
                </span>
                <span>
                  {theme ? (
                    <Link to={`/theme/${d.theme_id}`} className="t-body font-bold hover:underline">
                      {theme.title}
                    </Link>
                  ) : (
                    <span className="t-body text-gray-500">{d.theme_id}</span>
                  )}
                  <span className="t-explainer"> — {d.note}</span>
                </span>
              </div>
            )
          })}
        </div>
      </section>

      {/* 其余 Themes — 索引 */}
      <section className="py-7">
        <div className="flex items-baseline justify-between">
          <p className="t-kicker">Also Active</p>
          <span className="t-explainer">共 {active.count} 个</span>
        </div>
        <div>
          {rest.map((t, i) => (
            <Link key={t.id} to={`/theme/${t.id}`} className="group flex items-baseline gap-4 border-b border-gray-200 py-5 transition-colors hover:bg-gray-50/70 sm:gap-6">
              <span className="t-display-sm w-9 shrink-0 text-gray-200 sm:w-12">{String(i + 2).padStart(2, '0')}</span>
              <div className="flex-1">
                <h2 className="t-title group-hover:underline decoration-1 underline-offset-4">{t.title}</h2>
                <p className="t-explainer mt-1 max-w-2xl">{t.status_note}</p>
                <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1">
                  <StatusTag status={t.status} />
                  <ConvictionTag conviction={t.conviction} />
                  <NoiseScore score={t.theme_vs_noise.score} />
                </div>
              </div>
              <div className="hidden shrink-0 text-right sm:block">
                <p className="t-time font-bold text-gray-900">{t.performance.proxy_ticker}</p>
                <p className={`t-time mt-1 text-[15px] font-semibold ${t.performance.excess_1m >= 0 ? 'num-up' : 'num-down'}`}>
                  {fmtPct(t.performance.excess_1m, 'pp')}
                </p>
                <p className="t-explainer mt-0.5">1M 超额 · ~{readingMinutes(t.body_text)} min</p>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
