import { useEffect, useRef, useState } from 'react'

function getSpeechRecognition() {
  if (typeof window === 'undefined') return null
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

export default function TextResponseBox({
  id, label, prompt, helperText = '', whyText = '', placeholder = '',
  value, onChange, onSubmit, submitLabel = 'Continue',
  disabled = false, minRows = 4, autoFocus = false,
}) {
  const textareaRef = useRef(null)
  const recognitionRef = useRef(null)
  const [isListening, setIsListening] = useState(false)
  const [speechSupported, setSpeechSupported] = useState(false)
  const [speechError, setSpeechError] = useState('')
  const [showWhy, setShowWhy] = useState(false)

  useEffect(() => { setSpeechSupported(Boolean(getSpeechRecognition())) }, [])

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.max(el.scrollHeight, minRows * 24 + 24)}px`
  }, [value, minRows])

  useEffect(() => {
    if (autoFocus && textareaRef.current) textareaRef.current.focus()
  }, [autoFocus])

  useEffect(() => {
    return () => { if (recognitionRef.current) { recognitionRef.current.stop(); recognitionRef.current = null } }
  }, [])

  const handleVoiceInput = () => {
    const SR = getSpeechRecognition()
    if (!SR) { setSpeechError('Voice input is not supported in this browser.'); return }
    if (isListening && recognitionRef.current) { recognitionRef.current.stop(); return }
    setSpeechError('')
    const recognition = new SR()
    recognitionRef.current = recognition
    recognition.lang = 'en-US'
    recognition.interimResults = true
    recognition.continuous = false
    recognition.maxAlternatives = 1
    recognition.onstart = () => setIsListening(true)
    recognition.onerror = (e) => { setSpeechError(e?.error === 'not-allowed' ? 'Microphone access was blocked.' : 'Voice input failed. Please try again.'); setIsListening(false) }
    recognition.onend = () => setIsListening(false)
    recognition.onresult = (e) => {
      let transcript = ''
      for (let i = 0; i < e.results.length; i++) transcript += e.results[i][0].transcript
      const clean = transcript.replace(/\s+/g, ' ').trim()
      onChange(value?.trim() ? `${value.trim()} ${clean}` : clean)
    }
    recognition.start()
  }

  const s = {
    root: { display: 'flex', flexDirection: 'column', gap: 12 },
    label: { fontSize: 11, letterSpacing: '1.6px', textTransform: 'uppercase', color: 'var(--muted)', fontWeight: 700 },
    prompt: { fontFamily: "'Playfair Display', serif", fontSize: 18, lineHeight: 1.45, color: 'var(--text)' },
    helper: { fontSize: 13, lineHeight: 1.5, color: 'var(--text)', fontWeight: 600 },
    whyBlock: { display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-start' },
    whyToggle: { border: 'none', background: 'transparent', color: '#cfd5e8', textDecoration: 'underline', fontSize: 14, cursor: 'pointer', padding: 0 },
    whyBox: { fontSize: 13, lineHeight: 1.55, color: 'var(--muted)', background: 'rgba(255,255,255,.04)', border: '1px solid rgba(255,255,255,.07)', borderRadius: 12, padding: 12, width: '100%' },
    textarea: { width: '100%', resize: 'none', overflow: 'hidden', borderRadius: 16, padding: '16px', background: 'rgba(255,255,255,.05)', border: '1px solid rgba(255,255,255,.12)', color: 'var(--text)', fontSize: 14, lineHeight: 1.6, outline: 'none', minHeight: 120 },
    toolbar: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' },
    voiceBtn: { border: isListening ? '1px solid rgba(255,215,0,.45)' : '1px solid rgba(255,255,255,.12)', background: isListening ? 'rgba(255,215,0,.12)' : 'rgba(255,255,255,.05)', color: 'var(--text)', borderRadius: 999, padding: '10px 14px', cursor: 'pointer', fontSize: 14, fontWeight: 600 },
    submitBtn: { border: 'none', borderRadius: 999, padding: '10px 16px', background: disabled ? 'rgba(255,255,255,.12)' : 'linear-gradient(135deg,var(--gold),#FFA500)', color: disabled ? 'rgba(255,255,255,.45)' : '#000', fontWeight: 700, cursor: disabled ? 'not-allowed' : 'pointer' },
    voiceHint: { fontSize: 12, color: 'var(--muted)' },
    error: { fontSize: 12, color: '#ff8d8d' },
  }

  return (
    <div style={s.root}>
      {label && <span style={s.label}>{label}</span>}
      {prompt && <div style={s.prompt}>{prompt}</div>}
      {whyText && (
        <div style={s.whyBlock}>
          <button type="button" style={s.whyToggle} onClick={() => setShowWhy(v => !v)} aria-expanded={showWhy} title="Why this question?">ℹ️</button>
          {showWhy && <div style={s.whyBox}>{whyText}</div>}
        </div>
      )}
      {helperText && <div style={s.helper}>{helperText}</div>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <textarea id={id} ref={textareaRef} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} rows={minRows} style={s.textarea} />
        <div style={s.toolbar}>
          {speechSupported
            ? <button type="button" style={s.voiceBtn} onClick={handleVoiceInput} aria-pressed={isListening}>{isListening ? '🎙️ Listening…' : '🎤 Voice input'}</button>
            : <span style={s.voiceHint}>Voice input unavailable</span>}
          <button type="button" style={s.submitBtn} disabled={disabled} onClick={onSubmit}>{submitLabel}</button>
        </div>
      </div>
      {speechError && <div style={s.error}>{speechError}</div>}
    </div>
  )
}
