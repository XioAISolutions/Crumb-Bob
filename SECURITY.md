# Security Policy

## Supported versions

| Version | Status      | Security patches |
| ------- | ----------- | ---------------- |
| 0.3.x   | Current     | ✅ Yes           |
| 0.2.x   | End of life | ❌ No            |
| < 0.2   | Unsupported | ❌ No            |

When v0.4 ships, v0.3 will receive security fixes for ~3 months
before being retired. We do not backport features.

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Email **security@xioaisolutions.com** with:

1. A description of the issue and its impact.
2. Steps to reproduce (or a proof-of-concept).
3. Affected CrumbBob versions and any relevant environment details
   (Python version, OS, deployment topology).
4. Your name/handle for credit (optional).

We acknowledge reports within **2 business days** and aim to ship a
patched release within **14 days** for high-severity issues. For
critical issues (RCE, auth bypass) we will coordinate an embargo
window with the reporter and CVE assignment via GitHub's CNA.

Encrypted communication: PGP key fingerprint available on request.

## Threat model

CrumbBob is **not** a multi-tenant SaaS. The intended deployment
topologies are:

1. **Single-developer CLI** — runs as the user on their workstation.
   Trust boundary is the workstation; no network exposure.
2. **Single-node web dashboard** — `crumdbob serve` bound to
   `127.0.0.1`. Trust boundary is the workstation; access controlled
   by OS user permissions.
3. **Team dashboard behind a TLS proxy** — `crumdbob serve` running
   inside Docker behind nginx/Caddy/Traefik with TLS termination,
   `CRUMDBOB_API_KEY` set, accessed by trusted developers. Trust
   boundary is the proxy; access controlled by the API key plus the
   proxy's auth (mTLS, OIDC, whatever your org runs).

Out of scope:

- **Multi-tenant isolation.** A single CrumbBob instance assumes all
  users share the same trust level. Run separate instances if you
  need tenant isolation.
- **Untrusted CRUMB packs.** The validator and importer assume packs
  were produced by a trusted IBM Bob session. We refuse the obvious
  abuses (path traversal in `proof_chain`, multi-statement SQL in
  `query sql`) but do not promise full safety against an adversarial
  pack constructor.
- **DoS from authenticated clients.** Rate limiting protects against
  a single misbehaving client; a coordinated attack from N
  authenticated clients each under the limit will degrade the
  service. Mitigate at the proxy.

## Hardening guide

### Local development (default)

No action required. The defaults are safe:

- API binds to localhost only (`--host 127.0.0.1`).
- No authentication required (workstation isolation is the trust boundary).
- Rate limits are conservative (10 req/s sustained).
- CORS regex matches only `localhost`/`127.0.0.1`.

### Team / network deployment

1. **Enable API-key auth.** Set `CRUMDBOB_API_KEY` to a random
   32+ character value. Generate with:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

   Distribute via your secret manager (1Password, Vault, AWS Secrets
   Manager). Never commit the value.

2. **Terminate TLS at a proxy.** CrumbBob speaks plain HTTP. Front it
   with nginx, Caddy, Traefik, or a cloud load balancer.

3. **Tighten the CSP.** The default CSP allows inline scripts because
   the legacy dashboard ships them. If you don't use the dashboard
   (API-only deploys), set:

   ```
   CRUMDBOB_CSP="default-src 'none'; frame-ancestors 'none'"
   ```

   _Note: this env var is read in v0.4; for now, edit the middleware
   directly or override at the proxy._

4. **Enable HSTS** when serving over HTTPS:

   ```
   CRUMDBOB_ENABLE_HSTS=1
   ```

5. **Scrape `/metrics`** with Prometheus to alert on auth-failure
   bursts, rate-limit denials, and error rates.

6. **Review the audit log.** Query the `audit_log` table for
   security-relevant events:
   ```sql
   SELECT ts, event, actor, request_id, payload
   FROM audit_log
   WHERE event LIKE 'auth.%' OR event = 'rate.limited'
   ORDER BY ts DESC
   LIMIT 100;
   ```

### Container deployment

The shipped `Dockerfile` already applies:

- Non-root user (UID 10001).
- Read-only root filesystem (writable `/data` volume).
- All Linux capabilities dropped.
- `no-new-privileges` set.
- Healthcheck wired to `/api/health`.

Verify with:

```bash
docker run --rm crumdbob:latest id
# → uid=10001(crumdbob) gid=10001(crumdbob) groups=10001(crumdbob)
```

## Known limitations

- **In-process rate limiting.** Behind a load balancer with multiple
  CrumbBob replicas, rate limits are per-replica, not per-cluster.
  For shared-state limiting, you'd need to swap in a Redis-backed
  bucket store — not currently provided.
- **No CSRF tokens.** The dashboard uses no cookies and the API does
  not accept credentials by default (CORS `allow_credentials=False`).
  This means there's no CSRF vector — but it also means you can't
  put the API behind a cookie-auth SSO. If you need cookie auth,
  add a CSRF middleware before doing so.
- **SQLite single-writer.** All write traffic to the audit/memory
  database serializes on one writer. WAL mode helps but high write
  volume (>~100 writes/sec) will queue. Migrate to PostgreSQL if you
  need higher throughput.

## Security audits

- Internal review: 2026-05-15 (XSS hardening, error sanitization,
  rate limiting, audit logging added in v0.3.1).
- External pentest: not yet commissioned. Submission gated on v1.0.

## CVE history

None to date. Reports filed here will be backfilled.
