import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { fetchTheme, fmtPct, fmtUtc, readingMinutes } from '@/lib/api'
import RebasedChart from '@/sections/RebasedChart'
import { ConvictionTag, NoiseScore, StatusTag } from '@/sections/pills'
import type { Theme } from '@/types/theme'

// Theme detail page — fixed 8-section template (PRD §4), broadsheet feature layout
export default function ThemeDetail() {
  const { id } = useParams<{ id: string }>()
  const [theme, setTheme] = useState<Theme | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (!id) return
    fetchTheme(id)
      .then(setTheme)
      .catch((e) => setErr(e.message))
  }, [id])

  useEffect(() => {
    const onScroll = () => {
      const h = document.documentElement
      const max = h.scrollHeight - h.clientHeight
      setProgress(max > 0 ? Math.min(100, (h.scrollTop / max) * 100) : 100)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  if (err) return <div className="w-full p-8 t-body num-down sm:px-6 lg:px-10">Load failed: {err}</div>
  if (!theme) return <div className="w-full p-8 t-explainer sm:px-6 lg:px-10">Loading…</div>

  const p = theme.performance
  const mins = readingMinutes(theme.body_text)
  const stats = [
    { label: '1W excess', v: p.excess_1w },
    { label: '1M excess', v: p.excess_1m },
    { label: 'YTD excess', v: p.excess_ytd },
  ]

  return (
    <div className="w-full px-4 pb-16 sm:px-6 lg:px-10">
      {/* Reading progress bar */}
      <div className="sticky top-0 z-10 -mx-4 bg-white/95 px-4 py-2 backdrop-blur sm:-mx-6 sm:px-6 lg:-mx-10 lg:px-10">
        <div className="flex items-center gap-3">
          <Link to="/" className="t-kicker hover:text-gray-900 shrink-0">
            ← Today
          </Link>
          <div className="h-px flex-1 bg-gray-200">
            <div className="h-px bg-[#e51503] transition-all" style={{ width: `${progress}%` }} />
          </div>
          <span className="t-explainer shrink-0">~{mins} min</span>
        </div>
      </div>

      {/* 1. Header */}
      <header className="border-b-2 border-black pb-6 pt-6">
        <p className="t-kicker">Theme · {theme.week} · {theme.horizon}</p>
        <h1 className="t-display-sm mt-3 max-w-4xl">{theme.title}</h1>
        <p className="t-dek mt-3 max-w-2xl">{theme.status_note}</p>
        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1">
          <StatusTag status={theme.status} />
          <ConvictionTag conviction={theme.conviction} />
          <span className="t-explainer ml-auto">
            Updated {String(theme.updated_at).slice(0, 10)} · {p.source} · ~{mins} min read
          </span>
        </div>
      </header>

      {/* 2. Performance vs Benchmark — big numbers + chart */}
      <section className="border-b border-gray-200 py-7">
        <p className="t-kicker mb-5">Performance vs Benchmark</p>
        <div className="grid grid-cols-3 gap-2 border-y border-gray-200 py-4 sm:gap-4">
          {stats.map((s) => (
            <div key={s.label} className="text-center">
              <p className={`t-stat ${s.v >= 0 ? 'num-up' : 'num-down'}`}>{fmtPct(s.v, 'pp')}</p>
              <p className="t-kicker-plain mt-2">{s.label}</p>
            </div>
          ))}
        </div>
        <div className="mt-5">
          <RebasedChart series={theme.series} proxyLabel={p.proxy_ticker} benchmarkLabel={p.benchmark_name} />
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
      <section className="border-b border-gray-200 py-7">
        <p className="t-kicker mb-4">Why Now / Thesis</p>
        <p className="t-body max-w-3xl whitespace-pre-line first-letter:text-[52px] first-letter:font-bold first-letter:leading-none first-letter:float-left first-letter:mr-2 first-letter:mt-1">
          {theme.body_text}
        </p>
      </section>

      {/* 5. Key Events */}
      <section className="border-b border-gray-200 py-7">
        <p className="t-kicker mb-4">Key Events</p>
        <div className="space-y-4">
          {theme.events.map((ev, i) => (
            <div key={i} className="flex gap-5">
              <span className="t-time w-24 shrink-0 border-r border-gray-200 pr-3 pt-0.5 text-gray-500 sm:w-28 sm:pr-4">
                {fmtUtc(ev.event_time_utc)}
              </span>
              <div className="max-w-3xl">
                <p className="t-body">{ev.title}</p>
                <p className="t-explainer mt-0.5">
                  <span className="t-kicker-plain mr-2">{ev.type}</span>
                  <a href={ev.url} target="_blank" rel="noreferrer" className="link-ed">
                    {ev.source} ↗
                  </a>
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 6. Depends On / What to Watch */}
      <section className="border-b border-gray-200 py-7">
        <p className="t-kicker mb-4">Depends On / What to Watch</p>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[620px] border-t border-gray-300">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="t-kicker-plain py-2 text-left">Checkpoint</th>
              <th className="t-kicker-plain py-2 text-left">Date UTC</th>
              <th className="t-kicker-plain py-2 text-left">Bull</th>
              <th className="t-kicker-plain py-2 text-left">Bear / falsifier</th>
            </tr>
          </thead>
          <tbody>
            {theme.depends_on.map((d, i) => (
              <tr key={i} className="border-b border-gray-100 align-top">
                <td className="py-3 pr-4">
                  <p className="t-body font-bold">{d.event_name}</p>
                  <p className="t-explainer mt-0.5">{d.why_matters}</p>
                </td>
                <td className="t-time py-3 pr-4 whitespace-nowrap text-gray-700">{d.due_date.slice(0, 10)}</td>
                <td className="t-body py-3 pr-4 num-up">{d.if_bull}</td>
                <td className="t-body py-3 num-down">{d.if_bear}</td>
              </tr>
            ))}
          </tbody>
          </table>
        </div>
      </section>

      {/* 7. Theme vs Noise */}
      <section className="border-b border-gray-200 py-7">
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
