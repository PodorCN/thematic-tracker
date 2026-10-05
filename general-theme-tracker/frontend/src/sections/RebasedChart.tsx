import type { SeriesPoint } from '@/types/theme'

// Proxy vs Benchmark 归一化走势（Rebased to 100），纯 SVG 无依赖
export default function RebasedChart({
  series,
  proxyLabel,
  benchmarkLabel,
}: {
  series: SeriesPoint[]
  proxyLabel: string
  benchmarkLabel: string
}) {
  const W = 640
  const H = 220
  const PAD = { l: 40, r: 56, t: 16, b: 28 }

  const all = series.flatMap((p) => [p.proxy, p.benchmark])
  const min = Math.min(...all)
  const max = Math.max(...all)
  const span = max - min || 1
  const lo = min - span * 0.08
  const hi = max + span * 0.08

  const x = (i: number) => PAD.l + (i / (series.length - 1)) * (W - PAD.l - PAD.r)
  const y = (v: number) => PAD.t + (1 - (v - lo) / (hi - lo)) * (H - PAD.t - PAD.b)

  const line = (key: 'proxy' | 'benchmark') =>
    series.map((p, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(p[key]).toFixed(1)}`).join(' ')

  const ticks = [lo + (hi - lo) * 0.25, lo + (hi - lo) * 0.5, lo + (hi - lo) * 0.75]
  const last = series[series.length - 1]

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="rebased performance chart">
        {[100, ...ticks].map((v) =>
          v >= lo && v <= hi ? (
            <g key={v}>
              <line x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)} stroke={v === 100 ? '#9CA3AF' : '#E5E7EB'} strokeDasharray={v === 100 ? '4 3' : undefined} />
              <text x={PAD.l - 6} y={y(v) + 3} textAnchor="end" fontSize="10" fill="#6B7280">
                {v.toFixed(0)}
              </text>
            </g>
          ) : null,
        )}
        <path d={line('benchmark')} fill="none" stroke="#B4BCC8" strokeWidth="1.5" />
        <path d={line('proxy')} fill="none" stroke="#111827" strokeWidth="2.5" />
        <circle cx={x(series.length - 1)} cy={y(last.proxy)} r="3.5" fill="#111827" />
        <circle cx={x(series.length - 1)} cy={y(last.benchmark)} r="2.5" fill="#B4BCC8" />
        <text x={W - PAD.r + 6} y={y(last.proxy) + 3} fontSize="11" fontWeight="700" fill="#111827">
          {last.proxy.toFixed(1)}
        </text>
        <text x={W - PAD.r + 6} y={y(last.benchmark) + 3} fontSize="11" fill="#6B7280">
          {last.benchmark.toFixed(1)}
        </text>
        <text x={x(0)} y={H - 8} textAnchor="middle" fontSize="10" fill="#6B7280">
          {String(series[0].date).slice(0, 10)}
        </text>
        <text x={x(series.length - 1)} y={H - 8} textAnchor="middle" fontSize="10" fill="#6B7280">
          {String(last.date).slice(0, 10)}
        </text>
      </svg>
      <div className="t-explainer mt-1 flex gap-4">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-4 bg-gray-900" /> {proxyLabel}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-4 bg-gray-400" /> {benchmarkLabel}
        </span>
        <span>Rebased to 100</span>
      </div>
    </div>
  )
}
