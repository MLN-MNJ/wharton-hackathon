# ── Stage 1: Build React frontend ─────────────────────────────────────────
FROM node:20-slim AS frontend
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY gapquest-react-stl-2/package*.json ./
RUN npm ci
COPY gapquest-react-stl-2/ ./
# Download actual GLB files from GitHub Release (bypasses LFS pointer issue)
RUN curl -fL "https://github.com/MLN-MNJ/wharton-hackathon/releases/download/v1.0-assets/demo-resort3.glb" -o public/demo-resort3.glb \
    && curl -fL "https://github.com/MLN-MNJ/wharton-hackathon/releases/download/v1.0-assets/hotel1.glb" -o public/hotel1.glb
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

# React build (includes downloaded GLB assets)
COPY --from=frontend /build/dist ./dist

EXPOSE 8507
CMD sh -c "uvicorn adaptive_review_engine.api_server:app --host 0.0.0.0 --port ${PORT:-8507}"
