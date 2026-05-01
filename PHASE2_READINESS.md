# Phase 2 Readiness Checklist

This checklist captures the recommended tasks to prepare the project for Phase 2 development and staging readiness.

## Priority (High)

- [ ] Decide DB strategy: point Docker backend to Atlas or migrate Atlas data to local Mongo for reproducible testing.
- [ ] Move all production credentials out of local files into provider-managed secrets (GitHub Secrets / Docker secrets / Vault).
- [ ] Add integration tests for upload → analysis → storage (end-to-end smoke tests).
- [ ] Harden auth: verify Firebase client config in frontend and server-side token verification in backend.

## Priority (Medium)

- [ ] Add health-check endpoints and readiness probes for backend, worker, and frontend.
- [ ] Add backup/export strategy for Mongo (periodic dumps or managed backups if Atlas used).
- [ ] Add Docker image scanning (Snyk/Trivy) in CI and a pre-push secret scan.
- [ ] Fix markdown lint warnings and CI docs checklist.

## Priority (Low)

- [ ] Create `KNOWN_ISSUES.md` (completed) and wire it into developer onboarding.
- [ ] Document DB migration steps and provide a script to import/export sample dataset.

## Acceptance Criteria for Phase 2 kickoff

- All high priority items completed or scheduled with owners.
- CI pipeline runs on PRs and passes lint, tests, and image scans.
- A reproducible staging environment can be spun up with `docker compose up --build` using documented `.env.example` (no secrets included).
