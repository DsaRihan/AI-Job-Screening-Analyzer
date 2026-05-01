# Development Guide

This document explains how to set up and run the project locally (dev and Docker), the environment variables, common issues and how to run tests.

## Prerequisites

- Git
- Docker & Docker Compose (v2+) for containerized run
- Node.js 20+ and npm (for local frontend dev)
- Python 3.12 and virtualenv (for local backend dev)
- MongoDB tools (optional) if you plan to import/export DBs: `mongodump`/`mongorestore` or `mongosh`

## Quick repo layout

- `backend/` — Flask API, Celery tasks, Mongo integration
- `frontend/` — Vite + React app
- `docker-compose.yml` — local dev stack (backend, worker, frontend, redis, mongo)

## Local setup

### Backend (local virtualenv)

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
```

### Frontend (local dev server)

```bash
cd frontend
npm install
npm run dev
```

Frontend dev server runs on `localhost:5173` by default.

## Docker setup (full stack)

1. Create a root `.env` (project root) with real credentials (see table below).
2. Ensure `backend/firebase-service-account.json` exists and is not excluded by `backend/.dockerignore`.
3. Start services:

   ```bash
   docker compose up -d --build
   ```

4. Access frontend: `localhost:8080` (nginx in Docker). Backend: `localhost:5000`.

## Environment variables

| Variable | Required | Description | Default/Notes |
| --- | --- | --- | --- |
| `MONGO_URI` | yes | Mongo connection string. Use Atlas `mongodb+srv://...` or local `mongodb://mongo:27017/resumeAnalyzer` | set in `.env` |
| `REDIS_URL` | yes | Celery broker URL | `redis://redis:6379/0` (docker) |
| `DEV_BYPASS_AUTH` | no | When `1` disables auth checks for dev | `0` for real auth |
| `FIREBASE_CREDENTIAL_PATH` | yes | Path to service account JSON inside container | `/app/backend/firebase-service-account.json` |
| `VITE_FIREBASE_API_KEY` | yes | Web app Firebase key used by Vite build | set in root `.env` |
| `COHERE_API_KEY` | depends | LLM provider key used in backend | set actual key |
| `OPENAI_API_KEY` | depends | LLM provider key used in backend | set actual key |

## Common issues

### Firebase "Email login is not configured"

**Cause:** frontend build lacked Vite Firebase env vars or backend couldn't find service account.

**Fix:** ensure `VITE_FIREBASE_*` present in root `.env` and `FIREBASE_CREDENTIAL_PATH` points to `/app/backend/firebase-service-account.json` and the JSON file is not excluded by `backend/.dockerignore`.

### Frontend appears at `:5173` instead of `:8080`

**Cause:** local Vite dev server is running.

**Fix:** Stop local server to reach Dockerized frontend on `:8080`.

### Mongo SSL handshake errors with local Docker Mongo

**Cause:** code forced TLS (certifi).

**Fix:** code now only enables `tlsCAFile` when URI indicates Atlas (`mongodb+srv://` or `tls=true`).

### Docker using local Mongo instead of Atlas

**Cause:** `docker-compose.yml` was passing `mongodb://mongo:27017` as `MONGO_URI`.

**Fix:** set `MONGO_URI` in root `.env` to Atlas URI and ensure `docker-compose.yml` uses `${MONGO_URI}` or `env_file: ./.env`.

### Docker build caching prevents new env args

**Fix:** rebuild with cache cleared:

```bash
docker builder prune -af && docker compose up --build -d
```

## Running tests

### Backend unit tests

```bash
.venv/bin/activate
pytest tests/ -q
```

### Frontend tests

```bash
cd frontend
npm test
```

### CI pipeline

`.github/workflows/ci.yml` runs backend tests and frontend build on push/pull requests.

## Developer tips

- When switching between local dev server and Docker frontend, stop one to avoid port conflicts.
- Keep secrets out of Git – use `.env` ignored by git; rotate keys if accidentally exposed.
- Use named Docker volumes to persist DB data; `docker compose down -v` will remove them.

If anything here doesn't work, paste the failing command output and I'll help troubleshoot.
