# Changelog

## Final release polish

- Renamed the product to **Lead Gen** across frontend, backend, exports, docs and deployment files.
- Added the supplied Lead Gen logo to the sidebar, authentication screens and browser/app icons.
- Added favicon, Apple touch icon and web-app manifest assets.
- Made the default Render Blueprint zero-cost: free Static Site + one free Web Service.
- Added embedded lead/outreach workers for the free single-service deployment.
- Added active-session health keepalive while the browser is open.
- Added automatic GET retry for transient 502/503/504 API failures.
- Reduced authenticated-user sync from two Turso round trips to one upsert-with-returning query.
- Added API GZip responses and security headers.
- Added a Quick Send per-user rate limit.
- Increased user access-cache default to reduce repeated Turso lookups.
- Improved sidebar, top bar, login experience, card styling, form focus states, table headers, scrolling and motion.
- Made the default Find Leads form start clean rather than prefilled with demo data.
- Added free deployment and final release documentation.
