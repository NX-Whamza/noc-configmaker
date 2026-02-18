# NOC ConfigMaker API v2

This is the production contract for OMNI and other API clients.
Everything below uses exact request/response JSON shapes with no abbreviated payloads.

## Base URL

- API: `https://noc-configmaker.nxlink.com/api/v2`
- OMNI aliases: `https://noc-configmaker.nxlink.com/api/v2/omni/*`
- UI: `https://noc-configmaker.nxlink.com/l`

## Authentication

API key auth is required for every `/api/v2/*` request.

Accepted headers:

- `X-API-Key: <OMNI_API_KEY>`
- `Authorization: Bearer <OMNI_API_KEY>`

Recommended OMNI profile:

- `NOC_API_V2_REQUIRE_SIGNATURE=false`
- `NOC_API_V2_REQUIRE_IDEMPOTENCY=true`
- `NOC_API_KEYS_JSON` or `NOC_API_KEYS` configured

Example key config:

- `NOC_API_KEYS_JSON={"omni-prod-key":["admin"],"omni-read-key":["health.read","actions.read","job.read"]}`

## Common Headers

Read requests (`GET`):

```http
X-API-Key: omni-prod-key
Content-Type: application/json
```

Mutating requests (`POST`, `PUT`, `PATCH`):

```http
X-API-Key: omni-prod-key
Content-Type: application/json
Idempotency-Key: 1dbff6c0-4676-4c48-85f1-49b40d09c89a
```

## Success Envelope (all successful calls)

```json
{
  "request_id": "f00c6d11-f29f-4629-b4a6-640e12798ba0",
  "status": "ok",
  "message": "",
  "data": {},
  "errors": [],
  "timestamp": "2026-02-18T16:27:08.131000Z"
}
```

## Error Body (all HTTP errors)

```json
{
  "detail": "Missing API key"
}
```

## HTTP Status Codes

- `200`: successful read/update/cancel call
- `202`: async job accepted
- `400`: missing idempotency header when required
- `401`: missing/invalid auth headers
- `403`: invalid API key or missing scope
- `404`: job not found
- `409`: idempotency key reused with different payload
- `422`: validation failure (for example missing `action`)
- `503`: API key config not set on server

## Full OMNI Endpoint List

- `GET /api/v2/omni/health`
- `GET /api/v2/omni/whoami`
- `GET /api/v2/omni/actions`
- `GET /api/v2/omni/bootstrap`
- `GET /api/v2/omni/workflows`
- `POST /api/v2/omni/jobs`
- `GET /api/v2/omni/jobs`
- `GET /api/v2/omni/jobs/{job_id}`
- `GET /api/v2/omni/jobs/{job_id}/events`
- `POST /api/v2/omni/jobs/{job_id}/cancel`
- `PUT /api/v2/omni/jobs/{job_id}/cancel`
- `PATCH /api/v2/omni/jobs/{job_id}`

## 1) Health

### Request

`GET https://noc-configmaker.nxlink.com/api/v2/omni/health`

### Response `200`

```json
{
  "request_id": "de34edce-f608-4f1c-a4d6-c76c113cd4e4",
  "status": "degraded",
  "message": "v2 health",
  "data": {
    "legacy_api_base": "http://127.0.0.1:5000",
    "legacy_health": {
      "ok": false,
      "error": "HTTPConnectionPool(host='127.0.0.1', port=5000): Max retries exceeded"
    },
    "ido_caps": {
      "ok": false,
      "error": "HTTPConnectionPool(host='127.0.0.1', port=5000): Max retries exceeded"
    }
  },
  "errors": [],
  "timestamp": "2026-02-18T16:27:09.012000Z"
}
```

## 2) Whoami

### Request

`GET https://noc-configmaker.nxlink.com/api/v2/omni/whoami`

### Response `200`

```json
{
  "request_id": "8ddf1092-21e5-4edf-a5f4-f4f53f8f0ec0",
  "status": "ok",
  "message": "",
  "data": {
    "api_key": "omni-prod-key",
    "scopes": [
      "admin"
    ]
  },
  "errors": [],
  "timestamp": "2026-02-18T16:27:10.002000Z"
}
```

## 3) Actions

### Request

`GET https://noc-configmaker.nxlink.com/api/v2/omni/actions`

### Response `200`

```json
{
  "request_id": "b5f8c93f-0c66-4764-a651-c3a4302fcad8",
  "status": "ok",
  "message": "",
  "data": {
    "actions": [
      "activity.list",
      "activity.log",
      "app.config.get",
      "aviat.abort",
      "aviat.activate_scheduled",
      "aviat.check_status",
      "aviat.fix_stp",
      "aviat.loading.get",
      "aviat.queue.get",
      "aviat.queue.update",
      "aviat.reboot_required.get",
      "aviat.reboot_required.run",
      "aviat.run",
      "aviat.scheduled.get",
      "aviat.scheduled.sync",
      "aviat.stream.global",
      "compliance.apply",
      "config.autofill_from_export",
      "config.explain",
      "config.suggest",
      "config.translate",
      "config.validate",
      "configs.get",
      "configs.list",
      "configs.portmap.download",
      "configs.portmap.extract",
      "configs.save",
      "ftth.generate_bng",
      "ftth.mf2_package",
      "ftth.preview_bng",
      "health.get",
      "ido.ap.device_info",
      "ido.ap.generate",
      "ido.ap.running_config",
      "ido.ap.standard_config",
      "ido.bh.device_info",
      "ido.bh.generate",
      "ido.bh.running_config",
      "ido.bh.standard_config",
      "ido.capabilities",
      "ido.generic.device_info",
      "ido.nokia7250.generate",
      "ido.ping",
      "ido.rpc.device_info",
      "ido.rpc.generate",
      "ido.rpc.running_config",
      "ido.rpc.standard_config",
      "ido.swt.device_info",
      "ido.swt.generate",
      "ido.swt.running_config",
      "ido.swt.standard_config",
      "ido.ups.device_info",
      "ido.ups.generate",
      "ido.ups.running_config",
      "ido.ups.standard_config",
      "ido.wave.config",
      "infrastructure.get",
      "legacy.proxy",
      "migration.config",
      "migration.mikrotik_to_nokia",
      "mt.config",
      "mt.portmap",
      "mt.render",
      "nokia.generate_7250",
      "routerboards.list"
    ],
    "notes": {
      "mt.*": "Native renderer actions",
      "legacy.proxy": "Whitelisted generic proxy to legacy /api/* endpoint",
      "activity.list/configs.list": "Convenience wrappers for common list endpoints"
    }
  },
  "errors": [],
  "timestamp": "2026-02-18T16:27:10.584000Z"
}
```

## 4) Bootstrap

### Request

`GET https://noc-configmaker.nxlink.com/api/v2/omni/bootstrap`

### Response `200`

```json
{
  "request_id": "f913489f-97c8-4d5e-9ec7-4c6f5a4f1de5",
  "status": "ok",
  "message": "OMNI bootstrap contract",
  "data": {
    "api_version": "v2",
    "service": "noc-configmaker",
    "base_url_hint": "/api/v2",
    "methods_supported": [
      "GET",
      "POST",
      "PUT",
      "PATCH"
    ],
    "resources": {
      "health": {"method": "GET", "path": "/api/v2/health"},
      "identity": {"method": "GET", "path": "/api/v2/whoami"},
      "actions": {"method": "GET", "path": "/api/v2/actions"},
      "job_submit": {"method": "POST", "path": "/api/v2/jobs"},
      "job_list": {"method": "GET", "path": "/api/v2/jobs"},
      "job_get": {"method": "GET", "path": "/api/v2/jobs/{job_id}"},
      "job_events": {"method": "GET", "path": "/api/v2/jobs/{job_id}/events"},
      "job_cancel_patch": {"method": "PATCH", "path": "/api/v2/jobs/{job_id}"},
      "job_cancel_put": {"method": "PUT", "path": "/api/v2/jobs/{job_id}/cancel"}
    },
    "notes": {
      "read_method": "READ maps to GET in HTTP semantics",
      "auth": "X-API-Key",
      "idempotency": "Mutating endpoints require Idempotency-Key"
    }
  },
  "errors": [],
  "timestamp": "2026-02-18T16:27:11.004000Z"
}
```

## 5) Workflows

### Request

`GET https://noc-configmaker.nxlink.com/api/v2/omni/workflows`

### Response `200`

```json
{
  "request_id": "86d57fe9-a32e-44a3-bf33-eae2e8ff0f26",
  "status": "ok",
  "message": "OMNI workflow/action mappings",
  "data": {
    "workflows": {
      "dashboard": {
        "health": "health.get",
        "activity_list": "activity.list",
        "configs_list": "configs.list"
      },
      "mikrotik": {
        "render": {"action": "mt.render", "required": ["config_type", "payload"]},
        "config_only": {"action": "mt.config", "required": ["config_type", "payload"]},
        "portmap_only": {"action": "mt.portmap", "required": ["config_type", "payload"]}
      },
      "field_config_studio": {
        "ap": ["ido.ap.device_info", "ido.ap.running_config", "ido.ap.standard_config", "ido.ap.generate"],
        "bh": ["ido.bh.device_info", "ido.bh.running_config", "ido.bh.standard_config", "ido.bh.generate"],
        "switch": ["ido.swt.device_info", "ido.swt.running_config", "ido.swt.standard_config", "ido.swt.generate"],
        "ups": ["ido.ups.device_info", "ido.ups.running_config", "ido.ups.standard_config", "ido.ups.generate"],
        "rpc": ["ido.rpc.device_info", "ido.rpc.running_config", "ido.rpc.standard_config", "ido.rpc.generate"]
      },
      "aviat": {
        "run": "aviat.run",
        "check_status": "aviat.check_status",
        "activate_scheduled": "aviat.activate_scheduled",
        "queue_get": "aviat.queue.get",
        "queue_update": "aviat.queue.update"
      },
      "ftth": {
        "preview_bng": "ftth.preview_bng",
        "generate_bng": "ftth.generate_bng",
        "mf2_package": "ftth.mf2_package"
      }
    },
    "parity_doc": "/docs/UI_API_PARITY.md",
    "actions_count": 65
  },
  "errors": [],
  "timestamp": "2026-02-18T16:27:11.604000Z"
}
```

## 6) Submit Job

### Request

`POST https://noc-configmaker.nxlink.com/api/v2/omni/jobs`

Request body:

```json
{
  "action": "ftth.generate_bng",
  "payload": {
    "deployment_type": "outstate",
    "router_identity": "RTR-MT2216-AR1.NE-WESTERN-WE-1",
    "loopback_ip": "10.249.7.137/32",
    "olt_network": "10.249.180.0/29",
    "olt_name_primary": "NE-WESTERN-MF2-1"
  }
}
```

Alternative accepted body (top-level params become payload if `payload` is omitted):

```json
{
  "action": "health.get",
  "path": "/api/health",
  "method": "GET"
}
```

### Response `202`

```json
{
  "request_id": "9fcb9791-198c-43e3-8e5a-5f6aa7f15a03",
  "status": "accepted",
  "message": "Job accepted",
  "data": {
    "job_id": "089d0977-cec4-4cd8-9961-5c2dc9bbb34f",
    "request_id": "9fcb9791-198c-43e3-8e5a-5f6aa7f15a03",
    "action": "ftth.generate_bng",
    "status": "queued"
  },
  "errors": [],
  "timestamp": "2026-02-18T16:27:12.114000Z"
}
```

### Submit errors

Missing idempotency key:

```json
{
  "detail": "Missing Idempotency-Key"
}
```

Missing action:

```json
{
  "detail": "Missing 'action'"
}
```

## 7) List Jobs

### Request

`GET https://noc-configmaker.nxlink.com/api/v2/omni/jobs?limit=100`

### Response `200`

```json
{
  "request_id": "f8966fcb-98e2-44f8-8740-9ad2400c4bf7",
  "status": "ok",
  "message": "",
  "data": {
    "jobs": [
      {
        "job_id": "089d0977-cec4-4cd8-9961-5c2dc9bbb34f",
        "request_id": "9fcb9791-198c-43e3-8e5a-5f6aa7f15a03",
        "action": "health.get",
        "submitted_by": "omni-prod-key",
        "status": "success",
        "created_at": "2026-02-18T16:27:12.114000Z",
        "started_at": "2026-02-18T16:27:12.140000Z",
        "finished_at": "2026-02-18T16:27:12.221000Z",
        "cancel_requested": false,
        "result": {
          "http_status": 200,
          "ok": true,
          "method": "GET",
          "path": "/api/health",
          "response": {
            "status": "online"
          }
        },
        "error": null
      }
    ],
    "count": 1
  },
  "errors": [],
  "timestamp": "2026-02-18T16:27:12.231000Z"
}
```

## 8) Job Detail

### Request

`GET https://noc-configmaker.nxlink.com/api/v2/omni/jobs/089d0977-cec4-4cd8-9961-5c2dc9bbb34f`

### Response `200`

```json
{
  "request_id": "15a4df1c-3f32-483b-ab59-2874521ca2f5",
  "status": "ok",
  "message": "",
  "data": {
    "job_id": "089d0977-cec4-4cd8-9961-5c2dc9bbb34f",
    "request_id": "9fcb9791-198c-43e3-8e5a-5f6aa7f15a03",
    "action": "ftth.generate_bng",
    "submitted_by": "omni-prod-key",
    "status": "running",
    "created_at": "2026-02-18T16:27:12.114000Z",
    "started_at": "2026-02-18T16:27:12.140000Z",
    "finished_at": null,
    "cancel_requested": false,
    "result": null,
    "error": null,
    "payload": {
      "deployment_type": "outstate",
      "router_identity": "RTR-MT2216-AR1.NE-WESTERN-WE-1",
      "loopback_ip": "10.249.7.137/32",
      "olt_network": "10.249.180.0/29",
      "olt_name_primary": "NE-WESTERN-MF2-1"
    }
  },
  "errors": [],
  "timestamp": "2026-02-18T16:27:12.261000Z"
}
```

Not found:

```json
{
  "detail": "Job not found"
}
```

## 9) Job Events

### Request

`GET https://noc-configmaker.nxlink.com/api/v2/omni/jobs/089d0977-cec4-4cd8-9961-5c2dc9bbb34f/events`

### Response `200`

```json
{
  "request_id": "5a5e5db4-4ed6-4f26-ac87-d48eb7efc9f8",
  "status": "ok",
  "message": "",
  "data": {
    "job_id": "089d0977-cec4-4cd8-9961-5c2dc9bbb34f",
    "status": "running",
    "events": [
      {
        "ts": "2026-02-18T16:27:12.140000Z",
        "level": "info",
        "message": "Started action 'ftth.generate_bng'"
      },
      {
        "ts": "2026-02-18T16:27:12.221000Z",
        "level": "success",
        "message": "Action completed"
      }
    ]
  },
  "errors": [],
  "timestamp": "2026-02-18T16:27:12.281000Z"
}
```

## 10) Cancel Job

All cancel variants perform the same operation.

### POST cancel

`POST https://noc-configmaker.nxlink.com/api/v2/omni/jobs/089d0977-cec4-4cd8-9961-5c2dc9bbb34f/cancel`

Body:

```json
{}
```

### PUT cancel

`PUT https://noc-configmaker.nxlink.com/api/v2/omni/jobs/089d0977-cec4-4cd8-9961-5c2dc9bbb34f/cancel`

Body:

```json
{}
```

### PATCH cancel

`PATCH https://noc-configmaker.nxlink.com/api/v2/omni/jobs/089d0977-cec4-4cd8-9961-5c2dc9bbb34f`

Body:

```json
{
  "op": "cancel"
}
```

Also accepted:

```json
{
  "action": "stop"
}
```

### Response `200`

```json
{
  "request_id": "7dc6cb40-fc08-4e53-ad4d-8afeb1fdf0e0",
  "status": "ok",
  "message": "Cancel request accepted",
  "data": {
    "job_id": "089d0977-cec4-4cd8-9961-5c2dc9bbb34f",
    "status": "running",
    "cancel_requested": true
  },
  "errors": [],
  "timestamp": "2026-02-18T16:27:12.312000Z"
}
```

PATCH validation failure:

```json
{
  "detail": "Supported PATCH ops: cancel"
}
```

## Job Status Values and Meaning

- `queued`: accepted and waiting in worker queue
- `running`: worker started action execution
- `success`: action completed without exception
- `error`: action failed or was interrupted
- `cancelled`: cancel flag set before completion

## Fields by Endpoint

### Fields in `GET /jobs` items

- `job_id` (string)
- `request_id` (string)
- `action` (string)
- `submitted_by` (string)
- `status` (string)
- `created_at` (RFC3339 UTC string)
- `started_at` (RFC3339 UTC string or `null`)
- `finished_at` (RFC3339 UTC string or `null`)
- `cancel_requested` (boolean)
- `result` (object or `null`)
- `error` (string or `null`)

### Additional field in `GET /jobs/{job_id}`

- `payload` (object)

### Fields in `GET /jobs/{job_id}/events`

- `job_id` (string)
- `status` (string)
- `events` (array of objects)

Event object fields:

- `ts` (RFC3339 UTC string)
- `level` (`info`, `warning`, `success`, `error`)
- `message` (string)

## Auth and Validation Errors (Exact JSON)

Missing API key:

```json
{
  "detail": "Missing API key"
}
```

Invalid API key:

```json
{
  "detail": "Invalid API key"
}
```

Insufficient scope:

```json
{
  "detail": "Insufficient scope; need 'job.submit'"
}
```

Missing idempotency key:

```json
{
  "detail": "Missing Idempotency-Key"
}
```

Idempotency conflict:

```json
{
  "detail": "Idempotency-Key reused with different payload"
}
```

Server key config missing:

```json
{
  "detail": "API keys are not configured for /api/v2 (set NOC_API_KEYS_JSON or NOC_API_KEYS)"
}
```

## OMNI Quick Sequence

1. `GET /api/v2/omni/health`
2. `GET /api/v2/omni/whoami`
3. `GET /api/v2/omni/actions`
4. `POST /api/v2/omni/jobs`
5. Poll `GET /api/v2/omni/jobs/{job_id}`
6. Poll `GET /api/v2/omni/jobs/{job_id}/events`
7. Optional cancel with one cancel endpoint

## Runtime API Docs

- Swagger: `https://noc-configmaker.nxlink.com/docs`
- OpenAPI JSON: `https://noc-configmaker.nxlink.com/openapi.json`
