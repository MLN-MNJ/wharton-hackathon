import { roundTo50 } from '../App'

export default function Sidebar({ gaps, selectedGapId, answers, onSelectGap, nextMultiplier }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-title">Help Improve This Stay</div>
      </div>

      <div className="gap-list">
        {gaps.map((gap) => {
          const done = Boolean(answers[gap.id])
          const isExtra = !gap.points

          return (
            <button
              key={gap.id}
              type="button"
              className={`gap-card ${selectedGapId === gap.id ? 'active' : ''} ${done ? 'done' : ''} ${isExtra ? 'extra' : ''}`}
              onClick={() => onSelectGap(gap.id)}
            >
              <div className="gap-top">
                <div className="gap-name">{gap.icon} {gap.title}</div>
                {gap.points ? <div className="gap-points">+{roundTo50(gap.points * nextMultiplier)} pts</div> : null}
              </div>

              {/* <div className="gap-why">{gap.summary}</div> */}

              {/* {gap.signals ? (
                <div className="mini-row">
                  <span className="mini-pill">Missing <b>{gap.signals.missing}</b></span>
                  <span className="mini-pill">Stale <b>{gap.signals.stale}</b></span>
                  <span className="mini-pill">Conflict <b>{gap.signals.conflict}</b></span>
                </div>
              ) : null} */}
            </button>
          )
        })}
      </div>
    </aside>
  )
}
