import { useEffect, useMemo, useState } from 'react'
import TextResponseBox from './TextResponseBox'
import { roundTo50 } from '../App'

function inferTopic(text) {
  const v = text.toLowerCase()
  if (/(noise|loud|ac|air.?con|hvac)/.test(v)) return 'Room noise'
  if (/(clean|dirty|smell|stain)/.test(v)) return 'Cleanliness'
  if (/(staff|desk|service|check.?in)/.test(v)) return 'Staff service'
  if (/(room|bed|mattress|bathroom|shower)/.test(v)) return 'Room condition'
  if (/(safe|security|lock)/.test(v)) return 'Safety'
  if (/(food|breakfast|restaurant|dining)/.test(v)) return 'Dining'
  if (/(park|parking|car|garage)/.test(v)) return 'Parking'
  if (/(wifi|wi-fi|internet|signal|connection)/.test(v)) return 'Wi-Fi'
  return 'Other stay feedback'
}

export default function ReviewPanel({ activeCard, nextMultiplier = 1, onClose, onSubmit, propertyId }) {
  const [sessionId, setSessionId] = useState(null)
  const [history, setHistory] = useState([])       // [{question, answer}]
  const [currentQuestion, setCurrentQuestion] = useState('')
  const [currentResponse, setCurrentResponse] = useState('')
  const [loadingQuestion, setLoadingQuestion] = useState(false)
  const [loadingNext, setLoadingNext] = useState(false)
  const [extracting, setExtracting] = useState(false)
  const [findings, setFindings] = useState(null)
  const [pendingHistory, setPendingHistory] = useState(null)
  const [extractError, setExtractError] = useState(null)

  const isExtra = activeCard?.id === 'something-else'

  const allResponses = useMemo(
    () => [...history.map(h => h.answer), currentResponse].filter(Boolean).join(' '),
    [history, currentResponse]
  )
  const inferred = useMemo(() => inferTopic(allResponses), [allResponses])

  // Reset + start session when gap changes
  useEffect(() => {
    if (!activeCard) return
    setSessionId(null)
    setHistory([])
    setCurrentQuestion('')
    setCurrentResponse('')
    setFindings(null)
    setPendingHistory(null)

    const start = async () => {
      setLoadingQuestion(true)
      try {
        const res = await fetch('/api/chat/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ property_id: propertyId || 'resort', gap_id: activeCard.id }),
        })
        const data = await res.json()
        setSessionId(data.session_id)
        setCurrentQuestion(data.question)
      } catch {
        setCurrentQuestion(activeCard.question || `How was your experience with ${activeCard.title}?`)
      } finally {
        setLoadingQuestion(false)
      }
    }
    start()
  }, [activeCard?.id, propertyId])

  if (!activeCard) return null

  const stepNumber = history.length + 1
  const responseReady = currentResponse.trim().length >= 2

  const handleContinue = async () => {
    if (!responseReady || loadingNext) return
    const answer = currentResponse.trim()

    // Archive current Q&A
    const newHistory = [...history, { question: currentQuestion, answer }]
    setHistory(newHistory)
    setCurrentResponse('')

    if (!sessionId) {
      // No session — submit locally
      doSubmit(newHistory, null)
      return
    }

    setLoadingNext(true)
    try {
      const res = await fetch('/api/chat/respond', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, user_message: answer }),
      })
      const data = await res.json()
      setCurrentQuestion(data.response)

      if (data.is_complete) {
        await doExtract(newHistory)
      }
    } catch {
      doSubmit(newHistory, null)
    } finally {
      setLoadingNext(false)
    }
  }

  const doExtract = async (finalHistory) => {
    setExtracting(true)
    setExtractError(null)
    try {
      const res = await fetch('/api/chat/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      })
      const data = await res.json()
      if (!res.ok) {
        // Server returned an error — show it so we can debug
        setExtractError(`Server error ${res.status}: ${data.detail || JSON.stringify(data)}`)
        return
      }
      if (!data.findings) {
        setExtractError('Extract returned no findings — check server logs.')
        return
      }
      setFindings(data.findings)
      setPendingHistory(finalHistory)
    } catch (err) {
      setExtractError(`Network error: ${err.message}`)
    } finally {
      setExtracting(false)
    }
  }

  const doSubmit = (finalHistory, extractedFindings) => {
    const combined = finalHistory.map(h => h.answer).join(' ')
    if (isExtra) {
      onSubmit({ id: activeCard.id, mode: 'something-else', text: combined, inferredLabel: inferred, notes: '', findings: extractedFindings })
    } else {
      onSubmit({ id: activeCard.id, mode: 'gap', response: combined, notes: finalHistory[finalHistory.length - 1]?.answer || '', findings: extractedFindings })
    }
  }

  const s = {
    panel: { position: 'absolute', top: 0, right: 0, bottom: 0, zIndex: 25, width: 'min(430px,100vw)', background: 'rgba(10,14,26,.94)', backdropFilter: 'blur(24px)', borderLeft: '1px solid rgba(255,255,255,.1)', display: 'flex', flexDirection: 'column' },
    header: { display: 'flex', justifyContent: 'space-between', gap: 14, padding: 20, borderBottom: '1px solid rgba(255,255,255,.1)' },
    title: { fontFamily: "'Playfair Display', serif", fontSize: 24, color: 'var(--text)' },
    subtitle: { fontSize: 12, color: 'var(--muted)', lineHeight: 1.55, marginTop: 4 },
    closeBtn: { width: 40, height: 40, borderRadius: '50%', border: '1px solid rgba(255,255,255,.12)', background: 'rgba(255,255,255,.05)', color: 'var(--text)', cursor: 'pointer', fontSize: 18, flexShrink: 0 },
    body: { flex: 1, overflow: 'auto', padding: '18px 20px 24px', display: 'flex', flexDirection: 'column', gap: 14 },
    card: { background: 'rgba(255,255,255,.03)', border: '1px solid rgba(255,255,255,.06)', borderRadius: 22, padding: 16 },
    footer: { padding: '14px 20px', borderTop: '1px solid rgba(255,255,255,.1)', display: 'flex', justifyContent: 'space-between' },
    cancelBtn: { border: '1px solid rgba(255,255,255,.12)', borderRadius: 999, padding: '12px 18px', background: 'rgba(255,255,255,.06)', color: 'var(--text)', cursor: 'pointer', fontWeight: 600 },
    doneBtn: { border: 'none', borderRadius: 999, padding: '12px 18px', background: 'linear-gradient(135deg,var(--gold),#FFA500)', color: '#000', cursor: 'pointer', fontWeight: 700 },
    prevQA: { display: 'flex', flexDirection: 'column', gap: 4, background: 'rgba(255,255,255,.03)', border: '1px solid rgba(255,255,255,.06)', borderRadius: 14, padding: '10px 14px' },
    prevQ: { fontSize: 12, color: 'var(--muted)', lineHeight: 1.4 },
    prevA: { fontSize: 13, color: '#dbe2f2', lineHeight: 1.5 },
    loading: { fontSize: 14, color: 'var(--muted)', fontStyle: 'italic', padding: '12px 0' },
    dots: { display: 'flex', gap: 5, alignItems: 'center' },
    stepLabel: { fontSize: 11, letterSpacing: '1.4px', textTransform: 'uppercase', color: 'var(--muted)', fontWeight: 700 },
    findingsCard: { background: 'rgba(76,175,80,.1)', border: '1px solid rgba(76,175,80,.25)', borderRadius: 14, padding: '14px 16px' },
    verdictRow: { background: 'rgba(255,255,255,.03)', border: '1px solid rgba(255,255,255,.07)', borderRadius: 10, padding: '10px 14px', marginTop: 6 },
    interpreted: { fontSize: 14, color: '#dbe2f2', background: 'rgba(255,255,255,.03)', border: '1px solid rgba(255,255,255,.06)', borderRadius: 16, padding: 14 },
  }

  const dot = (active) => ({ width: 6, height: 6, borderRadius: '50%', background: active ? 'var(--gold)' : 'rgba(255,255,255,.2)', transition: 'background .3s' })

  return (
    <section style={s.panel} aria-labelledby="review-panel-title">
      {/* Header */}
      <div style={s.header}>
        <div>
          <div id="review-panel-title" style={s.title}>{activeCard.icon} {activeCard.title}</div>
          <div style={s.subtitle}>
            {isExtra ? 'Share one notable detail from your stay.'
              : activeCard.points
                ? `Recommended topic · +${roundTo50(activeCard.points * nextMultiplier)} pts${nextMultiplier < 1 ? ` (${Math.round(nextMultiplier * 100)}% value)` : ''}`
                : 'Recommended topic'}
          </div>
        </div>
        <button type="button" style={s.closeBtn} onClick={onClose} aria-label="Close">✕</button>
      </div>

      <div style={s.body}>
        {/* Previous Q&A history */}
        {history.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {history.map((h, i) => (
              <div key={i} style={s.prevQA}>
                <div style={s.prevQ}>{h.question}</div>
                <div style={s.prevA}>↳ {h.answer}</div>
              </div>
            ))}
          </div>
        )}

        {/* Progress dots */}
        {!findings && !extracting && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={s.dots}>
              {Array.from({ length: stepNumber }).map((_, i) => (
                <div key={i} style={dot(i < stepNumber)} />
              ))}
            </div>
            <span style={s.stepLabel}>Question {stepNumber}</span>
          </div>
        )}

        {/* Main content area */}
        {extractError && (
          <div style={{ background: 'rgba(239,83,80,.12)', border: '1px solid rgba(239,83,80,.4)', borderRadius: 12, padding: '12px 14px', fontSize: 13, color: '#ef5350' }}>
            <b>Extract failed:</b> {extractError}
          </div>
        )}

        {findings ? (
          <div style={s.findingsCard}>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#66bb6a', marginBottom: 8 }}>✓ Insights captured</div>
            {(findings.verdicts || []).map((v, i) => {
              const sc = { positive: '#66bb6a', negative: '#ef5350', neutral: '#42a5f5' }[v.sentiment] || '#42a5f5'
              const si = { positive: '↑', negative: '↓', neutral: '→' }[v.sentiment] || '→'
              return (
                <div key={i} style={{ ...s.verdictRow, borderLeft: `3px solid ${sc}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 600, color: '#c8d0e0' }}>{v.sub_feature}</div>
                      <div style={{ fontSize: 12, color: '#8a9ab5', marginTop: 3 }}>{v.discovery}</div>
                    </div>
                    <div style={{ fontSize: 12, color: sc, fontWeight: 600, flexShrink: 0 }}>{si} {v.sentiment}</div>
                  </div>
                </div>
              )
            })}
            {(findings.cross_landmark_discoveries || []).length > 0 && (
              <>
                <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1 }}>Additional insights</div>
                {findings.cross_landmark_discoveries.map((c, i) => {
                  const sc = { positive: '#66bb6a', negative: '#ef5350', neutral: '#42a5f5' }[c.sentiment] || '#42a5f5'
                  return (
                    <div key={i} style={{ ...s.verdictRow, borderLeft: `3px solid ${sc}` }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: sc }}>{c.area_name}</div>
                      <div style={{ fontSize: 12, color: '#8a9ab5', marginTop: 2 }}>{c.fact_captured}</div>
                    </div>
                  )
                })}
              </>
            )}
          </div>
        ) : extracting ? (
          <div style={s.loading}>Analysing your feedback…</div>
        ) : (
          <div style={s.card}>
            {loadingQuestion ? (
              <div style={s.loading}>Loading question…</div>
            ) : (
              <TextResponseBox
                key={stepNumber}
                id={`response-${activeCard.id}-q${stepNumber}`}
                label={stepNumber === 1 ? 'Question' : 'Follow-up'}
                prompt={loadingNext ? 'Generating next question…' : (isExtra && stepNumber === 1 ? 'What would you like to mention?' : currentQuestion)}
                helperText={stepNumber === 1 ? (isExtra ? 'Share one short detail that stood out.' : 'Type your answer in your own words.') : ''}
                whyText={stepNumber === 1 ? 'We ask targeted follow-ups when a property detail has not been confirmed recently.' : ''}
                placeholder={isExtra ? 'One short sentence is enough.' : stepNumber === 1 ? 'Write your answer here.' : 'Add one more detail…'}
                value={currentResponse}
                onChange={setCurrentResponse}
                onSubmit={handleContinue}
                submitLabel={loadingNext ? 'Loading…' : 'Continue'}
                disabled={!responseReady || loadingNext}
                minRows={4}
                autoFocus
              />
            )}
          </div>
        )}

        {isExtra && allResponses && !findings && !extracting && (
          <div style={s.interpreted}>We understood this as: <b>{inferred}</b></div>
        )}
      </div>

      <div style={s.footer}>
        {findings
          ? <button type="button" style={s.doneBtn} onClick={() => { doSubmit(pendingHistory || history, findings); onClose() }}>Done</button>
          : <button type="button" style={s.cancelBtn} onClick={onClose}>Cancel</button>}
      </div>
    </section>
  )
}
