# Changelog

## Admin, production deployment & performance update

### Admin / operations
- Added an admin-only application area with Overview, Users, Jobs and System tabs.
- Added configurable admin bootstrap through `ADMIN_EMAILS`.
- Added user suspension/reactivation with server-side enforcement.
- Added admin job inspection and retry controls.
- Added provider connection health, worker heartbeat status and Hostinger webhook status.
- Added admin audit logging for high-impact admin actions.

### Durable background processing
- Added a dedicated lead/discovery worker for automated lead searches and enrichment jobs.
- Production API can run with `BACKGROUND_JOBS_MODE=worker` so long discovery/enrichment work is not tied to a web request.
- Added database-backed job claiming, worker locks, stale-job release and worker heartbeats.
- Outreach worker now publishes health heartbeats as well.

### Performance
- Turso SQL-over-HTTP now reuses one long-lived `httpx.Client` with keep-alive connection pooling instead of opening a new HTTP client for every database request.
- Added `/api/v1/leads/snapshot` so lead lists + lead rows load through one Turso pipeline request.
- Added `/api/v1/outreach/snapshot` so templates + senders + campaigns + replies load through one Turso pipeline request.
- My Leads and Outreach now use the snapshot endpoints.
- Added frontend in-flight GET deduplication to prevent duplicate concurrent requests (including React StrictMode duplicate loads).
- Provider lists and operational data use short-lived cache entries with mutation invalidation.
- Preserved optimistic pause/resume/cancel/delete behavior from the previous bundle.
- Added a short-lived server-side user access cache so authenticated API calls do not need a Turso user-state lookup every time.

### Production deployment
- Added a Render Blueprint for:
  - static React frontend
  - paid FastAPI web service
  - lead/discovery worker
  - outreach/email worker
- Added pre-deploy database migrations for the API service.
- Added immutable static-asset cache headers and baseline security headers.
- Added production environment variables for Firebase, Turso, admin access, CORS, provider encryption and public webhook URL.
- Added `render-low-cost.yaml` for early deployment using only API + outreach worker, while retaining `render.yaml` as the recommended fully durable profile.
- Hostinger sender UI can enable the real-time reply webhook once `PUBLIC_API_URL` is configured.

### Database
- Added migration `004_admin_operations`:
  - `users.role`
  - job worker lock fields
  - sender webhook status/url
  - worker heartbeat table
  - admin audit table
