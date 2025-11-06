NOC Config Maker – Consolidated Documentation

Contents
- Setup (Local and Dedicated)
- Architecture & Components
- Policies & Compliance
- API Reference
- Generation Workflows
- Testing & Troubleshooting

Setup
- Requirements: Python 3.8+, Windows (batch scripts), optional: Ollama
- Install: pip install -r requirements.txt
- Start: start_backend_services.bat (launches Ollama if present, API on 5000, UI on 8000)

Architecture
- Backend (Flask): api_server.py
- Policies: config_policies/ (auto-loaded markdown)
- References: nextlink_*_reference.py (compliance, enterprise)
- Training data: ROS_TRAINING_DIR (optional)
- UI: NOC-configMaker.html served by serve_html.py

Policies & Compliance
- Markdown policies live in config_policies/ and are recursively loaded.
- Python references:
  - nextlink_compliance_reference.py – RFC-09-10-25 blocks
  - nextlink_enterprise_reference.py – standard blocks
  - nextlink_standards.py – constants and matrices
- Policy APIs:
  - GET /api/get-config-policies
  - GET /api/get-config-policy/{name}
  - POST /api/reload-config-policies

API Reference (Core)
- POST /api/validate-config – validate RouterOS
- POST /api/suggest-config – suggest partials
- POST /api/translate-config – ROS6↔ROS7
- POST /api/autofill-from-export – parse export
- POST /api/chat – chat with memory

Generation Workflows
- Non‑MPLS Enterprise: POST /api/gen-enterprise-non-mpls
  - Inputs: device, target_version, loopback_ip, public_cidr, bh_cidr, optional private_cidr/pool
  - Output: RouterOS config; normalized and consistent
- Tarana Sector: POST /api/gen-tarana-config
  - Inputs: device, routeros_version, raw_config
  - Output: corrected config with CIDR fixes

Testing
- Health: curl http://localhost:5000/api/health
- Chat: python test_simple_chat.py
- Validation: see README examples

Troubleshooting
- If Ollama unavailable: install via install_phi3.bat and rerun start_backend_services.bat
- Policy not visible: POST /api/reload-config-policies and retry
- CORS/UI access: serve_html.py restricts to NOC-configMaker.html only

