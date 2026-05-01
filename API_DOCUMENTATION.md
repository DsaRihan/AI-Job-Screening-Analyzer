# API Documentation

This is a compact API reference for Phase 1 services.

## Authentication

- Method: Firebase ID token
- How: Frontend obtains an ID token from Firebase client SDK and sends it in the `Authorization` header as `Bearer <idToken>` for protected endpoints.

## Base URLs

- Backend (Docker): `localhost:5000`
- Backend (local python): `localhost:8000` (if running `start.sh` locally adjust `PORT`)
- Frontend (Docker): `localhost:8080` (nginx runtime)
- Frontend (dev): `localhost:5173` (Vite dev server — may be stopped when testing Docker builds)

Note: The project reads `MONGO_URI` from `./.env` (or CI secrets). If `MONGO_URI` points to an Atlas cluster (`mongodb+srv://...`), the Dockerized backend will use Atlas and all writes (history, users) will be stored there and visible across instances.

## Endpoints

### GET `/auth/me`

- Description: Return authenticated user metadata and assigned role.
- Auth: Required (Firebase token)
- Example:

  ```bash
  curl -H "Authorization: Bearer <ID_TOKEN>" http://localhost:5000/auth/me
  ```

### POST `/auth/post-login`

- Description: Called after frontend login to persist or update user info, triggers welcome email.
- Body: `{ "uid": "<firebase-uid>", "email": "..." }` (frontend handles payload)
- Example:

  ```bash
  curl -X POST -H "Authorization: Bearer <ID_TOKEN>" -H "Content-Type: application/json" -d '{"uid":"abc","email":"a@b.com"}' http://localhost:5000/auth/post-login
  ```

### GET `/history`

- Description: Returns user's analysis history (most recent first).
- Auth: Required
- Query params: `limit` (optional)
- Example:

  ```bash
  curl -H "Authorization: Bearer <ID_TOKEN>" http://localhost:5000/history
  ```

### POST `/analyze`

- Description: Submit a resume + job description for analysis. Depending on config, analysis may run synchronously or enqueue a Celery task.
- Body (example):

  ```json
  {
    "resumeText": "...",
    "jobDescription": "...",
    "options": { "mode": "full" }
  }
  ```

- Example:

  ```bash
  curl -X POST -H "Authorization: Bearer <ID_TOKEN>" -H "Content-Type: application/json" -d @payload.json http://localhost:5000/analyze
  ```

### GET `/coaching/progress` and `/coaching/study-pack`

- Description: Coaching related endpoints; return curated progress and study material for a user.
- Auth: Required

## Task queue (Celery)

- Broker: Redis (default `redis://redis:6379/0` inside Docker)
- Common tasks registered: `estimate_salary`, `tailor_resume`, `generate_career_path`, `run_analysis` (worker logs list tasks during startup)

## Error codes

- 401 Unauthorized — missing or invalid Firebase ID token.
- 200 OK — successful requests.
- 500 Internal Server Error — check backend logs for details.

## Mongo configuration

- The service uses the `MONGO_URI` environment variable. When running with `docker compose` the compose file reads from `./.env` (via `env_file`) and forwards it to the backend/worker.
- If `MONGO_URI` is set to an Atlas URI (`mongodb+srv://...`) the backend will connect to Atlas (tls enabled). If set to a local container (`mongodb://mongo:27017/...`) it will connect to the local Mongo instance.
- Changing `MONGO_URI` controls where `POST /analyze` and `/auth/post-login` store history and user records.

## Firebase configuration

- Frontend: At build time the frontend receives `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_AUTH_DOMAIN`, `VITE_FIREBASE_PROJECT_ID`, etc. via build args (populated from `./.env`). Ensure these `VITE_` variables are present in `.env` before building the Docker frontend image.
- Backend: The backend needs a Firebase service account JSON to perform server-side operations. Provide the path via `FIREBASE_CREDENTIAL_PATH` (default in container: `/app/backend/firebase-service-account.json`). Do NOT commit this JSON to git; keep it out of source control and mount it or pass as a secret in CI.

## Testing Atlas connectivity

To test Atlas connectivity from your local Docker environment, set `MONGO_URI` in `./.env` to your Atlas URI and run:

```bash
docker compose up -d --build
```

Once the stack is running you can verify by saving a test role in the backend container:

```bash
docker compose exec -T backend python - <<'PY'
from backend.mongo_db import save_user_role, get_user_role_mongo
print(save_user_role('atlas-integration-test', 'candidate'))
print(get_user_role_mongo('atlas-integration-test'))
PY
```

If the writes appear in Atlas, your `docker-compose` is correctly pointing at Atlas.
