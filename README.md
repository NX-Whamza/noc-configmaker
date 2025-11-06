NOC Config Maker - AI-Powered RouterOS Configuration Tool

Overview
- Generates MikroTik RouterOS configs with AI, validates and translates (ROS6 ↔ ROS7), and provides a chat assistant with memory. Built for Nextlink with enterprise features.

Key Features
- AI config generation, validation, translation
- Chat with memory and user context
- Nextlink enterprise: Non‑MPLS, Tarana, MPLS/VPLS
- Standardized port assignments and policy enforcement
- Smart model selection (Ollama/OpenAI)

Quick Start
- Windows terminal
  - pip install -r requirements.txt
  - start_backend_services.bat
- Backend: http://localhost:5000
- Web UI: http://localhost:8000/NOC-configMaker.html

Ollama Local (optional)
- install_phi3.bat
- start_backend_services.bat

Project Structure
- api_server.py               Flask backend with AI
- NOC-configMaker.html        Main UI
- serve_html.py               Secure static server
- start_backend_services.bat  Unified startup (Ollama + API + UI)
- config_policies/            All policy markdowns
- docs/                       Consolidated docs

Core API Endpoints
- POST /api/validate-config      Validate config
- POST /api/suggest-config       Suggest values for partials
- POST /api/translate-config     Translate v6↔v7
- POST /api/autofill-from-export Parse exported config
- POST /api/chat                 Chat with memory
- GET  /api/get-config-policies  List policies
- GET  /api/get-config-policy/{name} Get a policy
- POST /api/reload-config-policies Reload policies

Examples
- Generate Enterprise (Non‑MPLS)
  fetch('/api/gen-enterprise-non-mpls', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ device:'CCR2004', target_version:'7.19.4', loopback_ip:'10.0.0.1/32', public_cidr:'203.0.113.1/30', bh_cidr:'192.0.2.9/30' }) })

- Chat
  fetch('/api/chat', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ message:'Help me configure OSPF', session_id:'user123' }) })

- Translate v6 → v7
  fetch('/api/translate-config', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ source_config:'/routing ospf area add area-id=0.0.0.0', target_device:'CCR2004', target_version:'7.19.4' }) })

Configuration
- Environment
  - AI_PROVIDER=ollama | openai
  - OLLAMA_MODEL=phi3:mini
  - ROS_TRAINING_DIR=./ros-migration-trainer-v3

Policies
- All policies live in config_policies/ (auto‑loaded). See config_policies/README.md and config_policies/USAGE.md.

Documentation
- See docs/index.md for consolidated setup, endpoints, and policy usage.

Testing
- curl http://localhost:5000/api/health
- curl -X POST http://localhost:5000/api/validate-config -H "Content-Type: application/json" -d '{"config":"/system identity\nset name=TestRouter","type":"tower"}'
