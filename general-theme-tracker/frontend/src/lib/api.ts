import type { ActiveResponse, Commentary, Snapshot, Theme } from '@/types/theme'

// 前端只读 API，绝不直接碰 data/ 原始 YAML（产品原则 #4）
async function get<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`${path} → ${res.status}`)
  return res.json() as Promise<T>
}

export const fetchActive = () => get<ActiveResponse>('/api/themes/active')
export const fetchTheme = (id: string) => get<Theme>(`/api/themes/${id}`)
export const fetchSnapshot = () => get<Snapshot>('/api/market/snapshot')
export const fetchCommentary = () => get<Commentary>('/api/commentary')

// 5-min rule：CJK 180 字/min，英文 200 wpm，取较大者
export function readingMinutes(text: string): number {
  const cjk = (text.match(/[一-鿿]/g) || []).length
  const words = (text.replace(/[一-鿿]/g, ' ').match(/\S+/g) || []).length
  return Math.max(1, Math.ceil(Math.max(cjk / 180, words / 200)))
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
