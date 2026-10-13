import type { ActiveResponse, Commentary, Snapshot, Theme } from '@/types/theme'

// The frontend only reads the API — it never touches raw data/ YAML (product principle #4)
async function get<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`${path} → ${res.status}`)
  return res.json() as Promise<T>
}

export const fetchActive = () => get<ActiveResponse>('/api/themes/active')
export const fetchTheme = (id: string) => get<Theme>(`/api/themes/${id}`)
export const fetchSnapshot = () => get<Snapshot>('/api/market/snapshot')
export const fetchCommentary = () => get<Commentary>('/api/commentary')

// 2-min core / up to 5min folded: legacy caliber 500 words = 5min (100wpm), so 200 words = 2min
export function readingMinutes(text: string): number {
  const words = (text.match(/\S+/g) || []).length
  return Math.max(1, Math.ceil(words / 100))
}

export function torontoToday(): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Toronto',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date())
}

export function isStale(asOfUtc: string, todayToronto: string): boolean {
  const d = new Date(asOfUtc)
  if (isNaN(d.getTime())) return true
  const asOfToronto = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Toronto',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(d)
  return asOfToronto !== todayToronto
}

export function fmtPct(n: number, unit = '%'): string {
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(1)}${unit}`
}

export function fmtChg(n: number, unit: '%' | 'bp'): string {
  const sign = n > 0 ? '+' : ''
  return unit === 'bp' ? `${sign}${n}bp` : `${sign}${n.toFixed(2)}%`
}

export function fmtUtc(iso: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return d.toISOString().replace('T', ' ').slice(0, 16) + 'Z'
}
