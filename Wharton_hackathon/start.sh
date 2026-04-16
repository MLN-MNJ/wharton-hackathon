#!/bin/bash
# GapQuest — Start both servers

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "Starting FastAPI backend on http://localhost:8507 ..."
cd "$ROOT/adaptive_review_engine"
python api_server.py &
BACKEND_PID=$!

echo "Starting React frontend on http://localhost:5173 ..."
cd "$ROOT/gapquest-react-stl-2"
node node_modules/vite/bin/vite.js &
FRONTEND_PID=$!

echo ""
echo "Both servers running."
echo "  Frontend : http://localhost:5173"
echo "  Backend  : http://localhost:8507"
echo "Press Ctrl+C to stop both."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Servers stopped.'" EXIT INT TERM
wait
