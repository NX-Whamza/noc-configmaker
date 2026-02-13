#!/usr/bin/env python3
"""
FastAPI runtime wrapper for the existing NOC backend.

This mounts the current Flask app so we can switch the server runtime to FastAPI/uvicorn
without breaking existing routes while we continue native FastAPI migration incrementally.
"""

import os
import sys
from urllib.parse import urljoin
import requests
from typing import Any, Dict, Type

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

# Ensure local imports resolve when launched from repo root or service wrappers.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from api_server import app as flask_app
try:
    from mt_config_gen.mt_tower import MTTowerConfig
    from mt_config_gen.mt_bng2 import MTBNG2Config
except Exception:
    from vm_deployment.mt_config_gen.mt_tower import MTTowerConfig
    from vm_deployment.mt_config_gen.mt_bng2 import MTBNG2Config
from ido_adapter import (
    apply_compliance as ido_apply_compliance,
    get_compliance as ido_get_compliance,
    get_defaults as ido_get_defaults,
    get_device_profiles as ido_get_device_profiles,
    get_templates as ido_get_templates,
    merge_defaults as ido_merge_defaults,
)


app = FastAPI(title="NOC Config Maker API", version="1.0")

# Match current permissive CORS behavior from Flask setup.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/runtime")
def runtime_info():
    return JSONResponse(
        {
            "runtime": "fastapi",
            "mounted_backend": "flask",
            "note": "Incremental migration mode",
        }
    )


IDO_PROXY_ALLOWED_PREFIXES = (
    "/api/bh/",
    "/api/ap/",
    "/api/ups/",
    "/api/rpc/",
    "/api/swt/",
    "/api/generic/",
    "/api/ping",
    "/api/waveconfig/",
    "/api/7250config/",
    "/generate",
)


def _ido_backend_url() -> str:
    return (os.getenv("NETLAUNCH_IDO_BACKEND_URL") or "").strip()


def _ido_target_allowed(target_path: str) -> bool:
    path = "/" + target_path.lstrip("/")
    if path.startswith("/api/sites"):
        return False
    return any(path.startswith(prefix) for prefix in IDO_PROXY_ALLOWED_PREFIXES)


@app.get("/api/ido/capabilities")
def ido_capabilities():
    return JSONResponse(
        content={
            "configured": bool(_ido_backend_url()),
            "backend_url": _ido_backend_url(),
            "excluded": ["/api/sites"],
            "allowed_prefixes": list(IDO_PROXY_ALLOWED_PREFIXES),
        }
    )


@app.api_route("/api/ido/proxy/{target_path:path}", methods=["GET", "POST"])
async def ido_proxy(target_path: str, request: Request):
    backend_url = _ido_backend_url()
    if not backend_url:
        raise HTTPException(
            status_code=503,
            detail="NETLAUNCH_IDO_BACKEND_URL is not configured",
        )
    if not _ido_target_allowed(target_path):
        raise HTTPException(
            status_code=403,
            detail=f"Target path '/{target_path.lstrip('/')}' is not allowed",
        )

    url = urljoin(backend_url.rstrip("/") + "/", target_path.lstrip("/"))
    try:
        if request.method.upper() == "GET":
            upstream = requests.get(url, params=dict(request.query_params), timeout=60)
        else:
            body = {}
            try:
                body = await request.json()
            except Exception:
                body = {}
            upstream = requests.post(url, params=dict(request.query_params), json=body, timeout=60)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"IDO upstream request failed: {exc}") from exc

    # Compatibility fallback: some IDO backends expose endpoints without `/api/` prefix.
    if upstream.status_code == 404 and target_path.startswith("api/"):
        fallback_url = urljoin(backend_url.rstrip("/") + "/", target_path[4:].lstrip("/"))
        try:
            if request.method.upper() == "GET":
                upstream = requests.get(fallback_url, params=dict(request.query_params), timeout=60)
            else:
                body = {}
                try:
                    body = await request.json()
                except Exception:
                    body = {}
                upstream = requests.post(fallback_url, params=dict(request.query_params), json=body, timeout=60)
        except Exception:
            pass

    content_type = (upstream.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        try:
            return JSONResponse(content=upstream.json(), status_code=upstream.status_code)
        except Exception:
            return PlainTextResponse(content=upstream.text, status_code=upstream.status_code)
    return PlainTextResponse(content=upstream.text, status_code=upstream.status_code)


def _mt_config_class(config_type: str) -> Type[Any]:
    config_map = {
        "tower": MTTowerConfig,
        "bng2": MTBNG2Config,
    }
    config_cls = config_map.get(config_type)
    if not config_cls:
        raise HTTPException(status_code=400, detail=f"Invalid config type: {config_type}")
    return config_cls


def _require_base_config_path() -> str:
    base_path = os.getenv("BASE_CONFIG_PATH") or os.getenv("NEXTLINK_BASE_CONFIG_PATH")
    fallback = os.path.join(os.path.dirname(__file__), "base_configs")

    def _required_dirs(path: str):
        return [
            os.path.join(path, "Router", "Tower", "config"),
            os.path.join(path, "Router", "Tower", "port_map"),
            os.path.join(path, "Router", "BNG2", "config"),
            os.path.join(path, "Router", "BNG2", "port_map"),
        ]

    if base_path:
        missing = [d for d in _required_dirs(base_path) if not os.path.isdir(d)]
        if not missing:
            return base_path

    missing_fallback = [d for d in _required_dirs(fallback) if not os.path.isdir(d)]
    if not missing_fallback:
        return fallback

    raise HTTPException(
        status_code=500,
        detail={
            "error": "No valid MikroTik base config template path found",
            "configured_base_config_path": base_path,
            "missing_in_configured_path": _required_dirs(base_path) if base_path else [],
            "fallback_path": fallback,
            "missing_in_fallback_path": missing_fallback,
        },
    )


@app.post("/api/mt/{config_type}/config")
def mt_generate_config(config_type: str, payload: Dict[str, Any] = Body(default_factory=dict)):
    _require_base_config_path()
    config_cls = _mt_config_class(config_type)
    try:
        local_payload = ido_merge_defaults(config_type, dict(payload or {}))
        apply_compliance = bool(local_payload.pop("apply_compliance", True))
        payload_loopback = local_payload.get("loopback_subnet") or local_payload.get("loop_ip")
        cfg = config_cls(**local_payload)
        # Keep response shape compatible: frontend expects response.json() -> string
        config_text = cfg.generate_config()
        if apply_compliance:
            config_text = ido_apply_compliance(config_text, payload_loopback)
        return JSONResponse(content=config_text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/mt/{config_type}/portmap")
def mt_generate_portmap(config_type: str, payload: Dict[str, Any] = Body(default_factory=dict)):
    _require_base_config_path()
    config_cls = _mt_config_class(config_type)
    try:
        cfg = config_cls(**ido_merge_defaults(config_type, dict(payload or {})))
        # Keep response shape compatible: frontend expects response.json() -> string
        return JSONResponse(content=cfg.generate_port_map())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/ido/defaults")
def ido_defaults(config_type: str | None = None):
    return JSONResponse(content=ido_get_defaults(config_type))


@app.get("/api/ido/templates")
def ido_templates(config_type: str | None = None):
    return JSONResponse(content=ido_get_templates(config_type))


@app.get("/api/ido/device-profiles")
def ido_device_profiles():
    return JSONResponse(content=ido_get_device_profiles())


@app.get("/api/ido/compliance")
def ido_compliance(loopback_ip: str = "10.0.0.1"):
    return JSONResponse(content={"compliance": ido_get_compliance(loopback_ip)})


@app.post("/api/ido/render")
def ido_render(config_type: str, payload: Dict[str, Any] = Body(default_factory=dict)):
    _require_base_config_path()
    config_cls = _mt_config_class(config_type)
    try:
        local_payload = ido_merge_defaults(config_type, dict(payload or {}))
        apply_compliance = bool(local_payload.pop("apply_compliance", True))
        payload_loopback = local_payload.get("loopback_subnet") or local_payload.get("loop_ip")
        cfg = config_cls(**local_payload)
        config_text = cfg.generate_config()
        if apply_compliance:
            config_text = ido_apply_compliance(config_text, payload_loopback)
        return JSONResponse(
            content={
                "config": config_text,
                "portmap": cfg.generate_port_map(),
                "config_type": config_type,
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# Mount all existing Flask routes at root
app.mount("/", WSGIMiddleware(flask_app))
