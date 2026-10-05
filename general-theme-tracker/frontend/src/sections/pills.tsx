import type { ThemeStatus } from '@/types/theme'

const STATUS_COLOR: Record<ThemeStatus, string> = {
  Emerging: '#7c3aed',
  New: '#e51503',
  Continuing: '#0a7d44',
  Fading: '#b45309',
  Dead: '#9ca3af',
}

// Bloomberg-style status tag: dot + uppercase small caps, no colored pills
export function StatusTag({ status }: { status: ThemeStatus }) {
  return (
    <span className="t-tag" style={{ color: STATUS_COLOR[status] }}>
      <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: STATUS_COLOR[status] }} />
      {status}
    </span>
  )
}

export function ConvictionTag({ conviction }: { conviction: string }) {
  return <span className="t-tag text-gray-500">{conviction} Conviction</span>
}

export function NoiseScore({ score }: { score: number }) {
  return (
    <span className="inline-flex items-center gap-1" title={`Theme vs Noise: ${score}/5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={`inline-block h-1.5 w-1.5 rounded-full ${i <= score ? 'bg-gray-900' : 'bg-gray-300'}`} />
      ))}
      <span className="t-time text-gray-500 ml-1">{score}/5</span>
    </span>
  )
}
