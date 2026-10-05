import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { fetchCommentary } from '@/lib/api'
import type { Commentary } from '@/types/theme'

// Archive — Weekly Commentary 来源库，报刊附录式
export default function Archive() {
  const [data, setData] = useState<Commentary | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    fetchCommentary()
      .then(setData)
      .catch((e) => setErr(e.message))
  }, [])

  if (err) return <div className="w-full p-8 t-body num-down sm:px-6 lg:px-10">加载失败：{err}</div>
  if (!data) return <div className="w-full p-8 t-explainer sm:px-6 lg:px-10">加载中…</div>

  return (
    <div className="w-full px-4 sm:px-6 lg:px-10">
      <section className="border-b border-gray-200 py-7">
        <p className="t-kicker">Archive · Weekly Commentary Digests</p>
        <h1 className="t-headline mt-3">来源库 · {data.week}</h1>
        <p className="t-explainer mt-2">每周必扫清单的原始出处。提炼分歧点，不搬运摘要。</p>
      </section>
      <div>
        {data.sources.map((s, i) => (
          <div key={i} className="border-b border-gray-200 py-5">
            <div className="flex flex-wrap items-baseline gap-x-3">
              <span className="t-kicker text-gray-900">{s.firm}</span>
              <a href={s.url} target="_blank" rel="noreferrer" className="t-body font-bold link-ed">
                {s.title} ↗
              </a>
            </div>
            <p className="t-body mt-1.5 max-w-3xl text-gray-700">{s.key_takeaway}</p>
            <p className="t-explainer mt-1.5">
              关联：
              {s.related_themes.map((t, j) => (
                <span key={t}>
                  {j > 0 && ' · '}
                  <Link to={`/theme/${t}`} className="link-ed">
                    {t}
                  </Link>
                </span>
              ))}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
