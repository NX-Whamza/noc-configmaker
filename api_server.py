#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compatibility shim for running the backend from the repo root.

The actual backend lives in `vm_deployment/api_server.py`, but several scripts,
docs, and service configs expect `python api_server.py` to work from the root.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
import runpy


def _load_real_module():
    repo_root = Path(__file__).resolve().parent
    vm_dir = repo_root / "vm_deployment"
    target = vm_dir / "api_server.py"

    if not target.exists():
        raise FileNotFoundError(f"Expected backend at: {target}")

    sys.path.insert(0, str(vm_dir))

    spec = importlib.util.spec_from_file_location("_noc_configmaker_vm_api_server", target)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load backend module from: {target}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# When imported, expose the real backend module's attributes so existing docs like
# `python -c "import api_server"` behave as expected.
if __name__ != "__main__":
    _real = _load_real_module()
    for _name in dir(_real):
        if _name.startswith("__"):
            continue
        globals()[_name] = getattr(_real, _name)


def _main() -> None:
    repo_root = Path(__file__).resolve().parent
    vm_dir = repo_root / "vm_deployment"
    target = vm_dir / "api_server.py"

    if not target.exists():
        raise SystemExit(f"Expected backend at: {target}")

    # Ensure imports like `import nextlink_standards` resolve from vm_deployment/
    sys.path.insert(0, str(vm_dir))

    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    _main()
