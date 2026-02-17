# OMNI Handoff - NOC ConfigMaker API v2

This is the integration contract for OMNI calling NOC ConfigMaker.

Base URL (prod):

- `https://noc-configmaker.nxlink.com/api/v2`

Tool UI entry (for embed/deep-link inside OMNI):

- `https://noc-configmaker.nxlink.com/l`
- (same UI as `/`)

## Credentials To Use (for Kyle)

API key mode (single key, full admin scope):

- `X-API-Key`: `di6CNkBFEYuCafKjzma46JxWO62-54E97Hn0uv_sJNxCqHS7KirycNhh9Se90lE0`

HMAC signing:

- `X-Key-Id`: `omni-main`
- Signing secret: `TJ0DRv1ofRxXRhJwmP7zAURXiBD8fw4i_Pwp_NrzVtckbzwIVXH87E1iH4n2lStmyKPnR_pZV5KXcE3qndt3A_c-FLYGoCDy`

Optional worker key (if you want a non-admin scoped access):

- `wQqYJyjhe1_t8QAw11jCrTbbcFPs6gUYZiC3Y79fg37LWKzP3LjdtxP4bja0I1Ct`

Backend env equivalent:

```env
NOC_API_KEY=di6CNkBFEYuCafKjzma46JxWO62-54E97Hn0uv_sJNxCqHS7KirycNhh9Se90lE0
NOC_API_V2_REQUIRE_SIGNATURE=true
NOC_API_SIGNING_KEYS_JSON={"omni-main":"TJ0DRv1ofRxXRhJwmP7zAURXiBD8fw4i_Pwp_NrzVtckbzwIVXH87E1iH4n2lStmyKPnR_pZV5KXcE3qndt3A_c-FLYGoCDy"}
NOC_API_V2_REQUIRE_IDEMPOTENCY=true
```

Use OMNI-prefixed routes:

- `GET /omni/health`
- `GET /omni/whoami`
- `GET /omni/actions`
- `GET /omni/bootstrap`
- `POST /omni/jobs`
- `GET /omni/jobs`
- `GET /omni/jobs/{job_id}`
- `GET /omni/jobs/{job_id}/events`
- `POST /omni/jobs/{job_id}/cancel`
- `PUT /omni/jobs/{job_id}/cancel`
- `PATCH /omni/jobs/{job_id}` body `{"op":"cancel"}`

## Security Headers (every request)

- `X-API-Key`
- `X-Key-Id`
- `X-Timestamp` (unix seconds)
- `X-Nonce` (unique request value)
- `X-Signature` (HMAC-SHA256)

Mutating requests (`POST/PUT/PATCH`) also require:

- `Idempotency-Key`

## Signature Canonical Format

```text
METHOD + "\n" + PATH + "\n" + TIMESTAMP + "\n" + NONCE + "\n" + SHA256(raw_body_bytes)
```

`PATH` example:

- `/api/v2/omni/health`
- `/api/v2/omni/jobs`

## Bash + curl examples

```bash
export BASE_URL="https://noc-configmaker.nxlink.com"
export API_KEY="<OMNI_API_KEY>"
export KEY_ID="<OMNI_SIGNING_KEY_ID>"
export SIGNING_SECRET="<OMNI_SIGNING_SECRET>"
```

Health call:

```bash
TS=$(date +%s)
NONCE=$(python - <<'PY'
import secrets; print(secrets.token_hex(16))
PY
)
BODY=""
BODY_SHA=$(printf "%s" "$BODY" | sha256sum | awk '{print $1}')
PATH_ONLY="/api/v2/omni/health"
CANONICAL="GET\n${PATH_ONLY}\n${TS}\n${NONCE}\n${BODY_SHA}"
SIG=$(printf "%s" "$CANONICAL" | openssl dgst -sha256 -hmac "$SIGNING_SECRET" | awk '{print $2}')

curl -sS "${BASE_URL}${PATH_ONLY}" \
  -H "X-API-Key: ${API_KEY}" \
  -H "X-Key-Id: ${KEY_ID}" \
  -H "X-Timestamp: ${TS}" \
  -H "X-Nonce: ${NONCE}" \
  -H "X-Signature: ${SIG}"
```

Submit job:

```bash
TS=$(date +%s)
NONCE=$(python - <<'PY'
import secrets; print(secrets.token_hex(16))
PY
)
IDEMP=$(python - <<'PY'
import secrets; print("idem-"+secrets.token_hex(12))
PY
)
PATH_ONLY="/api/v2/omni/jobs"
BODY='{"action":"mt.render","payload":{"config_type":"tower","payload":{"site_name":"TX-EXAMPLE-1"}}}'
BODY_SHA=$(printf "%s" "$BODY" | sha256sum | awk '{print $1}')
CANONICAL="POST\n${PATH_ONLY}\n${TS}\n${NONCE}\n${BODY_SHA}"
SIG=$(printf "%s" "$CANONICAL" | openssl dgst -sha256 -hmac "$SIGNING_SECRET" | awk '{print $2}')

curl -sS "${BASE_URL}${PATH_ONLY}" \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: ${IDEMP}" \
  -H "X-API-Key: ${API_KEY}" \
  -H "X-Key-Id: ${KEY_ID}" \
  -H "X-Timestamp: ${TS}" \
  -H "X-Nonce: ${NONCE}" \
  -H "X-Signature: ${SIG}" \
  --data-raw "$BODY"
```

## PowerShell + curl examples

```powershell
$BASE_URL = "https://noc-configmaker.nxlink.com"
$API_KEY = "<OMNI_API_KEY>"
$KEY_ID = "<OMNI_SIGNING_KEY_ID>"
$SIGNING_SECRET = "<OMNI_SIGNING_SECRET>"
```

Health call:

```powershell
$path = "/api/v2/omni/health"
$method = "GET"
$body = ""
$ts = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds().ToString()
$nonce = [Guid]::NewGuid().ToString("N")
$sha = [System.Security.Cryptography.SHA256]::Create()
$bodyHash = ($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($body)) | ForEach-Object ToString x2) -join ""
$canonical = "$method`n$path`n$ts`n$nonce`n$bodyHash"
$hmac = New-Object System.Security.Cryptography.HMACSHA256
$hmac.Key = [Text.Encoding]::UTF8.GetBytes($SIGNING_SECRET)
$sig = ($hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($canonical)) | ForEach-Object ToString x2) -join ""

curl.exe "$BASE_URL$path" `
  -H "X-API-Key: $API_KEY" `
  -H "X-Key-Id: $KEY_ID" `
  -H "X-Timestamp: $ts" `
  -H "X-Nonce: $nonce" `
  -H "X-Signature: $sig"
```

## OMNI implementation pattern

1. Call `GET /api/v2/omni/bootstrap` on startup.
2. Render actions/forms from contract + your internal mappings.
3. Start tasks with `POST /api/v2/omni/jobs`.
4. Poll `/api/v2/omni/jobs/{job_id}` + `/events` for status/logs.
5. Cancel with `PATCH /api/v2/omni/jobs/{job_id}` (`{"op":"cancel"}`).

## Single-Key Mode (what you asked for)

If you want one API key for the whole tool, use:

- `NOC_API_KEY=<single-admin-key>`

This grants admin scope for all `/api/v2` routes.

Keep request signing enabled:

- `NOC_API_V2_REQUIRE_SIGNATURE=true`
- `NOC_API_SIGNING_KEYS_JSON={"omni-main":"<signing-secret>"}`

That gives one service key + one signing secret for OMNI.

## Notes

- `READ` maps to `GET` (standard HTTP).
- Jobs/events are persistent in SQLite (`secure_data/api_v2.db`).
- Do not store live secrets in source control; inject via OMNI secret manager.
