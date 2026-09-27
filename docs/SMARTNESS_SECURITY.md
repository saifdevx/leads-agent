# Smartness & Security Strategy

Lead Gen should handle imperfect data in this order:

1. existing structured fields,
2. deterministic repair,
3. public website/search evidence,
4. enrichment provider,
5. AI only when ambiguity remains.

This minimizes AI cost and hallucination risk.

## Deterministic repairs

Safe:
- company from business email domain,
- company from business-like Gmail username,
- company from social handle,
- domain from website/work email,
- location from lead-list context,
- invalid phone removal.

Unsafe:
- inventing a decision-maker,
- guessing an email and calling it verified,
- inventing a company from `info@gmail.com`,
- claiming a location without evidence.

## Security controls already in Lead Gen

- Firebase ID-token verification on the backend
- per-user database scoping
- encrypted BYOK credentials
- production CORS allowlist
- sanitized HTML email
- Quick Send rate limiting
- campaign approval
- suppression/unsubscribe
- upload size limits
- crawler SSRF protection: private and non-global IPs are rejected
- redirect destinations are revalidated
- production security headers

This update additionally tells browsers/proxies not to cache authenticated `/api/v1/*` data.

## Before broad public SaaS use

Recommended future hardening:
- signup CAPTCHA / abuse controls
- monthly per-user provider quotas
- provider-spend ceilings
- CI secret/dependency scanning
- webhook replay/idempotency ledger
- database backup policy
- organization/workspace authorization tests
- production alerting for provider/mail/webhook failures
