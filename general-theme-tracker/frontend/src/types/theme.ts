// Aligned with data/schema/theme.schema.yaml (schema_v1)
export type ThemeStatus = 'Emerging' | 'New' | 'Continuing' | 'Fading' | 'Dead'
export type Conviction = 'High' | 'Med' | 'Low'

export interface Performance {
  proxy_ticker: string
  proxy_price: number
  currency: string
  return_type: 'price' | 'total_return'
  ret_1w: number
  ret_1m: number
  ret_ytd: number
  benchmark_ticker: string
  benchmark_name: string
  benchmark_ret_1w: number
  benchmark_ret_1m: number
  benchmark_ret_ytd: number
  excess_1w: number
  excess_1m: number
  excess_ytd: number
  as_of_utc: string
  source: string
  benchmark_rationale: string
}

export interface SeriesPoint {
  date: string
  proxy: number
  benchmark: number
}

export interface Proxy {
  ticker: string
  name: string
  type: 'ETF' | 'Index' | 'Basket'
  region: string
  expense?: string
  liquidity_note: string
  why_represents: string
  tracking_gap: string
}

export interface ThemeEvent {
  event_time_utc: string
  title: string
  source: string
  url: string
  type: 'macro' | 'earnings' | 'policy' | 'geopolitics'
}

export interface Catalyst {
  event_name: string
  due_date: string
  why_matters: string
  if_bull: string
  if_bear: string
}

export interface ThemeVsNoise {
  persistence: boolean
  breadth: boolean
  volume_confirm: boolean
  falsifiable_catalyst: boolean
  repricing_logic: boolean
  score: number
}

export interface Theme {
  schema_v: number
  id: string
  week: string
  title: string
  status: ThemeStatus
  status_note: string
  conviction: Conviction
  horizon: string
  created_at: string
  updated_at: string
  data_quality: 'production' | 'sample'
  body_text: string
  explainer?: string
  performance: Performance
  series: SeriesPoint[]
  proxies: Proxy[]
  events: ThemeEvent[]
  depends_on: Catalyst[]
  theme_vs_noise: ThemeVsNoise
}

export interface ActiveResponse {
  week: string | null
  count: number
  themes: Theme[]
}

export interface Benchmark {
  ticker: string
  name: string
  value: number
  chg_1d: number
  chg_unit: '%' | 'bp'
}

export interface Snapshot {
  week: string
  as_of_utc: string
  regime: { stance: string; oneliner: string; keywords: string[] }
  benchmarks: Benchmark[]
  yesterday_diff: { theme_id: string; change: 'new' | 'continuing' | 'fading' | 'dead'; note: string }[]
}

export interface CommentarySource {
  firm: string
  title: string
  url: string
  key_takeaway: string
  related_themes: string[]
}

export interface Commentary {
  week: string
  sources: CommentarySource[]
}
