export default function FileGate({ onUseDemo, onFileSelect }) {
  return (
    <div className="file-screen">
      <div className="hero-icon">🏝️</div>
      <h1 className="hero-title">GapQuest</h1>
      <p className="hero-tag">STL-Based Smart Travel Review Copilot</p>
      <p className="hero-sub">
        Keep the immersive 3D property view, but guide reviewers toward the most valuable knowledge gaps.
      </p>
      <div className="file-actions">
        <label className="btn-primary">
          Upload STL
          <input
            type="file"
            accept=".stl"
            hidden
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) onFileSelect(file)
            }}
          />
        </label>
        <button className="btn-secondary" onClick={onUseDemo}>Use bundled demo STL</button>
      </div>
      <p className="file-hint">The demo STL is included in /public/demo-resort.stl.</p>
    </div>
  )
}
