import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

const FALLBACK_OVERVIEW_POS = new THREE.Vector3(0, -1400, 1200)
const FALLBACK_OVERVIEW_LOOK = new THREE.Vector3(0, 0, 200)

export default function ThreeScene({ modelUrl, modelRotation, cameraConfig, gaps, answers = {}, nextMultiplier = 1, selectedGapId, onSelectGap }) {
  const mountRef = useRef(null)

  const onSelectGapRef = useRef(onSelectGap)
  const selectedGapIdRef = useRef(selectedGapId)
  const gapsRef = useRef(gaps)

  const overviewRef = useRef({
    pos: FALLBACK_OVERVIEW_POS.clone(),
    look: FALLBACK_OVERVIEW_LOOK.clone(),
  })

  const cameraTargetRef = useRef({
    pos: FALLBACK_OVERVIEW_POS.clone(),
    look: FALLBACK_OVERVIEW_LOOK.clone(),
  })

  const frameRef = useRef(null)
  const mouseRef = useRef(new THREE.Vector2())

  const modelRootRef = useRef(null)
  const interactiveRef = useRef([])
  const labelEntriesRef = useRef([])

  useEffect(() => {
    onSelectGapRef.current = onSelectGap
  }, [onSelectGap])

  // Update label scores whenever answers or multiplier changes — no scene rebuild needed
  useEffect(() => {
    labelEntriesRef.current.forEach(({ gap, label }) => {
      const answered = Boolean(answers[gap.id])
      const scoreSpan = label.querySelector('.scene-hotspot-score')

      if (!gap.points) return // "something else" has no score

      if (answered) {
        // Hide score after submission
        if (scoreSpan) scoreSpan.remove()
      } else {
        const raw = gap.points * nextMultiplier
        const adjustedPts = raw <= 0 ? 10 : raw <= 25 ? 25 : Math.max(10, Math.round(raw / 50) * 50)
        if (scoreSpan) {
          scoreSpan.textContent = `+${adjustedPts} pts`
        } else {
          const span = document.createElement('span')
          span.className = 'scene-hotspot-score'
          span.textContent = `+${adjustedPts} pts`
          label.appendChild(span)
        }
      }
    })
  }, [answers, nextMultiplier])

  useEffect(() => {
    gapsRef.current = gaps
  }, [gaps])

  useEffect(() => {
    selectedGapIdRef.current = selectedGapId

    const selectedGap = gapsRef.current.find((gap) => gap.id === selectedGapId) || null
    const cameraTarget = cameraTargetRef.current

    if (!selectedGap?.position) {
      cameraTarget.pos.copy(overviewRef.current.pos)
      cameraTarget.look.copy(overviewRef.current.look)
      return
    }

    cameraTarget.pos.set(
      selectedGap.position.x,
      selectedGap.position.y - 600,
      selectedGap.position.z + 500,
    )
    cameraTarget.look.set(
      selectedGap.position.x,
      selectedGap.position.y,
      selectedGap.position.z,
    )
  }, [selectedGapId])

  useEffect(() => {
    if (!modelUrl || !mountRef.current) return

    const mount = mountRef.current

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x1a2a3a)
    scene.fog = new THREE.Fog(0x1a2a3a, 8000, 14000)

    const camera = new THREE.PerspectiveCamera(
      45,
      mount.clientWidth / mount.clientHeight,
      10,
      20000,
    )
    camera.position.copy(overviewRef.current.pos)

    const renderer = new THREE.WebGLRenderer({ antialias: window.devicePixelRatio < 2, alpha: false, powerPreference: 'high-performance' })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1))
    renderer.setSize(mount.clientWidth, mount.clientHeight)
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.0
    mount.appendChild(renderer.domElement)

    const labelLayer = document.createElement('div')
    labelLayer.className = 'scene-label-layer'
    mount.appendChild(labelLayer)

    scene.add(new THREE.AmbientLight(0xffffff, 2.8))

    const sun = new THREE.DirectionalLight(0xffffff, 3.0)
    sun.position.set(800, -1200, 2000)
    scene.add(sun)

    const fill = new THREE.DirectionalLight(0xffffff, 1.5)
    fill.position.set(-1000, 800, 500)
    scene.add(fill)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.target.copy(overviewRef.current.look)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.rotateSpeed = 0.6
    controls.minDistance = 250
    controls.maxDistance = 25000

    const raycaster = new THREE.Raycaster()
    const interactive = []
    const labelEntries = []
    interactiveRef.current = interactive
    labelEntriesRef.current = labelEntries

    THREE.Cache.enabled = true
    const loader = new GLTFLoader()
    loader.load(
      modelUrl,
      (gltf) => {
        const root = gltf.scene

        // 1. Rotate upright — each property defines its own rotation
        const rot = modelRotation ?? { x: Math.PI / 2, y: 0, z: 0 }
        root.rotation.set(rot.x, rot.y, rot.z)
        root.updateMatrixWorld(true)

        // 2. Measure raw size
        const rawBox = new THREE.Box3().setFromObject(root)
        const rawSize = rawBox.getSize(new THREE.Vector3())
        const rawMax = Math.max(rawSize.x, rawSize.y, rawSize.z) || 1

        // 3. Scale so the longest axis = TARGET units (markers live in this space)
        const TARGET = 2000
        const scaleFactor = TARGET / rawMax
        root.scale.setScalar(scaleFactor)
        root.updateMatrixWorld(true)

        // 4. Re-measure after scale, then center & sit on z=0
        const scaledBox = new THREE.Box3().setFromObject(root)
        const scaledCenter = scaledBox.getCenter(new THREE.Vector3())
        root.position.set(-scaledCenter.x, -scaledCenter.y, -scaledBox.min.z)
        root.updateMatrixWorld(true)

        console.log(`Model loaded — raw max dim: ${rawMax.toFixed(2)}, scale applied: ${scaleFactor.toFixed(4)}`)

        root.traverse((obj) => {
          if (!obj.isMesh) return
          obj.castShadow = false
          obj.receiveShadow = true

          // Apply vertex colours if geometry has them; otherwise use a visible fallback
          const geo = obj.geometry
          const hasVertexColor = !!geo?.attributes?.color
          const mats = Array.isArray(obj.material) ? obj.material : [obj.material]
          mats.forEach((m) => {
            if (!m) return
            if (hasVertexColor) {
              m.vertexColors = true
            } else if (!m.map && (!m.color || (m.color.r === 0 && m.color.g === 0 && m.color.b === 0))) {
              m.color = new THREE.Color(0xc8b89a)
            }
            m.needsUpdate = true
          })
        })

        scene.add(root)
        modelRootRef.current = root

        // 5. Recompute final bounds for camera fitting
        const finalBox = new THREE.Box3().setFromObject(root)
        const finalCenter = finalBox.getCenter(new THREE.Vector3())
        const finalSize = finalBox.getSize(new THREE.Vector3())
        const maxDim = Math.max(finalSize.x, finalSize.y, finalSize.z) || 1000

        // Auto-fit overview camera — use per-property config or sensible defaults
        const cam = cameraConfig ?? { distY: 1.2, distZ: 1.0, lookZ: 0.05 }
        const overviewPos = new THREE.Vector3(
          finalCenter.x,
          finalCenter.y - maxDim * cam.distY,
          finalCenter.z + maxDim * cam.distZ,
        )
        const overviewLook = new THREE.Vector3(
          finalCenter.x,
          finalCenter.y,
          finalCenter.z + maxDim * cam.lookZ,
        )

        overviewRef.current.pos.copy(overviewPos)
        overviewRef.current.look.copy(overviewLook)

        if (!selectedGapIdRef.current) {
          camera.position.copy(overviewPos)
          controls.target.copy(overviewLook)
          cameraTargetRef.current.pos.copy(overviewPos)
          cameraTargetRef.current.look.copy(overviewLook)
          controls.update()
        }
      },
      undefined,
      (err) => {
        console.error('Failed to load GLB:', err)
      },
    )

    gaps.forEach((gap) => {
      const color = new THREE.Color(gap.color)
      const isExtra = !gap.points
      const radius = isExtra ? 32 : 40
      const ringInner = isExtra ? 42 : 52
      const ringOuter = isExtra ? 48 : 60

      const sphere = new THREE.Mesh(
        new THREE.SphereGeometry(radius, 10, 10),
        new THREE.MeshBasicMaterial({
          color,
          transparent: true,
          opacity: 0.92,
        }),
      )
      sphere.position.set(gap.position.x, gap.position.y, gap.position.z)
      sphere.userData.id = gap.id
      scene.add(sphere)
      interactive.push(sphere)

      const ring = new THREE.Mesh(
        new THREE.RingGeometry(ringInner, ringOuter, 32),
        new THREE.MeshBasicMaterial({
          color,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.22,
        }),
      )
      ring.position.set(gap.position.x, gap.position.y, gap.position.z)
      scene.add(ring)

      const label = document.createElement('button')
      label.className = `scene-hotspot-label ${isExtra ? 'extra' : ''}`
      label.type = 'button'
      label.style.setProperty('--gap-color', gap.color)
      label.innerHTML = `
        <span class="scene-hotspot-dot"></span>
        <span class="scene-hotspot-name">${gap.icon} ${gap.title}</span>
        ${gap.points ? `<span class="scene-hotspot-score">+${gap.points <= 25 ? 25 : Math.round(gap.points / 50) * 50} pts</span>` : ''}
      `
      label.addEventListener('click', () => onSelectGapRef.current?.(gap.id))
      labelLayer.appendChild(label)

      labelEntries.push({ gap, sphere, ring, label })
    })

    const onResize = () => {
      if (!mount) return
      camera.aspect = mount.clientWidth / mount.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(mount.clientWidth, mount.clientHeight)
    }

    const onClick = (event) => {
      const rect = renderer.domElement.getBoundingClientRect()
      mouseRef.current.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
      mouseRef.current.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
      raycaster.setFromCamera(mouseRef.current, camera)

      // SHIFT+CLICK = debug mode: log 3D coords for marker placement
      if (event.shiftKey && modelRootRef.current) {
        const modelMeshes = []
        modelRootRef.current.traverse((obj) => { if (obj.isMesh) modelMeshes.push(obj) })
        const hits = raycaster.intersectObjects(modelMeshes, true)
        if (hits.length) {
          const p = hits[0].point
          console.log(`📍 Shift-clicked position:\n  x: ${p.x.toFixed(0)}, y: ${p.y.toFixed(0)}, z: ${p.z.toFixed(0)}\n  → position: { x: ${p.x.toFixed(0)}, y: ${p.y.toFixed(0)}, z: ${p.z.toFixed(0)} }`)
        }
        return
      }

      const hits = raycaster.intersectObjects(interactive)
      if (hits.length) {
        onSelectGapRef.current?.(hits[0].object.userData.id)
      }
    }

    const animate = () => {
      frameRef.current = requestAnimationFrame(animate)
      const t = performance.now() / 1000

      camera.position.lerp(cameraTargetRef.current.pos, 0.05)
      controls.target.lerp(cameraTargetRef.current.look, 0.05)

      labelEntries.forEach(({ gap, sphere, ring, label }) => {
        const isActive = gap.id === selectedGapIdRef.current
        const pulse = isActive
          ? 1.18
          : 1 + Math.sin(t * 2.2 + sphere.position.x * 0.01) * 0.04

        sphere.scale.setScalar(pulse)
        ring.scale.setScalar(1 + Math.sin(t * 2.4 + sphere.position.y * 0.01) * 0.08)
        ring.material.opacity = isActive ? 0.38 : 0.16
        ring.lookAt(camera.position)

        const world = new THREE.Vector3(
          gap.position.x,
          gap.position.y,
          gap.position.z + 95,
        )
        const projected = world.project(camera)
        const visible = projected.z < 1

        const x = (projected.x * 0.5 + 0.5) * mount.clientWidth
        const y = (-(projected.y * 0.5) + 0.5) * mount.clientHeight - 24

        label.style.left = `${x}px`
        label.style.top = `${y}px`
        label.style.opacity = visible ? '1' : '0'
        label.classList.toggle('active', isActive)
      })

      controls.update()
      renderer.render(scene, camera)
    }

    window.addEventListener('resize', onResize)
    renderer.domElement.addEventListener('click', onClick)
    animate()

    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current)
      window.removeEventListener('resize', onResize)
      renderer.domElement.removeEventListener('click', onClick)

      if (modelRootRef.current) {
        scene.remove(modelRootRef.current)
        modelRootRef.current.traverse((obj) => {
          if (!obj.isMesh) return
          obj.geometry?.dispose()
          if (Array.isArray(obj.material)) {
            obj.material.forEach((m) => m?.dispose?.())
          } else {
            obj.material?.dispose?.()
          }
        })
        modelRootRef.current = null
      }

      labelEntries.forEach(({ sphere, ring, label }) => {
        scene.remove(sphere)
        scene.remove(ring)
        sphere.geometry.dispose()
        sphere.material.dispose()
        ring.geometry.dispose()
        ring.material.dispose()
        label.remove()
      })

      controls.dispose()
      renderer.dispose()

      if (mount.contains(labelLayer)) mount.removeChild(labelLayer)
      if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement)
    }
  }, [modelUrl, modelRotation, cameraConfig, gaps])

  return <div ref={mountRef} className="scene-root" />
}
