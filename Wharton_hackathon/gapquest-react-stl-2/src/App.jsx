import { useEffect, useMemo, useState } from 'react'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import Sidebar from './components/Sidebar'
import ThreeScene from './components/ThreeScene'
import ReviewPanel from './components/ReviewPanel'
import SummaryPanel from './components/SummaryPanel'
import Dashboard from './components/Dashboard'
import { properties } from './data/properties'

// Multiplier drops 20% per submission, floors at 25%
function getMultiplier(submissionIndex) {
  return Math.max(0.25, 1 - submissionIndex * 0.2)
}

export function roundTo50(n) {
  if (n <= 0) return 10
  if (n <= 25) return 25
  return Math.max(10, Math.round(n / 50) * 50)
}

const propertyCardMeta = {
  resort: {
    city: 'Broomfield, CO',
    rating: 9.1,
    ratingLabel: 'Exceptional',
    reviewCount: '11 reviews',
    nightly: '$461 nightly',
    total: '$1,115 total',
    feeText: 'Total with taxes and fees',
    badge: 'Ad',
  },
  hotel: {
    city: 'San Isidro, Costa Rica',
    rating: 8.6,
    ratingLabel: 'Excellent',
    reviewCount: '1,015 reviews',
    nightly: '$404 nightly',
    total: '$1,003 total',
    feeText: 'Total with taxes and fees',
    badge: 'Ad',
  },
}

function getCardMeta(index) {
  return index === 0 ? propertyCardMeta.resort : propertyCardMeta.hotel
}

function getPropertyImage(index) {
  const images = [
    'https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=1200&q=80',
    'https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=1200&q=80',
  ]
  return images[index % images.length]
}

function ThemeToggle({ isDark, onToggle }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      style={{
        border: isDark ? '1px solid rgba(255,255,255,.18)' : '1px solid #d1d5db',
        borderRadius: 999,
        background: isDark ? 'rgba(255,255,255,.08)' : '#fff',
        color: isDark ? '#fff' : '#334155',
        padding: '8px 14px',
        fontSize: 14,
        fontWeight: 600,
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: 6,
      }}
    >
      {isDark ? '☀️ Light' : '🌙 Dark'}
    </button>
  )
}

function PropertyEntryScreen({ properties, onSelect, isDark, onToggleTheme, onOpenDashboard }) {
  const tabs = ['Overview', 'About', 'Rooms', 'Accessibility', 'Policies']

  // Preload all GLB files into Three.js cache while the user is on this screen
  useEffect(() => {
    THREE.Cache.enabled = true
    const loader = new GLTFLoader()
    properties.forEach((prop) => {
      if (prop.modelUrl) loader.load(prop.modelUrl, () => {}, undefined, () => {})
    })
  }, [properties])

  const c = {
    page:       isDark ? '#0a0e1a' : '#f7f7f8',
    text:       isDark ? '#f0ede8' : '#1f2a44',
    subText:    isDark ? '#8a8a9a' : '#22345c',
    border:     isDark ? 'rgba(255,255,255,.1)' : '#d9dde5',
    card:       isDark ? '#141824' : '#ffffff',
    cardBorder: isDark ? 'rgba(255,255,255,.1)' : '#d8dce5',
    tabActive:  isDark ? '#60a5fa' : '#2563eb',
    tabText:    isDark ? '#f0ede8' : '#172554',
    btnBorder:  isDark ? 'rgba(255,255,255,.18)' : '#cfd5e3',
    btnBg:      isDark ? 'rgba(255,255,255,.06)' : '#ffffff',
    btnText:    isDark ? '#f0ede8' : '#334155',
    primaryBg:  isDark ? '#3b82f6' : '#2563eb',
    imgBg:      isDark ? '#1e2535' : '#e5e7eb',
    green:      '#198754',
  }

  return (
    <div style={{ minHeight: '100vh', background: c.page, color: c.text, padding: '0 26px 36px', overflowX: 'hidden' }}>

      {/* Top tabs bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${c.border}`, padding: '8px 0 0', marginBottom: 18, gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          {tabs.map((tab) => (
            <button
              key={tab}
              type="button"
              style={{
                border: 'none',
                background: 'transparent',
                color: tab === 'Rooms' ? c.tabActive : c.tabText,
                fontWeight: tab === 'Rooms' ? 700 : 600,
                fontSize: 16,
                padding: '10px 22px 14px',
                borderBottom: tab === 'Rooms' ? `3px solid ${c.tabActive}` : '3px solid transparent',
                cursor: 'default',
              }}
            >
              {tab}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12, paddingBottom: 8 }}>
          <ThemeToggle isDark={isDark} onToggle={onToggleTheme} />
          <button
            type="button"
            onClick={onOpenDashboard}
            style={{ borderRadius: 999, border: `1px solid ${c.btnBorder}`, background: c.btnBg, color: c.btnText, padding: '12px 18px', fontWeight: 600, fontSize: 15 }}
          >
            📊 Dashboard
          </button>
          <button type="button" style={{ borderRadius: 999, border: `1px solid ${c.btnBorder}`, background: c.btnBg, color: c.btnText, padding: '12px 18px', fontWeight: 600, fontSize: 15 }}>
            ♡ Save
          </button>
          <button type="button" style={{ borderRadius: 999, border: 'none', background: c.primaryBg, color: '#fff', padding: '14px 24px', fontWeight: 700, fontSize: 16 }}>
            Select a room
          </button>
        </div>
      </div>

      <div style={{ fontSize: 28, fontWeight: 800, color: c.text, margin: '18px 0' }}>Past bookings</div>

      <div style={{ display: 'flex', gap: 18, overflowX: 'auto', paddingBottom: 8 }}>
        {properties.map((property, index) => {
          const meta = getCardMeta(index)
          const imageUrl = getPropertyImage(index)

          return (
            <button
              key={property.id}
              type="button"
              onClick={() => onSelect(property)}
              style={{
                minWidth: 390, maxWidth: 390,
                background: c.card,
                border: `1px solid ${c.cardBorder}`,
                borderRadius: 24,
                overflow: 'hidden',
                cursor: 'pointer',
                flexShrink: 0,
                textAlign: 'left',
                transition: 'transform .15s ease, box-shadow .15s ease',
              }}
              onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-3px)'; e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,.12)' }}
              onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = 'none' }}
            >
              {/* Image */}
              {/* Banner */}
              <div style={{
                background: 'linear-gradient(90deg, #2563eb, #3b82f6)',
                color: '#fff',
                fontWeight: 600,
                fontSize: 14,
                padding: '10px 14px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}>
                <span>Earn Expedia points by reviewing this property</span>
                <span style={{ fontSize: 18 }}>→</span>
              </div>

              {/* Image */}
              <div style={{ position: 'relative', height: 210, background: c.imgBg, overflow: 'hidden' }}>
                  <img src={imageUrl} alt={property.name} style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
              </div>

              {/* Body */}
              <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ fontSize: 18, fontWeight: 800, color: c.text }}>{property.name}</div>
                <div style={{ fontSize: 15, color: c.subText }}>{meta.city}</div>

                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginTop: 2 }}>
                  <div style={{ background: c.green, color: '#fff', borderRadius: 6, minWidth: 40, height: 30, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 16 }}>
                    {meta.rating}
                  </div>
                  <div>
                    <div style={{ fontSize: 15, fontWeight: 700, color: c.text }}>{meta.ratingLabel}</div>
                    <div style={{ fontSize: 14, color: c.subText }}>{meta.reviewCount}</div>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 16, marginTop: 8 }}>
                  <div style={{
                    // border: '1px solid rgba(59,130,246,.35)',
                    background: 'linear-gradient(90deg, #2563eb, #3b82f6)',
                    color: '#fff',
                    borderRadius: 999,
                    padding: '10px 16px',
                    fontSize: 14,
                    fontWeight: 600
                  }}>
                    Review hotel
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 15, color: c.subText }}>{meta.nightly}</div>
                    <div style={{ fontSize: 18, fontWeight: 800, color: c.text, marginTop: 2 }}>{meta.total}</div>
                    <div style={{ fontSize: 13, color: c.green, marginTop: 4 }}>✓ {meta.feeText}</div>
                  </div>
                </div>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default function App() {
  const [selectedProperty, setSelectedProperty] = useState(null)
  const [selectedGapId, setSelectedGapId] = useState(null)
  const [answers, setAnswers] = useState({})
  const [summaryOpen, setSummaryOpen] = useState(false)
  const [isDark, setIsDark] = useState(true)
  const [dashboardOpen, setDashboardOpen] = useState(false)

  const gaps = selectedProperty?.gaps ?? []

  const activeCard = useMemo(
    () => gaps.find((item) => item.id === selectedGapId) || null,
    [selectedGapId, gaps],
  )

  const points = Object.values(answers).reduce((sum, item) => {
    const gap = gaps.find((g) => g.id === item.id)
    return sum + roundTo50((gap?.points || 0) * (item.multiplier ?? 1))
  }, 0)

  const resolvedCount = Object.values(answers).filter((item) => {
    const gap = gaps.find((g) => g.id === item.id)
    return Boolean(gap?.points)
  }).length

  const nextMultiplier = getMultiplier(Object.keys(answers).length)

  const handleSelectProperty = (prop) => {
    setSelectedProperty(prop)
    setSelectedGapId(null)
    setAnswers({})
  }

  const handleSelectGap = (gapId) => setSelectedGapId(gapId)

  const handleSubmit = (payload) => {
    const submissionIndex = Object.keys(answers).length
    const multiplier = getMultiplier(submissionIndex)
    setAnswers((prev) => ({ ...prev, [payload.id]: { ...payload, multiplier } }))
    setSelectedGapId(null)
  }

  const handleBack = () => {
    setSelectedProperty(null)
  }

  if (!selectedProperty) {
    return (
      <>
        <PropertyEntryScreen
          properties={properties}
          onSelect={handleSelectProperty}
          isDark={isDark}
          onToggleTheme={() => setIsDark(d => !d)}
          onOpenDashboard={() => setDashboardOpen(true)}
        />
        {dashboardOpen && (
          <Dashboard isDark={isDark} onClose={() => setDashboardOpen(false)} />
        )}
      </>
    )
  }

  return (
    <div className={`app-shell${isDark ? '' : ' app-light'}`}>
      <header className="topbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button className="btn-secondary" style={{ padding: '8px 14px', fontSize: '12px' }} onClick={handleBack}>
            ← Properties
          </button>
          <div>
            <div className="brand-title">{selectedProperty.icon} {selectedProperty.name}</div>
            <div className="brand-sub">Guide the traveler to high-value gaps</div>
          </div>
        </div>

        <div className="topbar-center">
          <div className="score-pill">Earned <strong>{points} pts</strong></div>
          {/* <div className="progress-copy">{resolvedCount} / 2 gaps resolve</div> */}
        </div>

        <div className="topbar-actions">
          <button className="btn-secondary" onClick={() => setDashboardOpen(true)}>
            📊 Dashboard
          </button>
          <button className="btn-secondary" onClick={() => setSummaryOpen(true)}>
            Knowledge impact
          </button>
        </div>
      </header>

      <Sidebar gaps={gaps} selectedGapId={selectedGapId} answers={answers} onSelectGap={handleSelectGap} nextMultiplier={nextMultiplier} />

      <ThreeScene
        modelUrl={selectedProperty.modelUrl}
        modelRotation={selectedProperty.modelRotation}
        cameraConfig={selectedProperty.camera}
        gaps={gaps}
        answers={answers}
        nextMultiplier={nextMultiplier}
        selectedGapId={selectedGapId}
        onSelectGap={handleSelectGap}
      />

      <ReviewPanel activeCard={activeCard} nextMultiplier={nextMultiplier} onClose={() => setSelectedGapId(null)} onSubmit={handleSubmit} propertyId={selectedProperty?.id} />

      <SummaryPanel open={summaryOpen} answers={answers} gaps={gaps} onClose={() => setSummaryOpen(false)} />

      {dashboardOpen && (
        <Dashboard isDark={isDark} onClose={() => setDashboardOpen(false)} />
      )}
    </div>
  )
}
