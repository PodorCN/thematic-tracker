import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { fetchTheme, fmtPct, fmtUtc, isStale, torontoToday } from '@/lib/api'
import RebasedChart from '@/sections/RebasedChart'
import { ConvictionTag, NoiseScore, StatusTag } from '@/sections/pills'
import type { Theme } from '@/types/theme'

// Theme detail page — fixed 8-section template (PRD §4), verdict-led broadsheet layout.
// Design: date banner → hero (title + verdict numbers + chart) → thesis → event rail
// → catalyst bull/bear rows → noise score → folded explainer. One bold move only:
// the verdict band (giant excess numbers beside the chart). Everything else quiet.
export default function ThemeDetail() {
  const { id } = useParams<{ id: string }>()
  const [theme, setTheme] = useState<Theme | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    fetchTheme(id)
      .then(setTheme)
      .catch((e) => setErr(e.message))
  }, [id])

  if (err) return <div className="w-full p-8 t-body num-down sm:px-6 lg:px-10">Load failed: {err}</div>
  if (!theme) return <div className="w-full p-8 t-explainer sm:px-6 lg:px-10">Loading…</div>

  const p = theme.performance
  const verdict = [
    { label: '1W excess', v: p.excess_1w },
    { label: '1M excess', v: p.excess_1m },
    { label: 'YTD excess', v: p.excess_ytd },
  ]
  const lastEvent = theme.events.length - 1

  return (
    <div className="w-full px-4 pb-16 sm:px-6 lg:px-10">
      {/* Date banner — very top: is this theme updated today? */}
      {(() => {
        const today = torontoToday()
        const stale = isStale(p.as_of_utc, today)
        return (
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b-2 border-black py-2">
            <span className="t-kicker">Week {theme.week}</span>
            <span className="t-time text-gray-700">Data as of {fmtUtc(p.as_of_utc)}</span>
            <span className="t-time text-gray-500">Today (Toronto) {today}</span>
            <span className="t-tag ml-auto" style={{ color: stale ? '#b45309' : '#0a7d44' }}>
              <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: stale ? '#b45309' : '#0a7d44' }} />
              {stale ? 'Stale — not updated today' : 'Updated today'}
            </span>
          </div>
        )
      })()}

      {/* Back nav + section index */}
      <div className="flex flex-wrap items-baseline gap-x-5 gap-y-1 py-2.5">
        <Link to="/" className="t-kicker hover:text-gray-900 shrink-0">
          ← Today
        </Link>
        <nav className="ml-auto flex flex-wrap gap-x-4">
          <a href="#thesis" className="t-kicker-plain link-ed">Thesis</a>
          <a href="#events" className="t-kicker-plain link-ed">Events</a>
          <a href="#catalysts" className="t-kicker-plain link-ed">Catalysts</a>
          <a href="#verdict" className="t-kicker-plain link-ed">Verdict</a>
        </nav>
      </div>

      {/* 1. Hero */}
      <header className="border-b-2 border-black pb-7 pt-3">
        <p className="t-kicker">Theme · {theme.week} · {theme.horizon}</p>
        <h1 className="t-display mt-3 max-w-4xl">{theme.title}</h1>
        <p className="t-dek mt-3 max-w-2xl">{theme.status_note}</p>
        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1">
          <StatusTag status={theme.status} />
          <ConvictionTag conviction={theme.conviction} />
          <NoiseScore score={theme.theme_vs_noise.score} />
          <span className="t-explainer ml-auto">
            Updated {String(theme.updated_at).slice(0, 10)} · {p.source}
          </span>
        </div>
      </header>

      {/* 2. Verdict — giant excess numbers beside the chart */}
      <section className="border-b border-gray-200 py-7">
        <p className="t-kicker mb-5">Performance vs Benchmark</p>
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-[260px_1fr]">
          <div className="grid grid-cols-3 gap-2 lg:grid-cols-1 lg:gap-0 lg:divide-y lg:divide-gray-200">
            {verdict.map((s) => (
              <div key={s.label} className="lg:py-4 lg:first:pt-0 lg:last:pb-0">
                <p className={`t-stat ${s.v >= 0 ? 'num-up' : 'num-down'}`}>{fmtPct(s.v, 'pp')}</p>
                <p className="t-kicker-plain mt-2">{s.label}</p>
              </div>
            ))}
          </div>
          <div className="min-w-0">
            <RebasedChart series={theme.series} proxyLabel={p.proxy_ticker} benchmarkLabel={p.benchmark_name} />
          </div>
        </div>
        <table className="mt-5 w-full border-t border-gray-300">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="t-kicker-plain py-2 text-left font-bold"></th>
              <th className="t-kicker-plain py-2 text-right font-bold">1W</th>
              <th className="t-kicker-plain py-2 text-right font-bold">1M</th>
              <th className="t-kicker-plain py-2 text-right font-bold">YTD</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-gray-100">
              <td className="t-time py-2 font-bold text-gray-900">{p.proxy_ticker}</td>
              <td className="t-time py-2 text-right">{fmtPct(p.ret_1w)}</td>
              <td className="t-time py-2 text-right">{fmtPct(p.ret_1m)}</td>
              <td className="t-time py-2 text-right">{fmtPct(p.ret_ytd)}</td>
            </tr>
            <tr className="border-b border-gray-300">
              <td className="t-time py-2 text-gray-500">{p.benchmark_name}</td>
              <td className="t-time py-2 text-right text-gray-500">{fmtPct(p.benchmark_ret_1w)}</td>
              <td className="t-time py-2 text-right text-gray-500">{fmtPct(p.benchmark_ret_1m)}</td>
              <td className="t-time py-2 text-right text-gray-500">{fmtPct(p.benchmark_ret_ytd)}</td>
            </tr>
          </tbody>
        </table>
        <p className="t-explainer mt-3">
          {p.proxy_ticker} {p.proxy_price} {p.currency} · {p.return_type === 'price' ? 'Price Return' : 'Total Return'} · as of{' '}
          <span className="t-time">{fmtUtc(p.as_of_utc)}</span> · {p.source} · Benchmark: {p.benchmark_rationale}
        </p>
      </section>

      {/* 3. Proxy to Track */}
      <section className="border-b border-gray-200 py-7">
        <p className="t-kicker mb-4">Proxy to Track</p>
        <div className="space-y-5">
          {theme.proxies.map((px, i) => (
            <div key={px.ticker} className="flex gap-4">
              <span className="t-stat shrink-0 text-gray-200" style={{ fontSize: 24 }}>
                {String(i + 1).padStart(2, '0')}
              </span>
              <div className="max-w-3xl">
                <p className="flex flex-wrap items-baseline gap-x-3">
                  <span className="t-time text-[15px] font-bold text-gray-900">{px.ticker}</span>
                  <span className="t-body font-bold">{px.name}</span>
                  <span className="t-kicker-plain">
                    {px.type} · {px.region}
                    {px.expense ? ` · ${px.expense}` : ''}
                  </span>
                </p>
                <p className="t-body mt-1 text-gray-700">
                  {px.why_represents} Liquidity: {px.liquidity_note}.
                </p>
                <p className="t-explainer mt-1">Flaw: {px.tracking_gap}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 4. Why Now / Thesis */}
      <section id="thesis" className="border-b border-gray-200 py-7">
        <p className="t-kicker mb-4">Why Now / Thesis</p>
        <p className="t-body max-w-3xl whitespace-pre-line">
          {theme.body_text}
        </p>
      </section>

      {/* 5. Key Events — rail timeline, latest marked red */}
      <section id="events" className="border-b border-gray-200 py-7">
        <p className="t-kicker mb-5">Key Events</p>
        <div className="space-y-6 border-l border-gray-200 pl-6 sm:pl-8">
          {theme.events.map((ev, i) => (
            <div key={i} className="relative">
              <span
                className="absolute top-1.5 h-2 w-2 rounded-full"
                style={{
                  left: '-1.75rem',
                  background: i === lastEvent ? '#e51503' : '#111111',
                }}
              />
              <p className="t-time text-gray-500">
                {fmtUtc(ev.event_time_utc)}
                {ev.return_window ? ` · ${ev.return_window}` : ''}
              </p>
              <p className="t-body mt-1 max-w-3xl">{ev.title}</p>
              {ev.proxy_ret !== undefined && ev.benchmark_ret !== undefined && (
                <p className="t-time mt-1">
                  <span className={ev.proxy_ret >= 0 ? 'num-up' : 'num-down'}>
                    {p.proxy_ticker} {fmtPct(ev.proxy_ret)}
                  </span>
                  <span className="text-gray-400"> vs </span>
                  <span className="text-gray-700">
                    {p.benchmark_name} {fmtPct(ev.benchmark_ret)}
                  </span>
                  <span className={ev.proxy_ret - ev.benchmark_ret >= 0 ? 'num-up' : 'num-down'}>
                    {' '}({fmtPct(ev.proxy_ret - ev.benchmark_ret, 'pp')} active)
                  </span>
                </p>
              )}
              <p className="t-explainer mt-0.5">
                <span className="t-kicker-plain mr-2">{ev.type}</span>
                <a href={ev.url} target="_blank" rel="noreferrer" className="link-ed">
                  {ev.source} ↗
                </a>
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* 6. Depends On / What to Watch — bull/bear decision rows */}
      <section id="catalysts" className="border-b border-gray-200 py-7">
        <p className="t-kicker mb-4">Depends On / What to Watch</p>
        <div className="space-y-6">
          {theme.depends_on.map((d, i) => (
            <div key={i} className="border-t border-gray-300 pt-4">
              <div className="flex flex-wrap items-baseline gap-x-3">
                <p className="t-body font-bold">{d.event_name}</p>
                <span className="t-time text-gray-500">{d.due_date.slice(0, 10)}</span>
              </div>
              <p className="t-explainer mt-1 max-w-3xl">{d.why_matters}</p>
              <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="border-l-2 pl-3" style={{ borderColor: '#0a7d44' }}>
                  <p className="t-kicker-plain">Bull</p>
                  <p className="t-body num-up mt-1">{d.if_bull}</p>
                </div>
                <div className="border-l-2 pl-3" style={{ borderColor: '#c0352b' }}>
                  <p className="t-kicker-plain">Bear / falsifier</p>
                  <p className="t-body num-down mt-1">{d.if_bear}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 7. Theme vs Noise */}
      <section id="verdict" className="border-b border-gray-200 py-7">
        <p className="t-kicker mb-4">Theme vs Noise</p>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5">
          <NoiseScore score={theme.theme_vs_noise.score} />
            {(
              [
                ['persistence', 'Persistence'],
                ['breadth', 'Breadth'],
                ['volume_confirm', 'Price-volume confirmation'],
                ['falsifiable_catalyst', 'Falsifiable catalyst'],
                ['repricing_logic', 'Re-pricing logic'],
              ] as const
            ).map(([k, label]) => (
            <span key={k} className={`t-explainer ${theme.theme_vs_noise[k] ? 'text-gray-900' : 'text-gray-400'}`}>
              {theme.theme_vs_noise[k] ? '✓' : '✗'} {label}
            </span>
          ))}
        </div>
      </section>

      {/* 8. Explainer (folded by default) */}
      {theme.explainer && (
        <section className="py-7">
          <details>
            <summary className="t-kicker cursor-pointer hover:text-gray-900">Conventions & terms</summary>
            <p className="t-explainer mt-3 max-w-3xl whitespace-pre-line border-l-2 border-gray-200 pl-4">{theme.explainer}</p>
          </details>
        </section>
      )}
    </div>
  )
}
