# Nexus tab index

**Backend source of truth:** `vm_deployment/api_server.py` → `NEXTLINK_TAB_CATALOG`. Keep this file aligned with that constant.

Source of truth for `data-tab="..."` values found in `vm_deployment/nexus.html`.
Grew session-over-session per skill improvement loop. Verify line numbers before quoting them — they drift.

Last full audit anchor: nexus.html line 4894 (nav block).

## MikroTik / wireless

| data-tab | Human name | Generator | Backend routes |
|---|---|---|---|
| `tower` | MikroTik Config Generator | `mt_config_gen/mt_tower.py` | `/api/generate-tower`, `/api/sites/search`, `/api/sites/refresh` |
| `enterprise` | Non-MPLS Enterprise | `mt_config_gen/mt_bng2.py` (partial) + api_server | `/api/generate-enterprise` |
| `enterprise-mpls` | MPLS Enterprise | api_server | `/api/generate-enterprise-mpls` |
| `tarana` | Tarana Sectors | api_server | `/api/generate-tarana` |
| `enterprise-feeding` | Enterprise Feeding | api_server | `/api/generate-enterprise-feeding` |
| `ccr2004` | 6GHz Switch Port | api_server | `/api/generate-ccr2004` |
| `switch-maker` | MikroTik Switch Maker | api_server | `/api/generate-switch` |
| `warehouse-sm` | Warehouse SM Provisioning | api_server | `/api/warehouse-sm` |
| `field-config-studio` | Device Config Studio | api_v2 (FastAPI) | `/field-config-studio/*` |

## Nokia

| data-tab | Human name | Routes |
|---|---|---|
| `nokia7250-maker` | Nokia Configurator | `/api/generate-nokia` |
| `mikrotik-to-nokia` | Nokia Migration | `/api/migrate-mikrotik-to-nokia` (line 17768) |

## Firmware / hardware updaters

| data-tab | data-device-firmware-tab | Generator/engine | Routes |
|---|---|---|---|
| `device-firmware-updater` | `aviat` | `vm_deployment/aviat_config.py` | `/api/aviat/*` (line 23044+) — run, queue, status, stream, precheck, fix-stp, abort |
| `device-firmware-updater` | `cambium` | `vm_deployment/cambium_firmware.py` | `/api/cambium/*` |
| `device-firmware-updater` | `wave-fw` | (Ubiquiti) | `/api/wave/*` |

## FTTH

| data-tab | data-ftth-home-tab | Generator | Routes |
|---|---|---|---|
| `ftth-home` | `olt` | `ftth_renderer.py` | `/api/generate-ftth-olt` |
| `ftth-home` | `bng` | `ftth_renderer.py` | `/api/generate-ftth-bng` |
| `ftth-home` | `fiber` | `ftth_renderer.py` | `/api/generate-ftth-fiber` |
| `ftth-home` | `fiber-site` | `ftth_renderer.py` | `/api/generate-ftth-fiber-site` (line 26850) |
| `ftth-home` | `isd-fiber` | `ftth_renderer.py` | `/api/generate-ftth-isd-fiber` |

## Migration / ops

| data-tab | Human name | Backend |
|---|---|---|
| `command-vault` | Command Vault (Nokia/Cisco/MikroTik) | `/api/command-vault/*` |
| `cisco-config` | Cisco Port Setup | `/api/generate-cisco-port` |
| `unimus-backup-configs` | Unimus Backup Configs | `/api/unimus/*` |
| `config-diff` | Config Diff Viewer | `/api/config-diff` |
| `bulk-config` | Bulk Operations Center | `/api/bulk/*` |
| `maintenance` | Scheduled Maintenance | `/api/maintenance/*` |
| `compliance-scanner` | Compliance Scanner | `/api/compliance-scan` |
| `completed-configs` | Completed Configs (history) | `/api/completed-configs` |
| `log-history` | Log History | `/api/log-history` |
| `admin-panel` | Admin Panel | `/api/admin/*` |
| `home` | Home dashboard | n/a |

## Migration entrypoint (cross-cutting)

The MikroTik ROS6→ROS7 upgrade path is invoked from the `tower` tab "Upgrade existing config" flow:
- Frontend: `performUpgrade()` in nexus.html (search by function name)
- Backend: `@app.route('/api/migrate-config')` at `vm_deployment/api_server.py:19509`
- Core funcs: `migrate_config()`, `apply_ros6_to_ros7_syntax()` (~line 3900), `validate_translation()`, `migrate_interface_config()`
- Skill: `mikrotik-migration-debug`

## Policy references

`vm_deployment/config_policies/nextlink/`:
- `texas-in-statepolicy.md` — TX in-state markets (Hudson Oaks, etc.)
- `kansas-out-of-state-mpls-config-policy.md` — KS OOS MPLS
- `illinois-out-of-state-mpls-config-policy.md` — IL OOS MPLS
- `router-interface-policy.md` — interface naming/role rules
- `nextlink-internet-policy.md` — global Nextlink rules

Per recent commit `c43f1cd`: TX/OK in-state mode is tower-only — DO NOT add to BNG2.
