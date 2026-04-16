# GapQuest React STL UI

A Vite + React version of the STL-based review prototype.

## What this version includes
- 3D STL property view using `three`
- ranked top-gap cards
- labels above 3D hotspot spheres
- camera focus when a sidebar card is clicked
- a simple right-side review panel
- a **Something else I want to mention** card
- automatic frontend topic inference for the Something Else flow
- a summary panel for demoing property knowledge impact

## Build and run
1. Install Node.js 18+.
2. Open a terminal in this folder.
3. Run:
   ```bash
   npm install
   npm run dev
   ```
4. Open the local Vite URL shown in the terminal.

## Build for production
```bash
npm run build
npm run preview
```

## Project structure
- `src/App.jsx` - main shell and state
- `src/components/ThreeScene.jsx` - STL rendering, labels, focus, and hotspot clicks
- `src/components/Sidebar.jsx` - ranked gap cards + Something Else card
- `src/components/ReviewPanel.jsx` - gap question flow and Something Else text flow
- `src/components/SummaryPanel.jsx` - demo summary / knowledge impact
- `src/data/gaps.js` - mock data for top gaps and hotspot positions
- `public/demo-resort.stl` - bundled demo STL file

## Change policy for future UI updates
After this ZIP, UI changes should be communicated as:
- `FILENAME` + exact change
- explicitly call out any new file to create
