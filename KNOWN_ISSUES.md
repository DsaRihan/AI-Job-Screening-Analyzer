# Known Issues & Limitations (Phase 1)

This file records non-critical issues discovered during Phase 1 that should be addressed in Phase 2.


## Firebase configuration discovery

- Symptom: Frontend shows "Email login is not configured".
- Cause: Vite build did not receive `VITE_FIREBASE_*` env vars or backend couldn't find `firebase-service-account.json` inside container.
- Mitigation: Ensure `VITE_FIREBASE_*` are set in root `.env`, frontend build args in `docker-compose.yml` forward them, and `backend/.dockerignore` does not exclude the JSON file.

## Mongo SSL handshake for local Mongo

- Symptom: `MongoDB connection failed: SSL handshake failed: mongo:27017: [SSL: UNEXPECTED_EOF_WHILE_READING]` in backend logs.
- Cause: `pymongo` was always passed a `tlsCAFile` (certifi) which triggers SSL handshake against local non-TLS server.
- Mitigation: Only enable `tlsCAFile` when `MONGO_URI` indicates Atlas or `tls=true`.

## Local vs Atlas DB mismatch

- Symptom: Records created via Dockerized backend do not appear in Atlas.
- Cause: Docker Compose passed `MONGO_URI` pointing to local `mongo` container while `.env` may contain Atlas URI.
- Mitigation: Decide whether Docker should use Atlas or local Mongo; update `docker-compose.yml` to use `${MONGO_URI}` from `env_file: ./.env` when you want Atlas.

## Frontend dev server vs Dockerized frontend port conflict

- Symptom: Opening `localhost:5173` shows Vite dev; Docker frontend is on `:8080`.
- Mitigation: Stop local dev server when testing Docker build or use proper `VITE_API_BASE_URL`.

## Docker build cache hides updated build args

- Symptom: New Vite build args not reflected after adjusting `docker-compose.yml`.
- Mitigation: Rebuild without cache: `docker builder prune -af && docker compose up --build -d` or `docker compose build --no-cache frontend`.

## Shell heredoc tests hang in some run contexts

- Symptom: Automated curl/heredoc tests got stuck (shell heredoc parsing issues in some terminal automation).
- Mitigation: Use single-line curl or here-strings or run scripts explicitly in a terminal. Avoid interactive heredocs in CI automation.

## Secrets handling

- Symptom: Firebase keys and other credentials present locally.
- Mitigation: Keep them in `.env` (gitignored). Use repo secrets for CI and Docker secrets or provider-managed secrets for production.
