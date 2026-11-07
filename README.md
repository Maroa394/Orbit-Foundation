# ORBIT Foundation — developer preview

ORBIT (Organisational Risk & Business Intelligence Technology) is a multi-organisation operations intelligence platform foundation.

## Included in this build
- Organisation registration and sign-in
- Password hashing and signed access tokens
- Organisation-scoped data queries
- Roles: owner, admin, manager, member, auditor (role checks on privileged routes)
- Departments
- FollowUp tasks
- Risk register with 1–25 likelihood × impact score
- Watch events and acknowledgement
- Evidence metadata catalogue (not file storage)
- Approval requests and decisions
- Audit log
- Responsive browser UI
- SQLite local development and PostgreSQL Docker configuration

## Run locally
Requires Python 3.11+.

1. Copy `.env.example` to `.env`.
2. Change `SECRET_KEY` to a long random value.
3. Install dependencies: `pip install -r requirements.txt`
4. Start: `uvicorn app.main:app --reload`
5. Open `http://127.0.0.1:8000`
6. API documentation: `http://127.0.0.1:8000/docs`

The first person to register creates an organisation and becomes its owner.

## Run with Docker
1. Install Docker on a computer/server.
2. Change both database password and SECRET_KEY in `docker-compose.yml`.
3. Run `docker compose up --build`.
4. Visit `http://localhost:8000`.

## Important limitations — not production-ready yet
This is a foundation build, not a certified enterprise service. Before real organisations use it:
- Move secrets to a managed secret store and rotate them.
- Use HTTPS, secure cookie/token lifecycle, MFA and account recovery.
- Add invitation flows, membership administration and fine-grained permissions.
- Add PostgreSQL row-level security policies and automated tenant-isolation tests.
- Add rate limiting, brute-force protection, CSRF strategy for cookie auth, security headers and dependency scanning.
- Add backups, restore drills, monitoring, alerting and incident response.
- Add migrations (Alembic) instead of relying on create_all.
- Add file storage with malware scanning and per-tenant access controls; evidence currently stores references/metadata only.
- Add notification delivery and integrations only after OAuth/token vaulting and webhook verification are designed.
- Conduct independent security and privacy review before handling sensitive business data.
- Verify local data retention, privacy notices and applicable laws for each deployment region.

## Architecture
FastAPI API + SQLAlchemy data layer + SQLite for local testing / PostgreSQL for hosted deployment. Every operational table has an organisation_id, and API list/detail/update queries are scoped to the authenticated user's organisation. This application-level scoping must be reinforced with PostgreSQL RLS before production.
