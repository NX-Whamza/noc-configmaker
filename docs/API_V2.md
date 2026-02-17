# NOC ConfigMaker API v2

`/api/v2` is the contract-first integration layer for OMNI/Mushu and any external frontend.

## Authentication

All endpoints require API key auth.

- Header: `X-API-Key: <key>`
- Or: `Authorization: Bearer <key>`

Configure keys with one of:

- `NOC_API_KEYS_JSON`:
  - `{"admin-key":["admin"],"ro-key":["health.read","actions.read","job.read"]}`
- `NOC_API_KEYS`:
  - `admin-key:admin;ro-key:health.read,actions.read,job.read`
- `NOC_API_KEY`:
  - single admin key

If no keys are configured, `/api/v2` returns `503`.

## Request Signing (HMAC)

By default, v2 also requires signed requests (`NOC_API_V2_REQUIRE_SIGNATURE=true`).

Headers required on every request:

- `X-Key-Id`: signing key id
- `X-Timestamp`: unix epoch seconds
- `X-Nonce`: random unique value per request
- `X-Signature`: hex HMAC-SHA256

Canonical string:

```text
{METHOD}\n{PATH}\n{TIMESTAMP}\n{NONCE}\n{SHA256_HEX_OF_RAW_BODY}
```

Signature:

```text
hex(hmac_sha256(signing_secret, canonical_string))
```

Signing key env:

- `NOC_API_SIGNING_KEYS_JSON`
- `NOC_API_SIGNING_KEYS`

Replay protection:

- nonce store with TTL (`NOC_API_V2_NONCE_TTL_SECONDS`)
- timestamp skew check (`NOC_API_V2_SIGNATURE_SKEW_SECONDS`)

## Scopes

- `admin`: bypass scope checks
- `health.read`
- `actions.read`
- `job.submit`
- `job.read`
- `job.cancel`

## Endpoints

- `GET /api/v2/health` (`health.read`)
  - backend health summary (`legacy_health`, `ido_caps`)
- `GET /api/v2/omni/health` (`health.read`)
  - OMNI alias of health
- `GET /api/v2/actions` (`actions.read`)
  - list of supported actions
- `GET /api/v2/omni/actions` (`actions.read`)
  - OMNI alias of actions
- `GET /api/v2/whoami` (`health.read`)
  - key identity/scopes
- `GET /api/v2/omni/whoami` (`health.read`)
  - OMNI alias of whoami
- `GET /api/v2/omni/bootstrap` (`actions.read`)
  - contract endpoint for OMNI integration
- `POST /api/v2/jobs` (`job.submit`)
  - submit async action job
- `POST /api/v2/omni/jobs` (`job.submit`)
  - OMNI alias of submit job
- `GET /api/v2/jobs` (`job.read`)
  - list jobs
- `GET /api/v2/omni/jobs` (`job.read`)
  - OMNI alias of list jobs
- `GET /api/v2/jobs/{job_id}` (`job.read`)
  - job details/result
- `GET /api/v2/omni/jobs/{job_id}` (`job.read`)
  - OMNI alias of job details
- `GET /api/v2/jobs/{job_id}/events` (`job.read`)
  - streaming-friendly event list
- `GET /api/v2/omni/jobs/{job_id}/events` (`job.read`)
  - OMNI alias of job events
- `POST /api/v2/jobs/{job_id}/cancel` (`job.cancel`)
  - request cancellation
- `POST /api/v2/omni/jobs/{job_id}/cancel` (`job.cancel`)
- `PUT /api/v2/jobs/{job_id}/cancel` (`job.cancel`)
- `PUT /api/v2/omni/jobs/{job_id}/cancel` (`job.cancel`)
- `PATCH /api/v2/jobs/{job_id}` (`job.cancel`) body `{"op":"cancel"}`
- `PATCH /api/v2/omni/jobs/{job_id}` (`job.cancel`) body `{"op":"cancel"}`

## Job Request Format

```json
{
  "action": "mt.render",
  "payload": {
    "config_type": "tower",
    "payload": {
      "...": "..."
    }
  }
}
```

`payload` is action-specific.

## Idempotency

Mutating endpoints (`POST /jobs`, `POST /jobs/{job_id}/cancel`) require:

- `Idempotency-Key` (when `NOC_API_V2_REQUIRE_IDEMPOTENCY=true`)

Behavior:

- same key + same request body => returns original response
- same key + different body => `409`
- retention controlled by `NOC_API_V2_IDEMPOTENCY_TTL_SECONDS`

## Built-in Actions

- `mt.render`
- `mt.config`
- `mt.portmap`
- `legacy.proxy` (restricted to `/api/*`, blocks `/api/v2/*`)
- `activity.list`
- `configs.list`
- `aviat.activate_scheduled`
- `aviat.check_status`

## Notes

- Jobs are persisted in SQLite (`secure_data/api_v2.db`) and survive restart.
- Job events are capped (latest 500 per job).
- OpenAPI/Swagger docs are available from FastAPI runtime (`/docs`, `/openapi.json`).

## OMNI Endpoints To Call

Primary integration endpoints (use OMNI-prefixed routes):

- `GET /api/v2/omni/health`
- `GET /api/v2/omni/whoami`
- `GET /api/v2/omni/actions`
- `GET /api/v2/omni/bootstrap`
- `POST /api/v2/omni/jobs`
- `GET /api/v2/omni/jobs`
- `GET /api/v2/omni/jobs/{job_id}`
- `GET /api/v2/omni/jobs/{job_id}/events`
- `POST /api/v2/omni/jobs/{job_id}/cancel`
- `PUT /api/v2/omni/jobs/{job_id}/cancel`
- `PATCH /api/v2/omni/jobs/{job_id}` with body `{"op":"cancel"}`

Recommended OMNI pattern:

1. Submit task to `/api/v2/omni/jobs`
2. Poll `/api/v2/omni/jobs/{job_id}` for state
3. Poll `/api/v2/omni/jobs/{job_id}/events` for progress log

Production examples:

- `GET https://noc-configmaker.nxlink.com/api/v2/omni/health`
- `GET https://noc-configmaker.nxlink.com/api/v2/omni/bootstrap`

`READ` is not an HTTP verb; use `GET` for read operations.

UI deep-link for OMNI embed/navigation:

- `https://noc-configmaker.nxlink.com/l`

## Login / Identity

- Service-to-service auth for OMNI/Mushu uses API keys + request signing (no username/password login required).
- Human UI login remains on legacy endpoint:
  - `POST /api/auth/login`

## Single API Key Option

If you prefer one secret for all API access, set:

- `NOC_API_KEY=<single-admin-key>`

This enables full admin scope on `/api/v2`.

## Key Generation

Generate strong keys in PowerShell:

```powershell
python - <<'PY'
import secrets, json
print("API key:", secrets.token_urlsafe(40))
print("Signing key id: omni-main")
print("Signing secret:", secrets.token_urlsafe(64))
PY
```
