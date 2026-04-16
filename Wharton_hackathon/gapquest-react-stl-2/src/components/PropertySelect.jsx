export default function PropertySelect({ properties, onSelect }) {
  return (
    <div className="property-select-screen">
      <div className="property-select-inner">
        <div className="property-select-logo">🗺️</div>
        <h1 className="property-select-title">GapQuest</h1>
        <p className="property-select-sub">Choose a property to explore</p>

        <div className="property-select-grid">
          {properties.map((prop) => (
            <button
              key={prop.id}
              className="property-card"
              onClick={() => onSelect(prop)}
            >
              <span className="property-card-icon">{prop.icon}</span>
              <span className="property-card-name">{prop.name}</span>
              <span className="property-card-hint">
                {prop.gaps.filter((g) => g.points).length} gaps to fix
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
