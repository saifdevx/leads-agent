# Performance Architecture

This bundle targets the latency problems observed during local development, especially actions/pages that previously waited on several Turso network round trips.

## Improvements included

### 1. Persistent Turso HTTP client

Before:

```text
DB query → new HTTP client/TLS connection
DB query → new HTTP client/TLS connection
DB query → new HTTP client/TLS connection
```

Now:

```text
FastAPI process
    ↓
long-lived httpx.Client
    ↓
keep-alive connection pool
    ↓
Turso
```

This reduces connection setup overhead and allows HTTP/2/keep-alive reuse.

### 2. My Leads snapshot

Before the page needed separate remote requests for lead lists and lead rows.

Now:

```text
GET /api/v1/leads/snapshot
    ↓
one Turso pipeline request
    ├── lead lists
    └── lead rows
```

### 3. Outreach snapshot

Instead of loading templates, senders, campaigns and replies using four separate Turso calls:

```text
GET /api/v1/outreach/snapshot
    ↓
one Turso pipeline request
    ├── templates
    ├── senders
    ├── campaigns
    └── replies
```

### 4. Frontend request deduplication

If two components/React StrictMode request the same authenticated GET at the same time, the frontend now reuses the same active Promise rather than creating duplicate API requests.

### 5. Short-lived caches

Read-heavy data uses short TTLs. Mutations invalidate the related cache.

The database remains the source of truth.

### 6. Optimistic mutations

Pause/resume/cancel/delete and similar user actions can update the UI immediately and reconcile with the backend result. On failure, the UI restores the previous state and displays the error.

### 7. User access-state cache

User role/status checks are cached server-side for a short period to avoid a Turso lookup on every authenticated endpoint call.

Admin suspension invalidates that user's cache immediately. The cache TTL is configurable with:

```env
USER_ACCESS_CACHE_SECONDS=30
```

### 8. Durable production workers

Automated lead search/enrichment no longer need to execute inside the API process in production.

```text
API creates job
    ↓
Turso jobs table
    ↓
lead worker claims job
    ↓
processes discovery/enrichment
```

This improves web-request reliability and makes long work independent of the user's browser/API request lifecycle.

## Why some actions can still take time

Turso is a remote database. A forced refresh must still travel over the network. Provider APIs and external websites can also be slow.

The UI should therefore distinguish:
- immediate local interaction feedback
- background server confirmation
- external provider completion

## Bundle 3 performance work

The final polish pass can add profiling-driven improvements if real production measurements still show bottlenecks, such as:
- endpoint timing dashboard
- pagination/virtualization for very large lead tables
- narrower response payloads
- provider request concurrency limits
- server response compression where useful
- additional read caching for stable configuration

Avoid adding Redis or another infrastructure service until production measurements prove it is necessary.
