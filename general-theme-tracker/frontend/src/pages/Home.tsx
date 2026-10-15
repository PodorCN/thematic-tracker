import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { fetchActive, fetchSnapshot, fmtChg, fmtPct, fmtUtc, isStale, torontoToday } from '@/lib/api'
import { ConvictionTag, NoiseScore, StatusTag } from '@/sections/pills'
import type { ActiveResponse, Catalyst, ChainStep, Performance, Snapshot, Theme, ThemeVsNoise } from '@/types/theme'

const DIFF_COLOR: Record<string, string> = {
  new: '#e51503',
  continuing: '#0a7d44',
  fading: '#b45309',
  dead: '#9ca3af',
}

const STATUS_RANK: Record<string, number> = { New: 0, Emerging: 1, Continuing: 2, Fading: 3, Dead: 4 }

// Formation chain — dated, numbered boxes joined by arrows; each step is a plain-English headline plus one
// explanatory sentence. The last step is the current state ("Now").
function Chain({ steps }: { steps: ChainStep[] }) {
  if (!steps || !steps.length) return null
  return (
    <ol className="flex flex-col">
      {steps.map((s, i) => {
        const last = i === steps.length - 1
        return (
          <li key={i} className="flex min-w-0 flex-col">
            <div className={`border px-4 py-3 lg:grid lg:grid-cols-[150px_minmax(0,1fr)] lg:gap-x-6 ${last ? 'border-gray-900 bg-gray-900' : 'border-gray-300'}`}>
              <p className={`t-kicker-plain flex items-baseline justify-between gap-2 lg:row-span-2 lg:flex-col lg:items-start lg:justify-start ${last ? '!text-gray-300' : ''}`}>
                <span>{last ? 'Now' : String(i + 1).padStart(2, '0')}</span>
                {s.when && <span className={`whitespace-nowrap ${last ? 'text-white' : 'text-gray-900'}`}>{s.when}</span>}
              </p>
              <p className={`t-body mt-1 font-bold ${last ? 'text-white' : 'text-gray-900'}`}>{s.label}</p>
              {s.detail && <p className={`t-body mt-1 lg:col-start-2 ${last ? 'text-gray-300' : 'text-gray-600'}`}>{s.detail}</p>}
            </div>
            {!last && (
              <span className="flex h-[22px] items-center justify-center text-gray-400" aria-hidden="true">
                ↓
              </span>
            )}
          </li>
        )
      })}
    </ol>
  )
}

// Mini proxy-vs-benchmark sparkline from the rebased series (no axes, legend below)
function MiniChart({
  series,
  proxyLabel,
  benchmarkLabel,
}: {
  series: { date: string; proxy: number; benchmark: number }[]
  proxyLabel: string
  benchmarkLabel: string
}) {
  if (!series || series.length < 2) return null
  const W = 200
  const H = 56
  const all = series.flatMap((pt) => [pt.proxy, pt.benchmark])
  const min = Math.min(...all)
  const max = Math.max(...all)
  const span = max - min || 1
  const x = (i: number) => (i / (series.length - 1)) * W
  const y = (v: number) => 4 + (1 - (v - min) / span) * (H - 8)
  const line = (key: 'proxy' | 'benchmark') =>
    series.map((pt, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(pt[key]).toFixed(1)}`).join(' ')
  return (
    <div className="mt-3">
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="block h-[180px] w-full overflow-visible" role="img" aria-label={`${proxyLabel} versus ${benchmarkLabel} sparkline`}>
        <path d={line('benchmark')} fill="none" stroke="#B4BCC8" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
        <path d={line('proxy')} fill="none" stroke="#111827" strokeWidth="2" vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="t-explainer mt-1 flex gap-3">
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-0.5 w-3 bg-gray-900" /> {proxyLabel}
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-0.5 w-3 bg-gray-400" /> {benchmarkLabel}
        </span>
      </div>
    </div>
  )
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

// "2026-10-07T14:30:00Z" -> "Oct 7" (string slice, no timezone drift)
function fmtDay(iso: string): string {
  const [, m, d] = String(iso).slice(0, 10).split('-')
  return m && d ? `${MONTHS[Number(m) - 1]} ${Number(d)}` : String(iso)
}

// Next checkpoints on/after the data date, soonest first (falls back to all if none are upcoming)
function nextCatalysts(deps: Catalyst[], asOfUtc: string, n = 2): Catalyst[] {
  const ref = String(asOfUtc).slice(0, 10)
  const sorted = [...deps].sort((a, b) => String(a.due_date).localeCompare(String(b.due_date)))
  const upcoming = sorted.filter((d) => String(d.due_date).slice(0, 10) >= ref)
  return (upcoming.length ? upcoming : sorted).slice(0, n)
}

const NOISE_CHECKS: [keyof Omit<ThemeVsNoise, 'score'>, string][] = [
  ['persistence', 'persistence'],
  ['breadth', 'breadth'],
  ['volume_confirm', 'price-volume'],
  ['falsifiable_catalyst', 'falsifiable catalyst'],
  ['repricing_logic', 're-pricing logic'],
]

const sign = (n: number) => (n >= 0 ? 'num-up' : 'num-down')

// Scoreboard: proxy / benchmark / excess across 1W, 1M, YTD
function PerfTable({ p }: { p: Performance }) {
  const cell = 't-time py-1 text-right'
  return (
    <table className="w-full border-collapse">
      <thead>
        <tr className="border-b border-gray-200">
          <th />
          {['1W', '1M', 'YTD'].map((h) => (
            <th key={h} className="t-kicker-plain pb-1.5 text-right">{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr>
          <td className="t-time py-1 font-bold text-gray-900">{p.proxy_ticker}</td>
          <td className={`${cell} ${sign(p.ret_1w)}`}>{fmtPct(p.ret_1w)}</td>
          <td className={`${cell} ${sign(p.ret_1m)}`}>{fmtPct(p.ret_1m)}</td>
          <td className={`${cell} ${sign(p.ret_ytd)}`}>{fmtPct(p.ret_ytd)}</td>
        </tr>
        <tr>
          <td className="t-time py-1 text-gray-500">{p.benchmark_name}</td>
          <td className={`${cell} text-gray-500`}>{fmtPct(p.benchmark_ret_1w)}</td>
          <td className={`${cell} text-gray-500`}>{fmtPct(p.benchmark_ret_1m)}</td>
          <td className={`${cell} text-gray-500`}>{fmtPct(p.benchmark_ret_ytd)}</td>
        </tr>
        <tr className="border-t border-gray-900">
          <td className="t-time py-1.5 font-bold text-gray-900">Excess</td>
          <td className={`${cell} font-bold ${sign(p.excess_1w)}`}>{fmtPct(p.excess_1w, 'pp')}</td>
          <td className={`${cell} font-bold ${sign(p.excess_1m)}`}>{fmtPct(p.excess_1m, 'pp')}</td>
          <td className={`${cell} font-bold ${sign(p.excess_ytd)}`}>{fmtPct(p.excess_ytd, 'pp')}</td>
        </tr>
      </tbody>
    </table>
  )
}

// One-minute card — the same four blocks for every theme:
// what it is (header) -> why it formed (chain) -> is it working (scoreboard) -> what decides it next (watch table)
function ThemeCard({ t, n, asOfUtc }: { t: Theme; n: number; asOfUtc: string }) {
  const p = t.performance
  const watch = nextCatalysts(t.depends_on, asOfUtc)
  const more = t.depends_on.length - watch.length
  const failed = NOISE_CHECKS.filter(([k]) => !t.theme_vs_noise[k]).map(([, label]) => label)
  const watchCols = 'sm:grid-cols-[56px_1fr_1.35fr_1.35fr]'
  return (
    <article id={t.id} className="scroll-mt-4 border-b border-gray-200 py-8">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <span className="t-time font-bold text-gray-400">{String(n).padStart(2, '0')}</span>
        <StatusTag status={t.status} />
        <ConvictionTag conviction={t.conviction} />
        <span className="t-tag text-gray-500">{t.horizon}</span>
        <span className="t-tag text-gray-500">Since {fmtDay(t.created_at)}</span>
        <NoiseScore score={t.theme_vs_noise.score} />
        {failed.length > 0 && <span className="t-explainer">fails: {failed.join(', ')}</span>}
      </div>
      <Link to={`/theme/${t.id}`} className="group mt-2 block">
        <h2 className="t-headline decoration-1 underline-offset-4 group-hover:underline">{t.title}</h2>
      </Link>
      <p className="t-body mt-1.5 max-w-4xl text-gray-700">{t.status_note}</p>

      <p className="t-kicker mb-2 mt-5">How it formed</p>
      <Chain steps={t.chain} />

      <div className="mt-7 grid grid-cols-1 gap-y-7">
        <div>
          <p className="t-kicker mb-2">Is it working · {p.proxy_ticker} vs {p.benchmark_name}</p>
          <PerfTable p={p} />
          <MiniChart series={t.series} proxyLabel={p.proxy_ticker} benchmarkLabel={p.benchmark_name} />
        </div>
        <div>
          <p className="t-kicker mb-2">What decides it next</p>
          <div className={`hidden gap-x-4 border-b border-gray-200 pb-1.5 sm:grid ${watchCols}`}>
            <span className="t-kicker-plain">Date</span>
            <span className="t-kicker-plain">Checkpoint</span>
            <span className="t-kicker-plain">Holds if</span>
            <span className="t-kicker-plain">Breaks if</span>
          </div>
          {watch.map((d) => (
            <div key={d.event_name} className={`grid grid-cols-1 gap-x-4 gap-y-1 border-b border-gray-100 py-2.5 ${watchCols}`}>
              <span className="t-time font-bold text-gray-900">{fmtDay(d.due_date)}</span>
              <span className="text-[13px] font-semibold leading-snug text-gray-900">{d.event_name}</span>
              <span className="t-explainer !text-gray-700">
                <span className="num-up font-bold">▲ </span>
                {d.if_bull}
              </span>
              <span className="t-explainer !text-gray-700">
                <span className="num-down font-bold">▼ </span>
                {d.if_bear}
              </span>
            </div>
          ))}
          <div className="mt-3 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
            <span className="t-explainer">
              Track with{' '}
              {t.proxies.map((px, i) => (
                <span key={px.ticker}>
                  {i > 0 && ' · '}
                  <span className="t-time font-bold text-gray-900">{px.ticker}</span> {px.type}
                </span>
              ))}
            </span>
            <Link to={`/theme/${t.id}`} className="link-ed t-explainer !text-gray-900">
              Full thesis, {t.events.length} sourced events{more > 0 ? `, ${more} more checkpoint${more > 1 ? 's' : ''}` : ''} →
            </Link>
          </div>
        </div>
      </div>
    </article>
  )
}

function ChangeTag({ change }: { change: string }) {
  return (
    <span className="t-tag whitespace-nowrap" style={{ color: DIFF_COLOR[change] }}>
      <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: DIFF_COLOR[change] }} />
      {change}
    </span>
  )
}

// Theme board — every theme in one row: yesterday -> today change, excess, next checkpoint
function Board({ themes, snap }: { themes: Theme[]; snap: Snapshot }) {
  const diffOf = (id: string) => snap.yesterday_diff.find((d) => d.theme_id === id)
  const gone = snap.yesterday_diff.filter((d) => !themes.some((t) => t.id === d.theme_id))
  const num = 't-time px-2 py-2 text-right font-semibold'
  return (
    <section className="border-b border-gray-200 py-7">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <p className="t-kicker">Theme Board · Yesterday → Today</p>
        <span className="t-explainer">1W / 1M / YTD = excess vs benchmark, pp</span>
      </div>
      {/* Phones: one stacked block per theme (no sideways scrolling) */}
      <div className="border-t border-gray-900 sm:hidden">
        {themes.map((t) => {
          const change = diffOf(t.id)?.change
          const next = nextCatalysts(t.depends_on, snap.as_of_utc, 1)[0]
          const p = t.performance
          return (
            <a key={t.id} href={`#${t.id}`} className="block border-b border-gray-200 py-3">
              <div className="flex items-center justify-between gap-3">
                {change ? <ChangeTag change={change} /> : <StatusTag status={t.status} />}
                <NoiseScore score={t.theme_vs_noise.score} />
              </div>
              <p className="mt-1 text-[15px] font-bold leading-snug text-gray-900">{t.title}</p>
              <div className="t-time mt-1.5 flex flex-wrap items-baseline gap-x-4 gap-y-0.5">
                <span className="font-bold text-gray-900">{p.proxy_ticker}</span>
                {([['1W', p.excess_1w], ['1M', p.excess_1m], ['YTD', p.excess_ytd]] as [string, number][]).map(([k, v]) => (
                  <span key={k}>
                    <span className="text-gray-500">{k} </span>
                    <span className={`font-semibold ${sign(v)}`}>{fmtPct(v, '')}</span>
                  </span>
                ))}
              </div>
              {next && (
                <p className="t-explainer mt-1">
                  Next: <span className="t-time font-bold text-gray-900">{fmtDay(next.due_date)}</span> {next.event_name}
                </p>
              )}
            </a>
          )
        })}
        {gone.map((d) => (
          <div key={d.theme_id} className="border-b border-gray-200 py-3">
            <ChangeTag change={d.change} />
            <p className="t-explainer mt-1">
              <span className="font-bold text-gray-500">{d.theme_id}</span> — {d.note}
            </p>
          </div>
        ))}
      </div>
      <div className="hidden overflow-x-auto sm:block">
        <table className="w-full min-w-[600px] border-collapse">
          <thead>
            <tr className="border-b border-gray-900 text-left">
              <th className="t-kicker-plain pb-1.5 pr-2">Today</th>
              <th className="t-kicker-plain pb-1.5 pr-2">Theme</th>
              <th className="t-kicker-plain px-2 pb-1.5">Proxy</th>
              <th className="t-kicker-plain px-2 pb-1.5 text-right">1W</th>
              <th className="t-kicker-plain px-2 pb-1.5 text-right">1M</th>
              <th className="t-kicker-plain px-2 pb-1.5 text-right">YTD</th>
              <th className="t-kicker-plain px-2 pb-1.5">Next checkpoint</th>
              <th className="t-kicker-plain pb-1.5 pl-2">Theme vs noise</th>
            </tr>
          </thead>
          <tbody>
            {themes.map((t) => {
              const change = diffOf(t.id)?.change
              const next = nextCatalysts(t.depends_on, snap.as_of_utc, 1)[0]
              const p = t.performance
              return (
                <tr key={t.id} className="border-b border-gray-200">
                  <td className="py-2 pr-2">
                    {change ? <ChangeTag change={change} /> : <StatusTag status={t.status} />}
                  </td>
                  <td className="py-2 pr-2">
                    <a href={`#${t.id}`} className="text-[13px] font-bold text-gray-900 hover:underline">{t.title}</a>
                  </td>
                  <td className="t-time px-2 py-2 font-bold text-gray-900">{p.proxy_ticker}</td>
                  <td className={`${num} ${sign(p.excess_1w)}`}>{fmtPct(p.excess_1w, '')}</td>
                  <td className={`${num} ${sign(p.excess_1m)}`}>{fmtPct(p.excess_1m, '')}</td>
                  <td className={`${num} ${sign(p.excess_ytd)}`}>{fmtPct(p.excess_ytd, '')}</td>
                  <td className="t-explainer px-2 py-2">
                    {next && (
                      <>
                        <span className="t-time font-bold text-gray-900">{fmtDay(next.due_date)}</span> {next.event_name}
                      </>
                    )}
                  </td>
                  <td className="py-2 pl-2"><NoiseScore score={t.theme_vs_noise.score} /></td>
                </tr>
              )
            })}
            {gone.map((d) => (
              <tr key={d.theme_id} className="border-b border-gray-200">
                <td className="py-2 pr-2">
                  <ChangeTag change={d.change} />
                </td>
                <td className="t-explainer py-2" colSpan={7}>
                  <span className="font-bold text-gray-500">{d.theme_id}</span> — {d.note}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

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
        <p className="t-body num-down">API connection failed: {err}. Start it with npm run dev (backend :8787).</p>
      </div>
    )
  if (!active || !snap) return <div className="w-full p-8 t-explainer sm:px-6 lg:px-10">Loading…</div>

  const themes = [...active.themes].sort((a, b) => (STATUS_RANK[a.status] ?? 9) - (STATUS_RANK[b.status] ?? 9))

  return (
    <div className="w-full px-4 sm:px-6 lg:px-10">
      {/* Date banner — very top: is the page updated today? */}
      {(() => {
        const today = torontoToday()
        const stale = isStale(snap.as_of_utc, today)
        return (
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b-2 border-black py-2">
            <span className="t-kicker">Week {snap.week}</span>
            <span className="t-time text-gray-700">Data as of {fmtUtc(snap.as_of_utc)}</span>
            <span className="t-time text-gray-500">Today (Toronto) {today}</span>
            <span
              className="t-tag ml-auto"
              style={{ color: stale ? '#b45309' : '#0a7d44' }}
            >
              <span
                className="inline-block h-1.5 w-1.5 rounded-full"
                style={{ background: stale ? '#b45309' : '#0a7d44' }}
              />
              {stale ? 'Stale — not updated today' : 'Updated today'}
            </span>
          </div>
        )
      })()}
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

      {/* Front-page lead: Market Regime */}
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

      <Board themes={themes} snap={snap} />

      {/* One-minute cards — identical blocks for every theme */}
      <section>
        {themes.map((t, i) => (
          <ThemeCard key={t.id} t={t} n={i + 1} asOfUtc={snap.as_of_utc} />
        ))}
      </section>
    </div>
  )
}
