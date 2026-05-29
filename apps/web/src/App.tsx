import { useState, useCallback } from 'react'

interface Author {
  nickname: string
  sec_uid: string | null
}

interface Media {
  type: string
  downloadable: boolean
  url: string | null
  mime: string | null
  reason_if_unavailable: string | null
}

interface Comment {
  cid: string
  text: string
  like_count: number
  reply_count: number | null
  create_time: string | null
}

interface ErrorInfo {
  code: string
  message: string
  detail: string | null
}

interface ResolveResult {
  ok: boolean
  platform: string
  input_url: string
  resolved_url: string | null
  aweme_id: string | null
  title: string | null
  author: Author | null
  cover_url: string | null
  media: Media | null
  comments: Comment[]
  warnings: string[]
  error: ErrorInfo | null
}

const EXAMPLE_URL = 'https://v.douyin.com/bk9fkF-STVc/'

function App() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ResolveResult | null>(null)
  const [copied, setCopied] = useState(false)

  const handleResolve = useCallback(async () => {
    if (!url.trim()) return
    setLoading(true)
    setResult(null)
    try {
      const resp = await fetch('/api/v1/douyin/resolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim(), include_comments: true, comment_limit: 50 }),
      })
      const data: ResolveResult = await resp.json()
      setResult(data)
    } catch (e) {
      setResult({
        ok: false,
        platform: 'douyin',
        input_url: url,
        resolved_url: null,
        aweme_id: null,
        title: null,
        author: null,
        cover_url: null,
        media: null,
        comments: [],
        warnings: [],
        error: { code: 'NETWORK_ERROR', message: '网络请求失败', detail: String(e) },
      })
    } finally {
      setLoading(false)
    }
  }, [url])

  const handleCopy = useCallback(() => {
    if (!result) return
    navigator.clipboard.writeText(JSON.stringify(result, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [result])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !loading) handleResolve()
    },
    [loading, handleResolve]
  )

  const handleClear = useCallback(() => {
    setUrl('')
    setResult(null)
  }, [])

  const handleExample = useCallback(() => {
    setUrl(EXAMPLE_URL)
  }, [])

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-indigo-600 to-indigo-500">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 py-6">
          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">Douyin Link Resolver</h1>
          <p className="mt-1 text-sm text-indigo-200">抖音公开分享链接解析工具</p>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
        {/* Input */}
        <div className="bg-white rounded-xl shadow-md border border-gray-100 p-4 sm:p-6">
          <label htmlFor="url-input" className="block text-sm font-medium text-gray-700 mb-2">
            粘贴抖音分享链接或分享文本
          </label>
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <input
                id="url-input"
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="https://v.douyin.com/xxxx/ 或 复制打开抖音..."
                className="w-full rounded-lg border border-gray-300 px-4 pr-10 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:border-transparent transition-shadow"
                disabled={loading}
              />
              {url.trim() && !loading && (
                <button
                  type="button"
                  onClick={handleClear}
                  aria-label="清除链接"
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-full text-gray-400 hover:text-gray-600 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition-colors"
                >
                  <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
                  </svg>
                </button>
              )}
            </div>
            <button
              onClick={handleResolve}
              disabled={loading || !url.trim()}
              className="px-6 py-3 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 hover:shadow-lg hover:scale-[1.02] active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100 disabled:hover:shadow-none transition-all"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  解析中...
                </span>
              ) : '解析'}
            </button>
          </div>
        </div>

        {/* Empty State */}
        {!loading && !result && (
          <div className="mt-8 text-center animate-fade-in">
            <div className="mx-auto w-16 h-16 bg-indigo-50 rounded-2xl flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-indigo-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z" />
              </svg>
            </div>
            <p className="text-sm text-gray-500 mb-3 leading-relaxed">
              粘贴抖音分享链接，获取视频信息和热门评论
            </p>
            <button
              type="button"
              onClick={handleExample}
              className="inline-flex items-center gap-1.5 text-sm text-indigo-600 hover:text-indigo-700 font-medium transition-colors"
            >
              <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H4.598a.75.75 0 00-.75.75v3.634a.75.75 0 001.5 0v-2.033l.312.311a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm-11.23-3.047a.75.75 0 01.564-.89 7 7 0 0111.712 3.138.75.75 0 01-1.449.39 5.5 5.5 0 00-9.201-2.466l-.312.311V6.33a.75.75 0 00-1.5 0v3.634a.75.75 0 00.75.75h3.634a.75.75 0 000-1.5H6.645l.312-.311a.75.75 0 00-.327-1.213z" clipRule="evenodd" />
              </svg>
              试试这个示例链接
            </button>
          </div>
        )}

        {/* Loading Skeleton */}
        {loading && (
          <div className="mt-6 space-y-4 animate-fade-in">
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <div className="flex gap-5">
                <div className="w-28 h-40 sm:w-36 sm:h-52 bg-gray-200 rounded-lg animate-pulse flex-shrink-0" />
                <div className="flex-1 space-y-3">
                  <div className="h-5 bg-gray-200 rounded animate-pulse w-3/4" />
                  <div className="h-4 bg-gray-200 rounded animate-pulse w-1/2" />
                  <div className="h-4 bg-gray-200 rounded animate-pulse w-1/3" />
                  <div className="mt-4 h-9 bg-gray-200 rounded-lg animate-pulse w-28" />
                </div>
              </div>
            </div>
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <div className="space-y-3">
                <div className="h-4 bg-gray-200 rounded animate-pulse w-1/4" />
                <div className="h-3 bg-gray-200 rounded animate-pulse w-full" />
                <div className="h-3 bg-gray-200 rounded animate-pulse w-5/6" />
                <div className="h-3 bg-gray-200 rounded animate-pulse w-2/3" />
              </div>
            </div>
          </div>
        )}

        {/* Result */}
        {result && (
          <div className="mt-6 space-y-4 animate-fade-in">
            {/* Error */}
            {!result.ok && result.error && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 shadow-sm">
                <div className="flex items-start gap-3">
                  <svg className="h-5 w-5 text-red-400 mt-0.5 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <p className="text-sm font-medium text-red-800">{result.error.message}</p>
                    {result.error.detail && (
                      <p className="mt-1 text-xs text-red-600">{result.error.detail}</p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Success */}
            {result.ok && (
              <>
                {/* Video Info Card */}
                <div className="bg-white rounded-xl shadow-md border border-gray-100 overflow-hidden">
                  <div className="p-4 sm:p-6">
                    <div className="flex flex-col sm:flex-row gap-4 sm:gap-6">
                      {/* Cover */}
                      {result.cover_url && (
                        <div className="flex-shrink-0">
                          <img
                            src={result.cover_url}
                            alt={result.title || '封面'}
                            className="w-full h-48 sm:w-36 sm:h-52 object-cover rounded-lg"
                          />
                        </div>
                      )}

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <h2 className="text-base sm:text-lg font-semibold text-gray-900 leading-relaxed line-clamp-2">
                          {result.title || '无标题'}
                        </h2>

                        <div className="mt-3 space-y-2 text-sm text-gray-600">
                          <div className="flex items-center gap-2">
                            <span className="text-gray-400 w-12 flex-shrink-0">作者</span>
                            <span className="font-medium text-gray-900">
                              {result.author?.nickname || '未知'}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-gray-400 w-12 flex-shrink-0">ID</span>
                            <span className="font-mono text-xs text-gray-600 bg-gray-50 px-2 py-0.5 rounded">{result.aweme_id}</span>
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="mt-4 flex flex-wrap items-center gap-2">
                          {result.media && (
                            result.media.downloadable ? (
                              <a
                                href={result.media.url || '#'}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 hover:shadow-lg hover:scale-[1.02] active:scale-[0.98] transition-all"
                              >
                                <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                  <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
                                </svg>
                                下载视频
                              </a>
                            ) : (
                              <div className="flex items-center gap-2 text-sm text-gray-500">
                                <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                  <path fillRule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 018.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clipRule="evenodd" />
                                </svg>
                                {result.media.reason_if_unavailable || '不可下载'}
                              </div>
                            )
                          )}
                          <button
                            onClick={handleCopy}
                            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs text-gray-500 hover:text-indigo-600 border border-gray-200 hover:border-indigo-200 rounded-lg hover:bg-indigo-50 transition-all"
                          >
                            <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                              <path d="M8 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" />
                              <path d="M6 3a2 2 0 00-2 2v11a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2 3 3 0 01-3 3H9a3 3 0 01-3-3z" />
                            </svg>
                            {copied ? '已复制!' : 'JSON'}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Warnings */}
                {result.warnings.length > 0 && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 shadow-sm">
                    {result.warnings.map((w, i) => (
                      <p key={i} className="text-sm text-yellow-800 leading-relaxed">{w}</p>
                    ))}
                  </div>
                )}

                {/* Comments */}
                {result.comments.length > 0 && (
                  <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                    <div className="px-4 sm:px-6 py-4 border-b border-gray-100">
                      <h3 className="text-sm font-semibold text-gray-900">
                        热门评论 ({result.comments.length})
                      </h3>
                    </div>
                    <div className="divide-y divide-gray-100">
                      {result.comments.map((c, i) => (
                        <div key={c.cid} className="px-4 sm:px-6 py-4">
                          <div className="flex items-start gap-3">
                            <span className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${i < 3 ? 'bg-indigo-50 text-indigo-600' : 'bg-gray-100 text-gray-500'}`}>
                              {i + 1}
                            </span>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-xs text-indigo-500 font-medium">
                                  {c.like_count > 0 && `${c.like_count > 10000 ? `${(c.like_count / 10000).toFixed(1)}w` : c.like_count} 赞`}
                                </span>
                                {c.reply_count != null && c.reply_count > 0 && (
                                  <span className="text-xs text-gray-400">{c.reply_count} 回复</span>
                                )}
                              </div>
                              <p className="text-sm text-gray-700 leading-relaxed">{c.text}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </main>

      {/* Compliance Notice */}
      <footer className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
        <div className="bg-white border border-gray-100 rounded-xl p-4 shadow-sm">
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">使用声明</h4>
          <ul className="space-y-1 text-xs text-gray-400 leading-relaxed">
            <li>请确认你拥有下载和使用该内容的权利</li>
            <li>不支持私密、删除、受限内容</li>
            <li>不保证所有链接都可下载</li>
            <li>本工具仅用于授权内容解析与测试</li>
          </ul>
        </div>
      </footer>
    </div>
  )
}

export default App
