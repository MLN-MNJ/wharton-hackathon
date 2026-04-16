export default function SummaryPanel({ open, answers, gaps, onClose }) {
  if (!open) return null

  const resolved = Object.values(answers)

  return (
    <div className="summary-overlay">
      <div className="summary-header">
        <h1>Knowledge impact</h1>
        <p>Show judges how fresh traveler signals improve property understanding.</p>
        <button className="icon-btn floating" onClick={onClose}>✕</button>
      </div>

      <div className="summary-grid">
        {resolved.map((answer, idx) => {
          const gap = gaps.find((g) => g.id === answer.id)

          return (
            <div key={idx} className="summary-card">
              {answer.mode === 'something-else' ? (
                <>
                  <div className="summary-title">✍️ Something else</div>
                  <div className="summary-text"><b>Detected topic:</b> {answer.inferredLabel}</div>
                  <div className="summary-text"><b>User text:</b> {answer.text}</div>
                  <div className="summary-badge">New unprompted signal captured</div>
                </>
              ) : (
                <>
                  <div className="summary-title">{gap?.icon} {gap?.title}</div>
                  <div className="summary-text"><b>Before:</b> {gap?.beforeMain}</div>
                  <div className="summary-text"><b>Answer:</b> {answer.choice}</div>
                  {answer.notes ? <div className="summary-text"><b>Note:</b> {answer.notes}</div> : null}
                  <div className="summary-text"><b>After:</b> {gap?.afterMain}</div>
                  <div className="summary-badge">Fresh traveler-confirmed signal added</div>
                </>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
