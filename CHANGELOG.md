# Changelog

## 0.1.1 — Windows frontend install hotfix

### Fixed
- Hardened Windows installs against npm optional-dependency omission for Rolldown.
- Explicitly pins `rolldown` 1.2.8 for Vite 8.3.x compatibility.
- Adds the Windows x64 Rolldown native binding as an optional dependency.
- Adds `.npmrc` with optional dependencies explicitly enabled.
- Render frontend install now explicitly includes optional dependencies.

### Preserved
- No application UI code changed.
- No backend code changed.
- No API contract changed.
- No database/authentication changes.

## 0.1.0 — Checkpoint 1 Foundation

### Added
- React/Vite/TypeScript application shell
- Tailwind CSS v4 design integration
- Locked brand tokens and typography
- Simplified 4-item user navigation
- Responsive desktop/mobile layout
- Find Leads interaction shell
- My Leads, Outreach and Settings prepared states
- FastAPI application foundation
- Structured health endpoint
- Request ID middleware
- Structured error response baseline
- JSON logging baseline
- Frontend API health status
- Backend health tests
- Frontend API-client tests
- Render deployment blueprint
- Environment templates
- Setup, testing and rollback documentation

### Not yet added
- Authentication
- Database
- Lead search/enrichment
- AI
- Email sending
