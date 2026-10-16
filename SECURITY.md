# Security

Report a suspected vulnerability privately to **wanjarisankalp@gmail.com**. Include the affected commit, reproduction and likely impact. Do not put credentials or private data in public issues.

## Existing controls

- Credentials are read server-side from environment variables or the ignored local `.env`.
- Public HTTP(S) destinations on standard ports are DNS checked; private/reserved addresses and URL credentials are rejected.
- Redirect destinations are checked; authorization headers do not follow a change of host.
- Responses have a size limit; company pages are subject to robots checks and host pacing.
- Viewer data escapes script delimiters and uses text nodes; source links allow HTTP(S) schemes only.
- Raw bytes, source hashes and locators make evidence review possible.

## Known boundaries

URL DNS checks do not pin the connection address; use an egress firewall denying private/reserved networks. DNS resolution and output validation are not hard-bounded by the HTTP deadline. Cross-domain redirects need a destination-specific robots review, and crawl delays above ten seconds are currently shortened in `fetch_robots`.

Website identity matching has known false-positive paths, including group/parent attribution and conflicting JSON-LD identifiers. A valid hash proves the bytes were retained, not that they support a claim. See the current audit before using results for decisions.

The pre-push credential check found no configured private credential values in the candidate files. This is a scoped scan, not a guarantee that every historical byte is free of every possible secret. The NAV public token is a published service token, distinct from private account credentials.

Code is MIT licensed. Third-party source content is not automatically covered by that licence; review redistribution rights before further public hosting of retained snapshots.
