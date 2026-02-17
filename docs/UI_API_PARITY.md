# UI to API v2 Parity Matrix

This maps current NOC ConfigMaker UI workflows to `/api/v2` job actions for OMNI/Mushu integration.

## How OMNI should call

1. `POST /api/v2/omni/jobs` with `{"action":"...", "payload":{...}}`
2. Poll `GET /api/v2/omni/jobs/{job_id}`
3. Poll `GET /api/v2/omni/jobs/{job_id}/events`

Use API key + HMAC signing + Idempotency-Key (for POST).

## Dashboard / Logs

- Health badge: `health.get`
- App defaults/config: `app.config.get`
- Infra defaults: `infrastructure.get`
- Routerboard list: `routerboards.list`
- Activity feed (history): `activity.list`
- Activity write: `activity.log`
- Saved configs list: `configs.list`

## MikroTik Generator

- Render config+portmap: `mt.render`
- Config only: `mt.config`
- Port map only: `mt.portmap`
- Compliance apply: `compliance.apply`

## Completed Configs

- Save generated config: `configs.save`
- Fetch one config by id: `configs.get` (`payload.config_id`)
- Download port map by id: `configs.portmap.download` (`payload.config_id`)
- Extract port map from text: `configs.portmap.extract`

## Migration / Translation / Explain

- Generic migration: `migration.config`
- MikroTik -> Nokia migration: `migration.mikrotik_to_nokia`
- Validate: `config.validate`
- Suggest: `config.suggest`
- Explain: `config.explain`
- Translate: `config.translate`
- Autofill from export: `config.autofill_from_export`
- Nokia 7250 generator: `nokia.generate_7250`

## Field Config Studio (IDO-backed)

- Capabilities: `ido.capabilities`
- Ping: `ido.ping`
- Generic device info: `ido.generic.device_info`

AP:

- `ido.ap.device_info`
- `ido.ap.running_config`
- `ido.ap.standard_config`
- `ido.ap.generate`

BH:

- `ido.bh.device_info`
- `ido.bh.running_config`
- `ido.bh.standard_config`
- `ido.bh.generate`

Switch:

- `ido.swt.device_info`
- `ido.swt.running_config`
- `ido.swt.standard_config`
- `ido.swt.generate`

UPS:

- `ido.ups.device_info`
- `ido.ups.running_config`
- `ido.ups.standard_config`
- `ido.ups.generate`

RPC:

- `ido.rpc.device_info`
- `ido.rpc.running_config`
- `ido.rpc.standard_config`
- `ido.rpc.generate`

Wave / 7250:

- `ido.wave.config`
- `ido.nokia7250.generate`

## FTTH

- Preview BNG: `ftth.preview_bng`
- Generate BNG: `ftth.generate_bng`
- MF2 package: `ftth.mf2_package`

## Aviat Backhaul Updater

- Run workflow: `aviat.run`
- Activate scheduled: `aviat.activate_scheduled`
- Check status batch: `aviat.check_status`
- Read queues: `aviat.scheduled.get`, `aviat.loading.get`, `aviat.queue.get`, `aviat.reboot_required.get`
- Update queue: `aviat.queue.update`
- Run reboot-required queue: `aviat.reboot_required.run`
- Sync scheduled queue: `aviat.scheduled.sync`
- Fix STP: `aviat.fix_stp`
- Stream global log: `aviat.stream.global`
- Abort task: `aviat.abort` (`payload.task_id`)

## Escape hatch

- `legacy.proxy` for endpoints not yet promoted.
- This should be treated as temporary; prefer typed actions above.
