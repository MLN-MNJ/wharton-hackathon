import { useEffect, useState } from 'react'

const PROPERTIES = [
  { id: 'resort', name: 'Paradise Resort', icon: '🏝️', city: 'Broomfield, CO' },
  { id: 'hotel',  name: 'San Isidro Hotel', icon: '🏨', city: 'San Isidro, Costa Rica' },
]

const SENTIMENT_COLOR = { positive: '#52B788', negative: '#ef5350', neutral: '#60a5fa' }
const SENTIMENT_ICON  = { positive: '↑', negative: '↓', neutral: '→' }

function ScoreBar({ value, color = '#60a5fa' }) {
  return (
    <div style={{ flex: 1, height: 6, background: 'rgba(255,255,255,.08)', borderRadius: 999, overflow: 'hidden' }}>
      <div style={{ width: `${Math.min(value * 100, 100)}%`, height: '100%', background: color, borderRadius: 999, transition: 'width .6s ease' }} />
    </div>
  )
}

function StatCard({ label, value, sub, color = '#60a5fa' }) {
  return (
    <div style={{ background: 'rgba(255,255,255,.04)', border: '1px solid rgba(255,255,255,.08)', borderRadius: 16, padding: '18px 20px', flex: 1, minWidth: 120 }}>
      <div style={{ fontSize: 28, fontWeight: 800, color }}>{value}</div>
      <div style={{ fontSize: 13, fontWeight: 600, color: '#c8d0e0', marginTop: 2 }}>{label}</div>
      {sub && <div style={{ fontSize: 12, color: '#6b7a99', marginTop: 4 }}>{sub}</div>}
    </div>
  )
}

export default function Dashboard({ onClose, isDark }) {
  const [activeProperty, setActiveProperty] = useState('resort')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetch(`/api/dashboard?property_id=${activeProperty}`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [activeProperty, refreshKey])

  const bg    = isDark ? '#0a0e1a' : '#f7f7f8'
  const card  = isDark ? '#141824' : '#ffffff'
  const text  = isDark ? '#f0ede8' : '#1f2a44'
  const muted = isDark ? '#6b7a99' : '#64748b'
  const border = isDark ? 'rgba(255,255,255,.09)' : '#e2e8f0'

  const totalSentiment = data
    ? Object.values(data.sentiment_breakdown).reduce((a, b) => a + b, 0)
    : 0

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 200, background: 'rgba(0,0,0,.55)', display: 'flex', alignItems: 'flex-start', justifyContent: 'center', overflowY: 'auto', padding: '32px 16px' }}>
      <div style={{ width: '100%', maxWidth: 860, background: bg, borderRadius: 24, border: `1px solid ${border}`, overflow: 'hidden', boxShadow: '0 24px 80px rgba(0,0,0,.45)' }}>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '22px 28px', borderBottom: `1px solid ${border}` }}>
          <div>
            <div style={{ fontSize: 22, fontWeight: 800, color: text }}>Review Dashboard</div>
            <div style={{ fontSize: 13, color: muted, marginTop: 2 }}>Live data from guest submissions</div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="button"
              onClick={() => setRefreshKey(k => k + 1)}
              disabled={loading}
              style={{ height: 38, padding: '0 14px', borderRadius: 999, border: `1px solid ${border}`, background: 'transparent', color: loading ? muted : text, cursor: loading ? 'default' : 'pointer', fontSize: 13, fontWeight: 600 }}
            >
              {loading ? '…' : '↻ Refresh'}
            </button>
            <button
              type="button"
              onClick={onClose}
              style={{ width: 38, height: 38, borderRadius: '50%', border: `1px solid ${border}`, background: 'transparent', color: text, cursor: 'pointer', fontSize: 18 }}
            >✕</button>
          </div>
        </div>

        {/* Property tabs */}
        <div style={{ display: 'flex', gap: 8, padding: '16px 28px 0', borderBottom: `1px solid ${border}` }}>
          {PROPERTIES.map(p => (
            <button
              key={p.id}
              type="button"
              onClick={() => setActiveProperty(p.id)}
              style={{
                padding: '10px 20px',
                borderRadius: '10px 10px 0 0',
                border: 'none',
                borderBottom: activeProperty === p.id ? '2px solid #60a5fa' : '2px solid transparent',
                background: activeProperty === p.id ? (isDark ? 'rgba(96,165,250,.1)' : '#eff6ff') : 'transparent',
                color: activeProperty === p.id ? '#60a5fa' : muted,
                fontWeight: 700,
                fontSize: 14,
                cursor: 'pointer',
              }}
            >
              {p.icon} {p.name}
            </button>
          ))}
        </div>

        <div style={{ padding: '24px 28px 32px', display: 'flex', flexDirection: 'column', gap: 24 }}>

          {loading && <div style={{ textAlign: 'center', color: muted, padding: 40 }}>Loading dashboard data…</div>}
          {error && <div style={{ textAlign: 'center', color: '#ef5350', padding: 40 }}>Could not load data: {error}<br /><span style={{ fontSize: 12, color: muted }}>Make sure the API server is running on port 8507.</span></div>}

          {data && !loading && (
            <>
              {/* Stat cards row */}
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                <StatCard label="Total Submissions" value={data.total_submissions} color="#60a5fa" />
                <StatCard label="Areas Covered" value={data.gaps_covered.length} sub={data.gaps_covered.join(', ') || '—'} color="#52B788" />
                <StatCard label="Positive Signals" value={data.sentiment_breakdown.positive} color="#52B788" />
                <StatCard label="Negative Signals" value={data.sentiment_breakdown.negative} color="#ef5350" />
              </div>

              {/* Sentiment breakdown */}
              {totalSentiment > 0 && (
                <div style={{ background: isDark ? 'rgba(255,255,255,.03)' : card, border: `1px solid ${border}`, borderRadius: 16, padding: '18px 20px' }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: muted, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 14 }}>Sentiment Breakdown</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {Object.entries(data.sentiment_breakdown).map(([key, val]) => (
                      <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <div style={{ width: 72, fontSize: 12, fontWeight: 600, color: SENTIMENT_COLOR[key] }}>{SENTIMENT_ICON[key]} {key}</div>
                        <ScoreBar value={totalSentiment ? val / totalSentiment : 0} color={SENTIMENT_COLOR[key]} />
                        <div style={{ width: 24, fontSize: 12, color: muted, textAlign: 'right' }}>{val}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Gap scores */}
              {data.gap_scores.length > 0 && (
                <div style={{ background: isDark ? 'rgba(255,255,255,.03)' : card, border: `1px solid ${border}`, borderRadius: 16, padding: '18px 20px' }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: muted, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 14 }}>Current Gap Scores</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    {data.gap_scores.map(bucket => (
                      <div key={bucket.bucket}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                          <div style={{ fontSize: 14, fontWeight: 700, color: text }}>{bucket.bucket}</div>
                          <div style={{ fontSize: 12, color: muted }}>avg gap {(bucket.avg_gap * 100).toFixed(0)}%</div>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                          {bucket.sub_features.map(sf => (
                            <div key={sf.name} style={{ display: 'flex', flexDirection: 'column', gap: 4, padding: '8px 10px', background: 'rgba(255,255,255,.03)', borderRadius: 10 }}>
                              <div style={{ fontSize: 12, fontWeight: 600, color: '#c8d0e0' }}>{sf.name}</div>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                                {[
                                  { label: 'Gap', value: sf.gap_score, color: '#ef5350' },
                                  { label: 'Conflict', value: sf.ambiguity_score, color: '#f59e0b' },
                                  { label: 'Stale', value: sf.staleness_score, color: '#8b5cf6' },
                                ].map(({ label, value, color }) => (
                                  <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                    <div style={{ width: 44, fontSize: 10, color: muted }}>{label}</div>
                                    <ScoreBar value={value} color={color} />
                                    <div style={{ width: 30, fontSize: 10, color: muted, textAlign: 'right' }}>{(value * 100).toFixed(0)}%</div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recent submissions feed */}
              {data.recent_submissions.length > 0 && (
                <div style={{ background: isDark ? 'rgba(255,255,255,.03)' : card, border: `1px solid ${border}`, borderRadius: 16, padding: '18px 20px' }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: muted, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 14 }}>Recent Submissions</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {[...data.recent_submissions].reverse().map((sub, i) => (
                      <div key={i} style={{ border: `1px solid ${border}`, borderRadius: 12, padding: '12px 14px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                          <div style={{ fontSize: 13, fontWeight: 700, color: text }}>{sub.landmark}</div>
                          <div style={{ display: 'flex', gap: 6 }}>
                            {sub.user_engagement && (
                              <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 999, background: sub.user_engagement === 'high' ? 'rgba(82,183,136,.15)' : 'rgba(107,122,153,.15)', color: sub.user_engagement === 'high' ? '#52B788' : muted, fontWeight: 600 }}>
                                {sub.user_engagement} engagement
                              </span>
                            )}
                            {sub.data_quality && (
                              <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 999, background: sub.data_quality === 'reliable' ? 'rgba(96,165,250,.15)' : 'rgba(239,83,80,.15)', color: sub.data_quality === 'reliable' ? '#60a5fa' : '#ef5350', fontWeight: 600 }}>
                                {sub.data_quality}
                              </span>
                            )}
                          </div>
                        </div>
                        {sub.verdicts.length > 0 && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            {sub.verdicts.map((v, j) => {
                              const sc = SENTIMENT_COLOR[v.sentiment] || '#60a5fa'
                              return (
                                <div key={j} style={{ fontSize: 12, color: '#8a9ab5', borderLeft: `2px solid ${sc}`, paddingLeft: 8 }}>
                                  <span style={{ fontWeight: 600, color: '#c8d0e0' }}>{v.sub_feature}: </span>{v.discovery}
                                </div>
                              )
                            })}
                          </div>
                        )}
                        {sub.freehand_insights && (
                          <div style={{ fontSize: 12, color: muted, marginTop: 6, fontStyle: 'italic' }}>"{sub.freehand_insights}"</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {data.total_submissions === 0 && (
                <div style={{ textAlign: 'center', color: muted, padding: '32px 0' }}>
                  No submissions yet for this property.<br />
                  <span style={{ fontSize: 13 }}>Complete a review in the app to see data here.</span>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
