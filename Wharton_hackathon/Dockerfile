# ── Stage 1: Build React frontend (with LFS) ──────────────────────────────
FROM node:20-slim AS frontend
RUN apt-get update && apt-get install -y git git-lfs && rm -rf /var/lib/apt/lists/*
RUN git lfs install
WORKDIR /build
RUN git clone https://github.com/MLN-MNJ/wharton-hackathon.git .
WORKDIR /build/Wharton_hackathon/gapquest-react-stl-2
RUN npm ci
RUN npm run build

# ── Stage 2: Python API + static server ───────────────────────────────────
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Backend source + data
COPY adaptive_review_engine/ ./adaptive_review_engine/
COPY gamified_responses.json bounties_db.json final_map_db.json \
     new_bounties_db.json physical_landmarks_db.json ./

# React build (includes GLB/STL assets from public/)
COPY --from=frontend /build/Wharton_hackathon/gapquest-react-stl-2/dist ./dist

EXPOSE 8507
CMD sh -c "uvicorn adaptive_review_engine.api_server:app --host 0.0.0.0 --port ${PORT:-8507}"
