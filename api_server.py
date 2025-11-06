#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOC Config Maker - AI Backend Server
Secure OpenAI API integration for RouterOS config generation and validation
"""

import sys
import io
# Fix Windows console encoding for Unicode
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re
import ipaddress
import json
import requests
from datetime import datetime
import sqlite3
try:
    import pytz
    CST = pytz.timezone('America/Chicago')
    HAS_PYTZ = True
except ImportError:
    HAS_PYTZ = False
    # Fallback: CST is UTC-6, CDT is UTC-5 (daylight saving)
    import time
from pathlib import Path
from nextlink_standards import (
    NEXTLINK_COMMON_ERRORS,
    NEXTLINK_NAMING,
    NEXTLINK_IP_RANGES,
    NEXTLINK_ROUTEROS_VERSIONS,
    NEXTLINK_MIGRATION_6X_TO_7X,
    NEXTLINK_DEVICE_ROLES,
    NEXTLINK_AUTO_DETECTABLE_ERRORS
)
from pathlib import Path
try:
    from nextlink_enterprise_reference import get_all_standard_blocks
    HAS_REFERENCE = True
except ImportError:
    HAS_REFERENCE = False

try:
    from nextlink_compliance_reference import get_all_compliance_blocks, validate_compliance
    HAS_COMPLIANCE = True
except ImportError:
    HAS_COMPLIANCE = False
    print("[WARN] Compliance reference not available - RFC-09-10-25 compliance will not be enforced")

# ========================================
# SMART MODEL SELECTION
# ========================================
def select_best_model(task_type: str, config_size: int = 0) -> str:
    """
    Auto-select the best model based on task type and complexity
    """
    # Model performance profiles
    models = {
        'phi3:mini': {
            'speed': 'fast',
            'accuracy': 'good',
            'context': 'medium',
            'best_for': ['validation', 'suggestion', 'chat', 'small_configs']
        },
        'qwen2.5-coder:7b': {
            'speed': 'medium', 
            'accuracy': 'excellent',
            'context': 'large',
            'best_for': ['translation', 'complex_configs', 'detailed_analysis']
        },
        'llama3.2:3b': {
            'speed': 'fast',
            'accuracy': 'good', 
            'context': 'medium',
            'best_for': ['quick_tasks', 'simple_chat']
        }
    }
    
    # Task-based selection logic - use only available models
    if task_type in ['chat', 'validation', 'suggestion']:
        return 'phi3:mini'  # Fast and reliable
    elif task_type in ['translation', 'upgrade']:
        if config_size > 5000:  # Large configs
            return 'qwen2.5-coder:7b'  # Better accuracy for complex translations
        else:
            return 'phi3:mini'  # Fast for smaller configs
    elif task_type in ['analysis', 'detailed_review']:
        return 'qwen2.5-coder:7b'  # Best accuracy for analysis
    else:
        return 'phi3:mini'  # Default to reliable model

# ========================================
# TRAINING DATA LOADER (External directory)
# ========================================
TRAINING_DIR = os.getenv('ROS_TRAINING_DIR', '').strip()
TRAINING_RULES = {}

def _read_text_file(p: Path) -> str:
    try:
        return p.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return ''

def _read_json_file(p: Path):
    try:
        import json as _json
        return _json.loads(p.read_text(encoding='utf-8', errors='ignore'))
    except Exception:
        return None

def load_training_rules(directory: str) -> dict:
    rules = {}
    if not directory:
        return rules
    base = Path(directory)
    if not base.exists():
        print(f"[TRAINING] Directory not found: {directory}")
        return rules
    print(f"[TRAINING] Loading RouterOS training from: {directory}")
    for p in base.iterdir():
        if p.suffix.lower() in ['.json']:
            obj = _read_json_file(p)
            if obj is not None:
                rules[p.stem] = obj
        elif p.suffix.lower() in ['.md', '.txt']:
            rules[p.stem] = _read_text_file(p)
    print(f"[TRAINING] Loaded {len(rules)} items: {', '.join(sorted(rules.keys()))}")
    return rules

TRAINING_RULES = load_training_rules(TRAINING_DIR)

# ========================================
# CONFIG POLICY LOADER
# ========================================
CONFIG_POLICIES_DIR = Path("config_policies")
CONFIG_POLICIES = {}

def load_config_policies(directory: Path = None) -> dict:
    """
    Load ALL configuration policies from directory structure recursively.
    Finds all .md policy files in config_policies/ and organizes them by category.
    
    Structure:
    - config_policies/{category}/{policy-name}.md
    - config_policies/{category}/{policy-name}-policy.md
    - config_policies/{category}/{policy-name}-config-policy.md
    
    Also loads compliance references from Python modules.
    """
    policies = {}
    if directory is None:
        directory = CONFIG_POLICIES_DIR
    
    if not directory.exists():
        print(f"[POLICIES] Directory not found: {directory}")
        return policies
    
    print(f"[POLICIES] Loading ALL configuration policies from: {directory}")
    
    # Recursively find all .md files (excluding README.md and USAGE.md in root)
    exclude_names = {'README.md', 'USAGE.md', 'readme.md', 'usage.md'}
    exclude_dirs = {'examples', '__pycache__', '.git'}
    
    for md_file in directory.rglob("*.md"):
        # Skip excluded files
        if md_file.name in exclude_names and md_file.parent == directory:
            continue
        
        # Skip excluded directories
        if any(excluded in md_file.parts for excluded in exclude_dirs):
            continue
        
        try:
            # Create policy key from path: category-policy-name
            # e.g., "nextlink/nextlink-internet-policy.md" -> "nextlink-internet-policy"
            relative_path = md_file.relative_to(directory)
            category = relative_path.parts[0] if len(relative_path.parts) > 1 else 'root'
            policy_name_no_ext = md_file.stem
            
            # Create unique key: category-policy-name
            policy_key = f"{category}-{policy_name_no_ext}" if category != 'root' else policy_name_no_ext
            
            # Read policy content
            policy_content = md_file.read_text(encoding='utf-8', errors='ignore')
            
            policies[policy_key] = {
                'name': policy_key,
                'category': category,
                'filename': md_file.name,
                'content': policy_content,
                'path': str(md_file),
                'relative_path': str(relative_path)
            }
            
            print(f"[POLICIES] Loaded: {policy_key} from {relative_path}")
            
        except Exception as e:
            print(f"[POLICIES] Error loading {md_file}: {e}")
    
    # Also load compliance references from Python modules
    try:
        if HAS_COMPLIANCE:
            from nextlink_compliance_reference import get_all_compliance_blocks
            compliance_blocks = get_all_compliance_blocks()
            if compliance_blocks:
                policies['compliance-reference'] = {
                    'name': 'compliance-reference',
                    'category': 'compliance',
                    'filename': 'nextlink_compliance_reference.py',
                    'content': f"# NextLink Compliance Reference (RFC-09-10-25)\n\nThis is the compliance reference module content.\n\n```python\n# Compliance blocks are available via get_all_compliance_blocks()\n```\n\n**Note:** This reference is loaded from the Python module `nextlink_compliance_reference.py`.",
                    'path': 'nextlink_compliance_reference.py',
                    'relative_path': 'nextlink_compliance_reference.py',
                    'type': 'python_module'
                }
                print(f"[POLICIES] Loaded compliance reference from Python module")
    except Exception as e:
        print(f"[POLICIES] Could not load compliance reference: {e}")
    
    # Load enterprise reference if available
    try:
        if HAS_REFERENCE:
            from nextlink_enterprise_reference import get_all_standard_blocks
            policies['enterprise-reference'] = {
                'name': 'enterprise-reference',
                'category': 'reference',
                'filename': 'nextlink_enterprise_reference.py',
                'content': "# NextLink Enterprise Reference\n\nThis is the enterprise reference module containing standard configuration blocks.\n\n**Note:** This reference is loaded from the Python module `nextlink_enterprise_reference.py`.",
                'path': 'nextlink_enterprise_reference.py',
                'relative_path': 'nextlink_enterprise_reference.py',
                'type': 'python_module'
            }
            print(f"[POLICIES] Loaded enterprise reference from Python module")
    except Exception as e:
        print(f"[POLICIES] Could not load enterprise reference: {e}")
    
    print(f"[POLICIES] ✅ Loaded {len(policies)} total policies/references")
    print(f"[POLICIES] Categories: {', '.join(sorted(set(p.get('category', 'unknown') for p in policies.values())))}")
    return policies

# Load policies on startup
CONFIG_POLICIES = load_config_policies()

# ========================================
# CHAT HISTORY & MEMORY SYSTEM
# ========================================
# SECURITY: Database files in secure directory (not accessible via HTTP)
import os
import shutil

SECURE_DATA_DIR = Path("secure_data")
SECURE_DATA_DIR.mkdir(exist_ok=True)
# Set restrictive permissions (Unix-like systems)
try:
    os.chmod(SECURE_DATA_DIR, 0o700)  # Only owner can access
except:
    pass  # Windows doesn't support chmod

CHAT_DB_PATH = SECURE_DATA_DIR / "chat_history.db"

# Migration: Move existing databases from root to secure directory
def migrate_databases():
    """Migrate existing database files from root to secure_data directory"""
    old_chat_db = Path("chat_history.db")
    old_configs_db = Path("completed_configs.db")
    
    if old_chat_db.exists() and not CHAT_DB_PATH.exists():
        print(f"[MIGRATION] Moving {old_chat_db} to {CHAT_DB_PATH}")
        shutil.move(str(old_chat_db), str(CHAT_DB_PATH))
        print(f"[MIGRATION] ✓ Chat history database migrated")
    
    if old_configs_db.exists():
        new_configs_db = SECURE_DATA_DIR / "completed_configs.db"
        if not new_configs_db.exists():
            print(f"[MIGRATION] Moving {old_configs_db} to {new_configs_db}")
            shutil.move(str(old_configs_db), str(new_configs_db))
            print(f"[MIGRATION] ✓ Configs database migrated")

# Run migration on import
migrate_databases()

def init_chat_db():
    """Initialize chat history database in secure location"""
    conn = sqlite3.connect(str(CHAT_DB_PATH))
    cursor = conn.cursor()
    
    # Create conversations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            user_message TEXT NOT NULL,
            ai_response TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            model_used TEXT,
            task_type TEXT
        )
    ''')
    
    # Create user preferences table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            session_id TEXT PRIMARY KEY,
            preferred_model TEXT,
            context_memory TEXT,
            last_activity DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"[CHAT] Database initialized: {CHAT_DB_PATH}")

def save_chat_message(session_id, user_message, ai_response, model_used, task_type):
    """Save chat message to database"""
    conn = sqlite3.connect(str(CHAT_DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO conversations (session_id, user_message, ai_response, model_used, task_type)
        VALUES (?, ?, ?, ?, ?)
    ''', (session_id, user_message, ai_response, model_used, task_type))
    
    conn.commit()
    conn.close()

def get_chat_history(session_id, limit=10):
    """Get recent chat history for context"""
    conn = sqlite3.connect(str(CHAT_DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_message, ai_response, timestamp, model_used, task_type
        FROM conversations 
        WHERE session_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    ''', (session_id, limit))
    
    history = cursor.fetchall()
    conn.close()
    
    return history

def get_user_context(session_id):
    """Get user's context and preferences"""
    conn = sqlite3.connect(str(CHAT_DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT preferred_model, context_memory, last_activity
        FROM user_preferences 
        WHERE session_id = ?
    ''', (session_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'preferred_model': result[0],
            'context_memory': result[1],
            'last_activity': result[2]
        }
    return None

def update_user_context(session_id, preferred_model=None, context_memory=None):
    """Update user preferences and context"""
    conn = sqlite3.connect(str(CHAT_DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO user_preferences (session_id, preferred_model, context_memory, last_activity)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (session_id, preferred_model, context_memory))
    
    conn.commit()
    conn.close()

# Initialize chat database
init_chat_db()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
CORS(app)  # Enable CORS for local HTML file access

# Hot-reload endpoint (now that app exists)
@app.route('/api/reload-training', methods=['POST'])
def reload_training():
    global TRAINING_RULES
    global TRAINING_DIR
    try:
        d = request.json.get('dir') if request.is_json else None
        if d:
            os.environ['ROS_TRAINING_DIR'] = d
            TRAINING_DIR = d
        directory = d or TRAINING_DIR
        TRAINING_RULES = load_training_rules(directory)
        return jsonify({'success': True, 'loaded': list(TRAINING_RULES.keys()), 'dir': directory})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========================================
# ENDPOINT: Simple AI Chat
# ========================================

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json(force=True)
        msgs = data.get('messages')
        message = data.get('message')
        session_id = data.get('session_id', 'default')

        # Get user context and chat history
        user_context = get_user_context(session_id)
        chat_history = get_chat_history(session_id, limit=5)
        
        training_context = build_training_context()
        system_prompt = "You are a RouterOS and network engineering assistant. Be accurate, concise, and prefer RouterOS CLI examples. If asked about migrations, apply ROS6→ROS7 rules."
        if training_context:
            system_prompt += "\n\n" + training_context
        
        # Add user context to system prompt
        if user_context and user_context.get('context_memory'):
            system_prompt += f"\n\nUser Context: {user_context['context_memory']}"

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add recent chat history for context
        for hist in reversed(chat_history):
            messages.append({"role": "user", "content": hist[0]})
            messages.append({"role": "assistant", "content": hist[1]})
        
        # Add current message
        if isinstance(msgs, list) and msgs:
            for m in msgs:
                if isinstance(m, dict) and m.get('role') in ('user', 'assistant') and m.get('content'):
                    messages.append({"role": m['role'], "content": str(m['content'])})
        elif message:
            messages.append({"role": "user", "content": str(message)})
        else:
            return jsonify({"success": False, "error": "No message(s) provided"}), 400

        # Smart model selection for chat (use user's preferred model if available)
        preferred_model = user_context.get('preferred_model') if user_context else None
        reply = call_ai(messages, max_tokens=2000, task_type='chat', model=preferred_model)
        
        # Save chat message to database
        current_message = message if message else (msgs[-1]['content'] if msgs else '')
        save_chat_message(session_id, current_message, reply, preferred_model or 'auto', 'chat')
        
        return jsonify({"success": True, "reply": reply, "session_id": session_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ========================================
# CHAT HISTORY & MEMORY ENDPOINTS
# ========================================

@app.route('/api/chat/history/<session_id>', methods=['GET'])
def get_chat_history_endpoint(session_id):
    """Get chat history for a session"""
    try:
        limit = request.args.get('limit', 20, type=int)
        history = get_chat_history(session_id, limit)
        
        formatted_history = []
        for hist in history:
            formatted_history.append({
                'user_message': hist[0],
                'ai_response': hist[1],
                'timestamp': hist[2],
                'model_used': hist[3],
                'task_type': hist[4]
            })
        
        return jsonify({"success": True, "history": formatted_history})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/chat/context/<session_id>', methods=['GET'])
def get_user_context_endpoint(session_id):
    """Get user context and preferences"""
    try:
        context = get_user_context(session_id)
        return jsonify({"success": True, "context": context})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/chat/context/<session_id>', methods=['POST'])
def update_user_context_endpoint(session_id):
    """Update user context and preferences"""
    try:
        data = request.get_json(force=True)
        preferred_model = data.get('preferred_model')
        context_memory = data.get('context_memory')
        
        update_user_context(session_id, preferred_model, context_memory)
        return jsonify({"success": True, "message": "Context updated"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/chat/export/<session_id>', methods=['GET'])
def export_chat_history(session_id):
    """Export chat history as JSON"""
    try:
        history = get_chat_history(session_id, limit=1000)
        
        export_data = {
            'session_id': session_id,
            'export_timestamp': datetime.now().isoformat(),
            'total_messages': len(history),
            'conversations': []
        }
        
        for hist in history:
            export_data['conversations'].append({
                'user_message': hist[0],
                'ai_response': hist[1],
                'timestamp': hist[2],
                'model_used': hist[3],
                'task_type': hist[4]
            })
        
        return jsonify(export_data)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/chat', methods=['GET'])
def web_chat():
    # Minimal standalone web chat for backend interaction
    popup = request.args.get('popup') in ('1','true','yes')
    wrap_extra = 'position:fixed; right:16px; bottom:16px; width:420px;' if popup else 'max-width:900px;margin:0 auto;'
    bg = '#0f1115cc' if popup else '#0f1115'
    radius = '12px' if popup else '0'
    shadow = '0 8px 24px rgba(0,0,0,.45)' if popup else 'none'
    log_h = '360px' if popup else '60vh'
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>NOC Config Maker - AI Chat</title>
  <style>
    body{font-family:Segoe UI,Arial,sans-serif;background:#0f1115;color:#eee;margin:0;padding:0}
    .wrap{ %(wrap_extra)s padding:20px; background:%(bg)s; border-radius:%(radius)s; box-shadow:%(shadow)s; z-index:99999; position:relative }
    h1{font-size:18px;margin:0 0 12px}
    #log{height:%(log_h)s;overflow:auto;border:1px solid #333;border-radius:8px;padding:12px;background:#161a22;white-space:pre-wrap}
    .row{display:flex;gap:8px;margin-top:10px}
    #q{flex:1;padding:10px;border-radius:6px;border:1px solid #333;background:#0f1115;color:#eee}
    button{background:#4CAF50;border:none;color:#fff;border-radius:6px;padding:10px 14px;cursor:pointer}
    .note{font-size:12px;color:#9aa}
  </style>
  <script>
    function bindChat(){
      const log=document.getElementById('log');
      const input=document.getElementById('q');
      const btn=document.getElementById('sendBtn');
      const status=document.getElementById('status');
      if(!log||!input||!btn) return;
      function append(prefix, msg){
        log.innerText += (prefix? prefix+' ':'') + msg + '\n';
        log.scrollTop = log.scrollHeight;
      }
      async function health(){
        try{ const r=await fetch('/api/health'); const j=await r.json(); status.textContent = (j.status==='online'?'Online':'Offline'); status.style.color = (j.status==='online'?'#7ee2a8':'#ff7676'); }
        catch{ status.textContent='Offline'; status.style.color='#ff7676'; }
      }
      async function sendMsg(){
        const t=input.value.trim();
        if(!t) return;
        append('[user]', t);
        input.value='';
        try{
          const ctrl = new AbortController(); const to = setTimeout(()=>ctrl.abort(), 60000);
          const r = await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:t}) , signal: ctrl.signal});
          clearTimeout(to);
          if(!r.ok){ throw new Error('HTTP '+r.status); }
          const j = await r.json();
          if(!j.success) throw new Error(j.error||'Chat failed');
          append('[ai]', String(j.reply||''));
        }catch(e){ append('[error]', e.message||String(e)); }
      }
      const form=document.getElementById('frm');
      form.addEventListener('submit', function(e){ e.preventDefault(); sendMsg(); });
      btn.addEventListener('click', function(e){ e.preventDefault(); sendMsg(); });
      input.addEventListener('keydown', function(e){ if(e.key==='Enter'){ e.preventDefault(); sendMsg(); }});
      window.sendMsg = sendMsg; // optional
      health();
    }
    window.addEventListener('DOMContentLoaded', bindChat);
  </script>
</head>
<body>
  <div class="wrap">
    <h1>AI Assistant Chat</h1>
    <div id="status" class="note" style="margin:4px 0 8px 0;">Checking...</div>
    <div id="log"></div>
    <form class="row" id="frm">
      <input id="q" type="text" placeholder="Ask about RouterOS, ROS6->ROS7, OSPF/BGP, etc..." autocomplete="off" />
      <button id="sendBtn" type="submit">Send</button>
    </form>
    <p class="note">Tip: set ROS_TRAINING_DIR before start, or POST /api/reload-training to apply your standards.</p>
  </div>
</body>
</html>
""" % { 'wrap_extra': wrap_extra, 'bg': bg, 'radius': radius, 'shadow': shadow, 'log_h': log_h }
    return html

# ========================================
# OpenAI-compatible endpoints for external UIs (e.g., Open WebUI)
# Base URL: http://localhost:5000/v1
# ========================================

@app.route('/v1/models', methods=['GET'])
def v1_models():
    # Minimal model list so Open WebUI recognizes the server
    model_name = os.getenv('OPENAI_COMPAT_MODEL', 'noc-local')
    return jsonify({
        "object": "list",
        "data": [
            {"id": model_name, "object": "model", "created": int(datetime.utcnow().timestamp()), "owned_by": "noc-configmaker"}
        ]
    })

@app.route('/v1/chat/completions', methods=['POST'])
def v1_chat_completions():
    try:
        payload = request.get_json(force=True) or {}
        msgs = payload.get('messages', [])
        temperature = float(payload.get('temperature', 0.1))
        max_tokens = int(payload.get('max_tokens', 2000))

        # Merge OpenAI-style messages with our training context
        training_context = build_training_context()
        sys_prompt = "You are a RouterOS assistant. Prefer MikroTik CLI. Enforce ROS6→ROS7 standards and Nextlink rules."
        if training_context:
            sys_prompt += "\n\n" + training_context

        messages = [{"role": "system", "content": sys_prompt}]
        for m in msgs:
            role = m.get('role')
            content = m.get('content')
            if role in ("system", "user", "assistant") and isinstance(content, str):
                messages.append({"role": role, "content": content})

        answer = call_ai(messages, temperature=temperature, max_tokens=max_tokens)

        resp = {
            "id": f"chatcmpl_{int(datetime.utcnow().timestamp())}",
            "object": "chat.completion",
            "created": int(datetime.utcnow().timestamp()),
            "model": payload.get('model') or os.getenv('OPENAI_COMPAT_MODEL', 'noc-local'),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": answer},
                    "finish_reason": "stop"
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }
        return jsonify(resp)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========================================
# AI PROVIDER CONFIGURATION
# ========================================
# Supports: 'ollama' (free, local) or 'openai' (paid, cloud)
AI_PROVIDER = os.getenv('AI_PROVIDER', 'ollama').lower()
OLLAMA_API_URL = os.getenv('OLLAMA_API_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'phi3:mini')

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# Initialize based on provider
if AI_PROVIDER == 'openai':
    try:
        from openai import OpenAI, OpenAIError, RateLimitError, AuthenticationError
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print(f"Using OpenAI (API Key: {'configured' if OPENAI_API_KEY else 'MISSING'})")
    except ImportError:
        print("WARNING: OpenAI library not installed. Install with: pip install openai")
        AI_PROVIDER = 'ollama'
else:
    print(f"Using Ollama (Local AI)")
    print(f"Model: {OLLAMA_MODEL}")
    print(f"API URL: {OLLAMA_API_URL}")

# ========================================
# AI-POWERED CONFIG HELPERS
# ========================================

def call_ollama(messages, model=None, temperature=0.1, max_tokens=4000):
    """
    Call Ollama local LLM API
    """
    if model is None:
        model = OLLAMA_MODEL
    
    try:
        # Convert messages to Ollama format
        prompt = "\n\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in messages])
        
        response = requests.post(
            f"{OLLAMA_API_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            },
            timeout=30  # 30 seconds for chat, 60 for complex tasks
        )
        
        if response.status_code != 200:
            raise Exception(f"Ollama API returned {response.status_code}: {response.text}")
        
        result = response.json()
        return result.get('response', '')
        
    except requests.exceptions.ConnectionError:
        raise Exception("Cannot connect to Ollama. Make sure Ollama is running. Install from: https://ollama.com/download")
    except requests.exceptions.Timeout:
        raise Exception("Ollama request timed out. The model might be too large or your system is under load.")
    except Exception as e:
        raise Exception(f"Ollama Error: {str(e)}")


def call_openai_chat(messages, model="gpt-4o", temperature=0.1, max_tokens=4000):
    """
    Call OpenAI API
    """
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except RateLimitError:
        raise Exception("OpenAI API quota exceeded. Please check your billing settings.")
    except AuthenticationError:
        raise Exception("Invalid OpenAI API key. Please check server configuration.")
    except OpenAIError as e:
        raise Exception(f"OpenAI API Error: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error: {str(e)}")


def call_ai(messages, model=None, temperature=0.1, max_tokens=16000, task_type='chat', config_size=0):
    """
    Universal AI caller with smart model selection
    Auto-selects best model based on task type and complexity
    """
    # Auto-select model if not specified
    if not model:
        model = select_best_model(task_type, config_size)
        print(f"[AI] Auto-selected model '{model}' for task '{task_type}' (size: {config_size})")
    
    if AI_PROVIDER == 'ollama':
        return call_ollama(messages, model, temperature, max_tokens)
    # Prefer OpenAI if configured, but fall back to Ollama on any error
    try:
        return call_openai_chat(messages, model or "gpt-4o", temperature, max_tokens)
    except Exception as e:
        print(f"[AI FALLBACK] OpenAI failed: {e}. Falling back to Ollama...")
        return call_ollama(messages, model, temperature, max_tokens)


def build_training_context() -> str:
    if not TRAINING_RULES:
        return ''
    parts = ["TRAINING DATA (ROS6→ROS7 standards):"]
    # Compact include for important sections
    for key in [
        'ai-consistency-rules', 'routing-ospf', 'routing-bgp', 'firewall',
        'ip-addresses', 'interfaces', 'mpls-vpls', 'snmp', 'users', 'queue',
        'nextlink-styleguide', 'system-prompt'
    ]:
        if key in TRAINING_RULES:
            val = TRAINING_RULES[key]
            if isinstance(val, dict):
                parts.append(f"[{key}]\n{json.dumps(val, indent=2)}")
            else:
                # Trim long docs to keep prompt size manageable
                txt = str(val)
                if len(txt) > 2000:
                    txt = txt[:2000] + "\n... (truncated)"
                parts.append(f"[{key}]\n{txt}")
    return "\n\n".join(parts)

# ========================================
# CONFIG NORMALIZATION / DEDUP
# ========================================

def normalize_config(config_text: str) -> str:
    """Normalize RouterOS config: strip markdown fences, deduplicate lines per section,
    and output sections in a stable order for consistency."""
    if not isinstance(config_text, str):
        return config_text
    txt = config_text.replace('```routeros', '').replace('```', '').replace('\r', '\n')
    lines = [ln.strip() for ln in txt.split('\n') if ln.strip()]

    # Section ordering for readability
    order = [
        '/system identity',
        '/queue type',
        '/interface bridge',
        '/interface ethernet',
        '/interface vlan',
        '/interface bridge port',
        '/ip address',
        '/ip pool',
        '/ip dhcp-server',
        '/routing ospf',
        '/routing bgp',
        '/mpls',
        '/interface vpls',
        '/snmp',
        '/ip service',
        '/ip firewall address-list',
        '/ip firewall filter',
        '/ip firewall nat',
        '/ip firewall mangle',
        '/system logging',
        '/system ntp',
    ]

    # Bucket lines by nearest section header
    buckets = {}
    current = None
    for ln in lines:
        if ln.startswith('/'):
            current = ln.split(' ', 2)[0] + ('' if ' ' not in ln else ' ' + ln.split(' ', 2)[1])
            # normalize known multi-word headers
            if ln.startswith('/ip firewall address-list'):
                current = '/ip firewall address-list'
            elif ln.startswith('/ip firewall filter'):
                current = '/ip firewall filter'
            elif ln.startswith('/ip firewall nat'):
                current = '/ip firewall nat'
            elif ln.startswith('/ip firewall mangle'):
                current = '/ip firewall mangle'
            elif ln.startswith('/routing ospf'):
                current = '/routing ospf'
            elif ln.startswith('/routing bgp'):
                current = '/routing bgp'
            elif ln.startswith('/interface bridge port'):
                current = '/interface bridge port'
            elif ln.startswith('/interface bridge'):
                current = '/interface bridge'
            elif ln.startswith('/interface ethernet'):
                current = '/interface ethernet'
            elif ln.startswith('/interface vlan'):
                current = '/interface vlan'
            elif ln.startswith('/interface vpls'):
                current = '/interface vpls'
            elif ln.startswith('/system identity'):
                current = '/system identity'
            elif ln.startswith('/system logging'):
                current = '/system logging'
            elif ln.startswith('/system ntp'):
                current = '/system ntp'
            elif ln.startswith('/ip address'):
                current = '/ip address'
            elif ln.startswith('/ip pool'):
                current = '/ip pool'
            elif ln.startswith('/ip dhcp-server'):
                current = '/ip dhcp-server'
            elif ln.startswith('/ip service'):
                current = '/ip service'
            elif ln.startswith('/snmp'):
                current = '/snmp'
            buckets.setdefault(current, [])
            buckets[current].append(ln)
        else:
            if current is None:
                current = '_preamble'
            buckets.setdefault(current, [])
            buckets[current].append(ln)

    # Deduplicate while preserving order within each bucket
    def dedup(seq):
        seen = set()
        out = []
        for s in seq:
            key = s
            if key in seen:
                continue
            seen.add(key)
            out.append(s)
        return out

    parts = []
    for sect in order:
        if sect in buckets:
            parts.extend(dedup(buckets[sect]))
            parts.append('')
    # Append any remaining buckets not in order list
    for sect, content in buckets.items():
        if sect not in order:
            parts.extend(dedup(content))
            parts.append('')
    return '\n'.join([p for p in parts]).strip() + '\n'

# ========================================
# ENDPOINT 1: AI Config Validation
# ========================================

@app.route('/api/validate-config', methods=['POST'])
def validate_config():
    """
    Validates a RouterOS config for syntax errors, missing fields, RFC compliance
    """
    try:
        print(f"[VALIDATE] Validation request received for type: {request.json.get('type', 'unknown')}")
        data = request.json
        config = data.get('config', '')
        config_type = data.get('type', 'tower')  # tower, enterprise, mpls
        
        if not config:
            return jsonify({'error': 'No configuration provided'}), 400
        
        print(f"[VALIDATE] Config size: {len(config)} characters, calling AI...")

        # Build Nextlink-specific context
        nextlink_context = f"""
NEXTLINK CONFIGURATION STANDARDS:

Device Roles:
{json.dumps(NEXTLINK_DEVICE_ROLES, indent=2)}

Naming Conventions:
- Devices: {NEXTLINK_NAMING['device_patterns']['tower']} or {NEXTLINK_NAMING['device_patterns']['core']}
- Bridges: {', '.join(NEXTLINK_NAMING['bridge_patterns'].values())}
- VLANs: {NEXTLINK_NAMING['vlan_patterns']['format']}

IP Addressing:
- Loopbacks: {NEXTLINK_IP_RANGES['loopback']['format']}
- Uplinks: {', '.join(NEXTLINK_IP_RANGES['uplink']['formats'])}
- Management VLANs: {json.dumps(NEXTLINK_IP_RANGES['management_vlans'], indent=2)}
- Customer VLANs: Range {NEXTLINK_IP_RANGES['customer_vlans']['range']}

Common NOC Errors to Check:
{chr(10).join([f"- {err['error']} (severity: {err['severity']})" for err in NEXTLINK_COMMON_ERRORS])}

Auto-detectable Errors:
{chr(10).join([f"- {err}" for err in NEXTLINK_AUTO_DETECTABLE_ERRORS])}
"""

        training_context = build_training_context()
        system_prompt = f"""You are a Nextlink NOC MikroTik RouterOS configuration validator. 
Analyze the provided configuration and identify:
1. Syntax errors
2. Missing required fields
3. RFC compliance issues (OSPF RFC 2328, BGP RFC 4271, MPLS RFC 3031, IPv4 RFC 791)
4. Security issues
5. Best practice violations
6. Nextlink-specific standard violations

{nextlink_context}

Return JSON format:
{{
  "valid": true/false,
  "issues": [{{"severity": "error|warning|info", "message": "description", "line": number}}],
  "summary": "brief summary"
}}
"""
        if training_context:
            system_prompt += "\n\n" + training_context

        user_prompt = f"""Validate this RouterOS configuration ({config_type}):

```
{config}
```

Provide validation results in JSON format."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        print(f"[VALIDATE] Calling AI for validation (this may take 10-30 seconds)...")
        result = call_ai(messages, max_tokens=2000, task_type='validation')
        print(f"[VALIDATE] AI response received, parsing...")
        
        # Parse JSON response
        try:
            validation_result = json.loads(result)
        except:
            # Fallback if AI doesn't return pure JSON
            print(f"[VALIDATE] AI response not in JSON format, using fallback")
            validation_result = {
                "valid": True,
                "issues": [],
                "summary": result
            }

        print(f"[VALIDATE] Validation complete, returning results")
        return jsonify({
            'success': True,
            'validation': validation_result
        })

    except Exception as e:
        print(f"[VALIDATE ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ========================================
# ENDPOINT 2: AI Config Suggestions
# ========================================

@app.route('/api/suggest-config', methods=['POST'])
def suggest_config():
    """
    AI suggests config values based on partial input (autocomplete assistant)
    """
    try:
        data = request.json
        
        # Handle both old format (partial_config) and new format (device-based)
        if 'device' in data:
            # New format from frontend
            device = data.get('device', '')
            target_version = data.get('target_version', '')
            loopback_ip = data.get('loopback_ip', '')
            public_cidr = data.get('public_cidr', '')
            bh_cidr = data.get('bh_cidr', '')
            
            # Generate suggestions based on device type
            suggestions = {}
            
            if device == 'ccr2004':
                suggestions = {
                    'public_port': 'sfp-sfpplus7',
                    'nat_port': 'sfp-sfpplus8',
                    'uplink_interface': 'sfp-sfpplus1',
                    'public_pool': f"{public_cidr.split('/')[0].rsplit('.', 1)[0]}.{int(public_cidr.split('/')[0].split('.')[-1]) + 1}-{public_cidr.split('/')[0].rsplit('.', 1)[0]}.{int(public_cidr.split('/')[0].split('.')[-1]) + 2}",
                    'gateway': f"{bh_cidr.split('/')[0].rsplit('.', 1)[0]}.{int(bh_cidr.split('/')[0].split('.')[-1]) - 1}"
                }
            elif device == 'rb5009':
                suggestions = {
                    'public_port': 'ether7',
                    'nat_port': 'ether8',
                    'uplink_interface': 'sfp-sfpplus1',
                    'public_pool': f"{public_cidr.split('/')[0].rsplit('.', 1)[0]}.{int(public_cidr.split('/')[0].split('.')[-1]) + 1}-{public_cidr.split('/')[0].rsplit('.', 1)[0]}.{int(public_cidr.split('/')[0].split('.')[-1]) + 2}",
                    'gateway': f"{bh_cidr.split('/')[0].rsplit('.', 1)[0]}.{int(bh_cidr.split('/')[0].split('.')[-1]) - 1}"
                }
            elif device == 'ccr1036':
                suggestions = {
                    'public_port': 'sfp-sfpplus7',
                    'nat_port': 'sfp-sfpplus8',
                    'uplink_interface': 'sfp-sfpplus1',
                    'public_pool': f"{public_cidr.split('/')[0].rsplit('.', 1)[0]}.{int(public_cidr.split('/')[0].split('.')[-1]) + 1}-{public_cidr.split('/')[0].rsplit('.', 1)[0]}.{int(public_cidr.split('/')[0].split('.')[-1]) + 2}",
                    'gateway': f"{bh_cidr.split('/')[0].rsplit('.', 1)[0]}.{int(bh_cidr.split('/')[0].split('.')[-1]) - 1}"
                }
            
            return jsonify({
                'success': True,
                'public_port': suggestions.get('public_port', ''),
                'nat_port': suggestions.get('nat_port', ''),
                'uplink_interface': suggestions.get('uplink_interface', ''),
                'public_pool': suggestions.get('public_pool', ''),
                'gateway': suggestions.get('gateway', '')
            })
        
        # Old format (legacy)
        partial_config = data.get('partial_config', '')
        config_type = data.get('type', 'tower')
        context = data.get('context', {})  # Customer info, site details, etc.

        training_context = build_training_context()
        system_prompt = """You are a MikroTik RouterOS configuration assistant for NOC operations.
Given partial configuration and context, suggest appropriate values for:
- IP addressing schemes
- OSPF/BGP parameters
- MPLS labels
- Firewall rules
- Interface configurations

Follow these rules:
1. Use RFC-compliant values
2. Maintain consistency with existing network design
3. Suggest private IPs (RFC 1918) for internal networks
4. Use logical OSPF areas and BGP AS numbers
5. Provide explanations for suggestions

Return JSON format:
{
  "suggestions": [{"field": "name", "value": "suggested value", "reason": "why"}],
  "warnings": ["potential issues"]
}
"""
        if training_context:
            system_prompt += "\n\n" + training_context

        user_prompt = f"""Configuration Type: {config_type}
Context: {json.dumps(context, indent=2)}

Partial Configuration:
```
{partial_config}
```

Suggest appropriate values for missing or incomplete fields."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        result = call_ai(messages, max_tokens=2000, task_type='suggestion')

        try:
            suggestions = json.loads(result)
        except:
            suggestions = {"suggestions": [], "warnings": [], "raw": result}

        return jsonify({
            'success': True,
            'suggestions': suggestions
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========================================
# ENDPOINT 3: AI Config Translation
# ========================================

@app.route('/api/translate-config', methods=['POST'])
def translate_config():
    """
    Translates RouterOS config between firmware versions
    """
    try:
        data = request.json
        source_config = data.get('source_config', '')
        target_device = data.get('target_device', '')
        target_version = data.get('target_version', '')

        if not all([source_config, target_device, target_version]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Define helper functions FIRST before using them
        def detect_routeros_syntax(config):
            """Intelligently detect RouterOS version and syntax patterns from config"""
            syntax_info = {
                'version': 'unknown',
                'bgp_syntax': 'unknown',
                'ospf_syntax': 'unknown',
                'parameter_style': 'unknown'
            }
            
            # Detect version from multiple patterns
            if 'by RouterOS 6.' in config or 'RouterOS 6.' in config:
                syntax_info['version'] = '6.x'
            elif 'by RouterOS 7.' in config or 'RouterOS 7.' in config or 'interface-template' in config:
                syntax_info['version'] = '7.x'
            
            # Detect BGP syntax
            if '/routing bgp peer' in config:
                syntax_info['bgp_syntax'] = 'peer'
            elif '/routing bgp connection' in config:
                syntax_info['bgp_syntax'] = 'connection'
            
            # Detect OSPF syntax  
            if '/routing ospf interface add' in config:
                syntax_info['ospf_syntax'] = 'interface'
            elif '/routing ospf interface-template add' in config:
                syntax_info['ospf_syntax'] = 'interface-template'
            
            # Detect parameter style
            if 'remote-address=' in config:
                syntax_info['parameter_style'] = 'dash'
            elif 'remote.address=' in config:
                syntax_info['parameter_style'] = 'dot'
            
            return syntax_info
        
        def get_target_syntax(target_version):
            """Determine target syntax based on RouterOS version"""
            if target_version.startswith('7.'):
                return {
                    'bgp_peer': '/routing bgp connection',
                    'bgp_params': {
                        'remote-address': 'remote.address',
                        'remote-as': 'remote.as',
                        'tcp-md5-key': 'tcp.md5.key',
                        'update-source': 'update.source'
                    },
                    'ospf_interface': '/routing ospf interface-template',
                    'ospf_params': {
                        'interface': 'interfaces'
                    },
                    'bridge_vlan': True
                }
            else:
                return {
                    'bgp_peer': '/routing bgp peer',
                    'bgp_params': {
                        'remote-address': 'remote-address',
                        'remote-as': 'remote-as',
                        'tcp-md5-key': 'tcp-md5-key',
                        'update-source': 'update-source'
                    },
                    'ospf_interface': '/routing ospf interface',
                    'ospf_params': {
                        'interface': 'interface'
                    },
                    'bridge_vlan': False
                }

        def detect_source_device(config):
            """Intelligently detect source device from config patterns"""
            device_info = {
                'model': 'unknown',
                'type': 'unknown',
                'ports': [],
                'management': 'ether1'
            }
            
            # Detect model from config - check more specific patterns first
            # CCR2216: Has sfp28-1 through sfp28-12 (12 sfp28 ports), NO sfp-sfpplus ports
            # CCR2004: Has sfp-sfpplus1-12, plus sfp28-1, sfp28-2 (only 2 sfp28 ports)
            if 'CCR2216' in config or 'MT2216' in config or (config.count('sfp28-') > 3 and 'sfp28-3' in config and 'sfp-sfpplus' not in config):
                device_info['model'] = 'CCR2216-1G-12XS-2XQ'
                device_info['type'] = 'ccr2216'
                device_info['ports'] = ['ether1', 'sfp28-1', 'sfp28-2', 'sfp28-3', 'sfp28-4', 'sfp28-5', 'sfp28-6', 'sfp28-7', 'sfp28-8', 'sfp28-9', 'sfp28-10', 'sfp28-11', 'sfp28-12']
            elif 'CCR1072' in config or ('sfp1' in config and 'sfp2' in config and 'sfp3' in config and 'sfp4' in config and 'sfp-sfpplus' not in config):
                device_info['model'] = 'CCR1072-12G-4S+'
                device_info['type'] = 'ccr1072'
                device_info['ports'] = ['ether1', 'ether2', 'ether3', 'ether4', 'ether5', 'ether6', 'ether7', 'ether8', 'ether9', 'ether10', 'ether11', 'ether12', 'sfp1', 'sfp2', 'sfp3', 'sfp4']
            elif 'CCR1036' in config:
                device_info['model'] = 'CCR1036-12G-4S'
                device_info['type'] = 'ccr1036'
                device_info['ports'] = ['ether1', 'ether2', 'ether3', 'ether4', 'ether5', 'ether6', 'ether7', 'ether8', 'ether9', 'ether10', 'ether11', 'ether12', 'sfp1', 'sfp2', 'sfp3', 'sfp4']
            elif 'CCR2004' in config or 'MT2004' in config or ('sfp-sfpplus' in config and 'sfp28-' not in config.replace('sfp28-1', '').replace('sfp28-2', '')):
                # CCR2004 uses sfp-sfpplus1-12, and has sfp28-1, sfp28-2
                # Check that we have sfp-sfpplus but NOT many sfp28 ports (CCR2216 has sfp28-1 through sfp28-12)
                device_info['model'] = 'CCR2004-1G-12S+2XS'
                device_info['type'] = 'ccr2004'
                device_info['ports'] = ['ether1', 'sfp-sfpplus1', 'sfp-sfpplus2', 'sfp-sfpplus3', 'sfp-sfpplus4', 'sfp-sfpplus5', 'sfp-sfpplus6', 'sfp-sfpplus7', 'sfp-sfpplus8', 'sfp-sfpplus9', 'sfp-sfpplus10', 'sfp-sfpplus11', 'sfp-sfpplus12', 'sfp28-1', 'sfp28-2']
            elif 'CCR2116' in config:
                device_info['model'] = 'CCR2116-12G-4S+'
                device_info['type'] = 'ccr2116'
                device_info['ports'] = ['ether1', 'ether2', 'ether3', 'ether4', 'ether5', 'ether6', 'ether7', 'ether8', 'ether9', 'ether10', 'ether11', 'ether12', 'sfp-sfpplus1', 'sfp-sfpplus2', 'sfp-sfpplus3', 'sfp-sfpplus4']
            elif 'RB5009' in config:
                device_info['model'] = 'RB5009UG+S+'
                device_info['type'] = 'rb5009'
                device_info['ports'] = ['ether1', 'ether2', 'ether3', 'ether4', 'ether5', 'ether6', 'ether7', 'ether8', 'ether9', 'ether10', 'sfp-sfpplus1']
            
            return device_info
        
        def get_target_device_info(target_device):
            """Get target device information dynamically"""
            device_database = {
                'ccr1072': {
                    'model': 'CCR1072-12G-4S+',
                    'type': 'ccr1072',
                    'ports': ['ether1', 'ether2', 'ether3', 'ether4', 'ether5', 'ether6', 'ether7', 'ether8', 'ether9', 'ether10', 'ether11', 'ether12', 'sfp1', 'sfp2', 'sfp3', 'sfp4'],
                    'management': 'ether1',
                    'description': '12x Gigabit + 4x SFP (CCR1072)'
                },
                'ccr2004': {
                    'model': 'CCR2004-1G-12S+2XS',
                    'type': 'ccr2004',
                    'ports': ['ether1', 'sfp-sfpplus1', 'sfp-sfpplus2', 'sfp-sfpplus3', 'sfp-sfpplus4', 'sfp-sfpplus5', 'sfp-sfpplus6', 'sfp-sfpplus7', 'sfp-sfpplus8', 'sfp-sfpplus9', 'sfp-sfpplus10', 'sfp-sfpplus11', 'sfp-sfpplus12', 'sfp28-1', 'sfp28-2'],
                    'management': 'ether1',
                    'description': '1 Gigabit + 12 SFP+ + 2 SFP28'
                },
                'ccr2216': {
                    'model': 'CCR2216-1G-12XS-2XQ',
                    'type': 'ccr2216',
                    # CCR2216: use only SFP28 ports for access; QSFP28 not used in our workflow
                    'ports': ['ether1', 'sfp28-1', 'sfp28-2', 'sfp28-3', 'sfp28-4', 'sfp28-5', 'sfp28-6', 'sfp28-7', 'sfp28-8', 'sfp28-9', 'sfp28-10', 'sfp28-11', 'sfp28-12'],
                    'management': 'ether1',
                    'description': '1 Gigabit + 12 SFP28 + 2 QSFP28 (CCR2216)'
                },
                'ccr1036': {
                    'model': 'CCR1036-12G-4S',
                    'type': 'ccr1036',
                    'ports': ['ether1', 'ether2', 'ether3', 'ether4', 'ether5', 'ether6', 'ether7', 'ether8', 'ether9', 'ether10', 'ether11', 'ether12', 'sfp1', 'sfp2', 'sfp3', 'sfp4'],
                    'management': 'ether1',
                    'description': '12x Gigabit + 4x SFP (CCR1036)'
                },
                'ccr2116': {
                    'model': 'CCR2116-12G-4S+',
                    'type': 'ccr2116',
                    'ports': ['ether1', 'ether2', 'ether3', 'ether4', 'ether5', 'ether6', 'ether7', 'ether8', 'ether9', 'ether10', 'ether11', 'ether12', 'sfp-sfpplus1', 'sfp-sfpplus2', 'sfp-sfpplus3', 'sfp-sfpplus4'],
                    'management': 'ether1',
                    'description': '12x Gigabit + 4x SFP+ (CCR2116)'
                },
                'rb5009': {
                    'model': 'RB5009UG+S+',
                    'type': 'rb5009',
                    'ports': ['ether1', 'ether2', 'ether3', 'ether4', 'ether5', 'ether6', 'ether7', 'ether8', 'ether9', 'ether10', 'sfp-sfpplus1'],
                    'management': 'ether1',
                    'description': '10x Gigabit + 1x SFP+ (RB5009)'
                },
                'rb1009': {
                    'model': 'RB1009UG+S+',
                    'type': 'rb1009',
                    'ports': ['ether1', 'ether2', 'ether3', 'ether4', 'ether5', 'ether6', 'ether7', 'ether8', 'ether9', 'sfp-sfpplus1'],
                    'management': 'ether1',
                    'description': '9x Gigabit + 1x SFP+ (RB1009)'
                }
            }
            
            key = (target_device or '').lower().strip()
            if key in device_database:
                return device_database[key]
            
            # Fallback detection
            if '1072' in key:
                return device_database['ccr1072']
            if '2216' in key:
                return device_database['ccr2216']
            if '2116' in key:
                return device_database['ccr2116']
            if '2004' in key:
                return device_database['ccr2004']
            if '5009' in key:
                return device_database['rb5009']
            
            # Default fallback
            return device_database.get('ccr2004', {
                'model': 'unknown',
                'type': 'unknown',
                'ports': ['ether1'],
                'management': 'ether1',
                'description': 'Unknown device'
            })
        
        # SMART DETECT: Only skip AI if SAME EXACT device model AND same major version
        # CRITICAL: Device changes (e.g., CCR2004 → CCR2216) require AI translation for proper port mapping
        is_source_v7 = ('interface-template' in source_config or 
                       'default-v2' in source_config or
                       'ros7' in source_config.lower())
        is_source_v6 = ('routing ospf interface' in source_config and 
                       'routing ospf instance' not in source_config)
        is_target_v7 = target_version.startswith('7.')
        
        # Detect source device model more precisely
        source_device_info = detect_source_device(source_config)
        target_device_info = get_target_device_info(target_device)
        
        # Only skip AI if SAME EXACT device model (not just same family)
        same_exact_device = (source_device_info['model'] != 'unknown' and 
                             source_device_info['model'] == target_device_info['model'])
        
        if is_source_v7 and is_target_v7 and same_exact_device:
            print(f"[FAST MODE] Same exact device ({source_device_info['model']}), same major version - minimal processing")
            # Just return source with device name update if needed
            translated = source_config
            validation = validate_translation(source_config, translated)
            return jsonify({
                'success': True,
                'translated_config': translated,
                'validation': validation,
                'fast_mode': True,
                'message': 'Config already compatible - no changes needed'
            })
        elif is_source_v7 and is_target_v7 and not same_exact_device:
            print(f"[AI MODE] Device change detected: {source_device_info['model']} → {target_device_info['model']} (both ROS7, but hardware differs - need port mapping)")
        elif is_source_v6 and is_target_v7:
            print(f"[AI MODE] v6 to v7 conversion needed - using AI")
        else:
            print(f"[AI MODE] Device change detected: {source_device_info['model']} → {target_device_info['model']}, using AI")

        # Build Nextlink migration context
        migration_notes = ""
        if '7.' in target_version:
            migration_notes = f"""
NEXTLINK-SPECIFIC MIGRATION NOTES (6.x → 7.x):

OSPF Changes:
- Old: {NEXTLINK_MIGRATION_6X_TO_7X['ospf']['old']}
- New: {NEXTLINK_MIGRATION_6X_TO_7X['ospf']['new']}
- Note: {NEXTLINK_MIGRATION_6X_TO_7X['ospf']['change']}

BGP Changes:
- Old: {NEXTLINK_MIGRATION_6X_TO_7X['bgp']['old']}
- New: {NEXTLINK_MIGRATION_6X_TO_7X['bgp']['new']}
- Note: {NEXTLINK_MIGRATION_6X_TO_7X['bgp']['change']}

Bridge VLAN:
- {NEXTLINK_MIGRATION_6X_TO_7X['bridge_vlan']['change']}
- MANDATORY: {NEXTLINK_MIGRATION_6X_TO_7X['bridge_vlan']['mandatory']}

Interface Naming:
- {NEXTLINK_MIGRATION_6X_TO_7X['interface_naming']['change']}
- {NEXTLINK_MIGRATION_6X_TO_7X['interface_naming']['note']}

Port Roles:
- {NEXTLINK_MIGRATION_6X_TO_7X['port_roles']['change']}
- {NEXTLINK_MIGRATION_6X_TO_7X['port_roles']['note']}
"""

        # INTELLIGENT ROUTEROS SYNTAX DETECTION AND LEARNING
        # (Functions already defined above, no need to redefine)

        def extract_loopback_ip(config_text):
            """Extract loopback IP (interface=loop0) without mask if present; fallback to router-id."""
            # Try interface=loop0 address first
            m = re.search(r"/ip address add[^\n]*address=(\d+\.\d+\.\d+\.\d+)(?:/\d+)?[^\n]*interface=loop0", config_text)
            if m:
                return m.group(1)
            # Fallback to router-id in BGP/OSPF instance
            m = re.search(r"router-id=(\d+\.\d+\.\d+\.\d+)", config_text)
            if m:
                return m.group(1)
            return None

        def postprocess_to_v7(translated_text, target_version):
            """Normalize output to RouterOS v7 syntax for BGP/OSPF and parameters regardless of AI path."""
            if not target_version.startswith('7.'):
                return translated_text

            text = translated_text

            # Unwrap RouterOS line continuations and clean spacing
            # Prefer joining WITHOUT a space when the break is in the middle of a token
            # 1) mid-token joins: non-space before and after the break
            text = re.sub(r"(?<=\S)\\\r?\n\s*(?=\S)", "", text)
            # 2) remaining continuations join with a single space
            text = re.sub(r"\\\r?\n\s*", " ", text)
            # Remove stray trailing backslashes
            text = re.sub(r"(?m)\\\s*$", "", text)
            # Remove stray trailing backslashes
            text = re.sub(r"(?m)\\\s*$", "", text)
            # Collapse multiple blank lines
            text = re.sub(r"\n{3,}", "\n\n", text)

            # Remove placeholder BREAK marker lines and comments
            text = re.sub(r"(?m)^.*\bchain=break\b.*$", "", text)
            text = re.sub(r"(?m)^.*\bcomment(?:s)?=([\"'])?[^\n]*?BREAK[^\n]*\1.*$", "", text)

            # Normalize spacing around '=' and collapse excessive spaces per line
            norm_lines = []
            for raw_line in text.splitlines():
                line = re.sub(r"=\s+", "=", raw_line)
                line = re.sub(r"\s{2,}", " ", line)
                norm_lines.append(line.rstrip())
            text = "\n".join(norm_lines)

            # --- BGP normalizations ---
            # instance -> template
            if re.search(r"(?m)^/routing bgp ", text):
                text = re.sub(r"(?m)^/routing bgp instance", "/routing bgp template", text)
            # ensure 'set default' lines use template
            text = re.sub(r"(?m)^/routing bgp template\s+set\s+default(.*)$", lambda m: f"/routing bgp template set default{m.group(1)}", text)

            # parameter key migrations
            param_map = {
                'remote-address=': 'remote.address=',
                'remote-as=': 'remote.as=',
                'tcp-md5-key=': 'tcp.md5.key=',
                'update-source=': 'update.source=',
                'local-address=': 'local.address='
            }
            for old, new in param_map.items():
                text = text.replace(old, new)

            # peer -> connection
            text = text.replace('/routing bgp peer', '/routing bgp connection')

            # Filters: v6 'in-filter/out-filter' -> v7 'input.filter/output.filter'
            # Per requirement: DO NOT set any BGP input/output filter on ROS7 (avoid loops)
            # Remove any existing v6 or v7 filter parameters from bgp connection lines
            def strip_bgp_filters(m):
                line = m.group(0)
                line = re.sub(r"\s(?:in-filter|out-filter|input\.filter|output\.filter)=[^\s]+", "", line)
                line = re.sub(r"\s{2,}", " ", line).rstrip()
                return line
            if re.search(r"(?m)^/routing bgp ", text):
                text = re.sub(r"(?m)^/routing bgp connection\s+(?:add|set)\b[^\n]*$", strip_bgp_filters, text)

            # update.source should use IP, not interface name
            lb_ip = extract_loopback_ip(text)
            if lb_ip:
                text = re.sub(r"update\.source=([A-Za-z0-9_.-]+)", f"update.source={lb_ip}", text)

            # Ensure there is exactly one '/routing bgp template set default' with key IP fields
            def ensure_template_set_default(t):
                tpl_line = None
                out_lines = []
                for l in t.splitlines():
                    if re.match(r"^/routing bgp template\s+set\s+default\b", l):
                        tpl_line = l
                        continue
                    out_lines.append(l)
                # Build normalized default line
                base = "/routing bgp template set default disabled=no multihop=yes output.network=bgp-networks routing-table=main"
                if lb_ip:
                    base += f" local.address={lb_ip} router-id={lb_ip} update.source={lb_ip}"
                # Re-add at top of routing bgp template section
                out_text = "\n".join(out_lines)
                return base + "\n" + out_text if base not in out_text else out_text

            # Only ensure defaults if BGP exists in the source
            if re.search(r"(?m)^/routing bgp ", text):
                text = ensure_template_set_default(text)
                # Move template 'set default' to immediately after the last connection add
                def _reorder_bgp(t: str) -> str:
                    lines = t.splitlines()
                    tpl_positions = [i for i,l in enumerate(lines) if re.match(r"^/routing bgp template\s+set\s+default\b", l)]
                    conn_positions = [i for i,l in enumerate(lines) if re.match(r"^/routing bgp connection\s+add\b", l)]
                    if not tpl_positions or not conn_positions:
                        return t
                    tpl_line = lines[tpl_positions[0]]
                    del lines[tpl_positions[0]]
                    insert_at = conn_positions[-1] + 1
                    lines.insert(insert_at, tpl_line)
                    return "\n".join(lines)
                text = _reorder_bgp(text)

            # Ensure BGP template defaults exist and include ROS7 recommended fields
            def normalize_bgp_template(line: str, lb_ip_val: str, asn_val: str) -> str:
                if asn_val and ' as=' not in line:
                    line += f' as={asn_val}'
                if ' disabled=' not in line:
                    line += ' disabled=no'
                if ' multihop=' not in line:
                    line += ' multihop=yes'
                if ' output.network=' not in line:
                    line += ' output.network=bgp-networks'
                if lb_ip_val and ' router-id=' not in line:
                    line += f' router-id={lb_ip_val}'
                if ' routing-table=' not in line:
                    line += ' routing-table=main'
                return line

            # derive ASN from existing config if possible
            asn_match = re.search(r"(?m)\bas=(\d+)\b", text)
            asn_val = asn_match.group(1) if asn_match else ''

            if re.search(r"(?m)^/routing bgp template\s+set\s+default", text):
                text = re.sub(r"(?m)^(/routing bgp template\s+set\s+default[^\n]*)$",
                              lambda m: normalize_bgp_template(m.group(1), lb_ip, asn_val),
                              text)
            else:
                # Do not add a BGP template line if there is no BGP section at all
                pass

            # Normalize each BGP connection add line
            def normalize_bgp_connection(m):
                line = m.group(0)
                if ' output.network=' not in line:
                    line += ' output.network=bgp-networks'
                if lb_ip and ' local.address=' not in line:
                    line += f' local.address={lb_ip}'
                if lb_ip and ' router-id=' not in line:
                    line += f' router-id={lb_ip}'
                if ' routing-table=' not in line:
                    line += ' routing-table=main'
                if ' templates=' not in line:
                    line += ' templates=default'
                if ' multihop=' not in line:
                    line += ' multihop=yes'
                if ' connect=' not in line:
                    line += ' connect=yes'
                if ' listen=' not in line:
                    line += ' listen=yes'
                # Enforce /32 remote.address if missing mask
                line = re.sub(r"remote\.address=(\d+\.\d+\.\d+\.\d+)(?!/\d+)", r"remote.address=\1/32", line)
                return line

            if re.search(r"(?m)^/routing bgp ", text):
                text = re.sub(r"(?m)^/routing bgp connection\s+add\b[^\n]*$", normalize_bgp_connection, text)

            # Convert '/routing bgp network' entries into address-list 'bgp-networks' and remove them
            if re.search(r"(?m)^/routing bgp ", text):
                nets = set(re.findall(r"(?m)^/routing bgp network\s+add\s+[^\n]*?network=([^\s]+)", text))
                if nets:
                    # Remove header and add lines
                    text = re.sub(r"(?m)^/routing bgp network\s*$\n?", "", text)
                    text = re.sub(r"(?m)^/routing bgp network\s+add\b[^\n]*\n?", "", text)
                    # Ensure address-list exists for each network
                    for net in nets:
                        if not re.search(rf"(?m)^/ip firewall address-list\s+add\s+address={re.escape(net)}\s+list=bgp-networks\b", text):
                            text += f"\n/ip firewall address-list add address={net} list=bgp-networks"

            # --- OSPF normalizations ---
            # Fix accidental slash-separated hierarchy to spaced hierarchy
            if re.search(r"(?m)^/routing ospf ", text):
                text = re.sub(r"(?m)^/routing/ospf/interface-template\b", "/routing ospf interface-template", text)
                text = re.sub(r"(?m)^/routing/ospf/interface\b", "/routing ospf interface-template", text)
                text = re.sub(r"(?m)^/routing ospf interface\b", "/routing ospf interface-template", text)

            # instance default to default-v2 add
            if re.search(r"(?m)^/routing ospf ", text):
                text = re.sub(r"(?ms)^/routing ospf instance\s+set\s+\[\s*find\s+default=yes\s*\]\s+router-id=(\d+\.\d+\.\d+\.\d+).*?$",
                              r"/routing ospf instance add disabled=no name=default-v2 router-id=\1", text)

            # interface -> interface-template (OSPF only)
            if re.search(r"(?m)^/routing ospf ", text):
                text = text.replace('/routing ospf interface add', '/routing ospf interface-template add')

            # Prefix orphan OSPF interface-template 'add' lines without header
            # e.g., lines that start with 'add area=... interfaces=...' or 'add area=... networks=...'
            if re.search(r"(?m)^/routing ospf ", text):
                text = re.sub(r"(?m)^(add\s+[^\n]*\barea=\S+[^\n]*(?:\binterfaces?=|\bnetworks=)[^\n]*)$",
                              r"/routing ospf interface-template \1", text)

            # Replace interface= to interfaces= ONLY on OSPF interface-template lines
            def ospf_iface_params(m):
                line = m.group(0)
                line = re.sub(r'\binterface=', 'interfaces=', line)
                return line
            if re.search(r"(?m)^/routing ospf ", text):
                text = re.sub(r"(?m)^/routing ospf interface-template\s+add\b[^\n]*$", ospf_iface_params, text)

            # Force-convert any leftover v6-style OSPF interface lines to v7 interface-template
            if re.search(r"(?m)^/routing ospf interface\s+add\b", text):
                def v6_to_v7_iface(m):
                    ln = m.group(0).replace('/routing ospf interface add', '/routing ospf interface-template add')
                    ln = re.sub(r'\bauthentication=', 'auth=', ln)
                    ln = re.sub(r'\bauthentication-key=', 'auth-key=', ln)
                    ln = re.sub(r'\bnetwork-type=point-to-point', 'type=ptp', ln)
                    ln = re.sub(r'\binterface=', 'interfaces=', ln)
                    if ' cost=' not in ln and ' type=ptp' in ln:
                        ln += ' cost=10'
                    if ' disabled=' not in ln:
                        ln += ' disabled=no'
                    return ln
                text = re.sub(r"(?m)^/routing ospf interface\s+add\b[^\n]*$", v6_to_v7_iface, text)

            # Fix unintended pluralization outside OSPF context
            # in-interfaces/out-interfaces -> singular
            text = re.sub(r"\bin-interfaces=", "in-interface=", text)
            text = re.sub(r"\bout-interfaces=", "out-interface=", text)
            # generic interfaces= -> interface= on non-OSPF lines
            def depluralize_non_ospf(m):
                line = m.group(0)
                if line.startswith('/routing ospf interface-template'):
                    return line
                return line.replace('interfaces=', 'interface=')
            text = re.sub(r"(?m)^.*\binterfaces=[^\n]*$", depluralize_non_ospf, text)
            # parameter key migrations
            text = text.replace('authentication=', 'auth=')
            text = text.replace('authentication-key=', 'auth-key=')
            text = text.replace('network-type=point-to-point', 'type=ptp')

            # Convert old network statements to interface-template networks= form (preserve source area)
            if re.search(r"(?m)^/routing ospf ", text):
                text = re.sub(r"(?m)^/routing ospf network\s+add\s+area=([^\s]+)\s+network=([^\s]+)$",
                              r"/routing ospf interface-template add area=\1 networks=\2", text)

            # Detect declared OSPF area names (use first as primary when we need a default)
            declared_areas = re.findall(r"(?m)^/routing ospf area\s+add\s+[^\n]*\bname=([^\s]+)", text)
            primary_area = declared_areas[0] if declared_areas else None

            # Normalize all interface-template lines (area, disabled, networks for loopback)
            def normalize_ospf_iface_tmpl(m):
                line = m.group(0)
                # Preserve existing area; if missing and we detected one, set it
                if ' area=' not in line and primary_area:
                    line = line.replace('add ', f'add area={primary_area} ', 1)
                if ' disabled=' not in line:
                    line += ' disabled=no'
                if 'interfaces=loop0' in line and 'networks=' not in line:
                    lb = extract_loopback_ip(text)
                    if lb:
                        line += f' networks={lb}/32 passive priority=1'
                if ' auth=md5' in line and ' auth-id=' not in line:
                    line += ' auth-id=1'
                return line

            if re.search(r"(?m)^/routing ospf ", text):
                text = re.sub(r"(?m)^/routing ospf interface-template\s+add\b[^\n]*$", normalize_ospf_iface_tmpl, text)

            # Remove legacy '/routing ospf network' block remnants
            if re.search(r"(?m)^/routing ospf ", text):
                text = re.sub(r"(?m)^/routing ospf network\s*$\n?", "", text)
                text = re.sub(r"(?m)^/routing ospf network\s+add\b[^\n]*\n?", "", text)

            # Consolidate all OSPF interface-template lines under a single header block
            ospf_iface_lines = re.findall(r"(?m)^/routing ospf interface-template\s+add[^\n]*$", text)
            # Also capture orphan lines like 'add area=...' that were emitted under wrong headers (e.g. after /radius)
            orphan_iface_adds = re.findall(r"(?m)^(add\s+[^\n]*\barea=\S+[^\n]*)$", text)
            # Capture additional orphan OSPF interface lines that contain OSPF-specific tokens ONLY
            # Require at least one of: auth=, area=, networks=, passive, priority
            # Explicitly exclude VLAN/bridge/VPLS/DHCP style tokens to avoid misclassification
            orphan_iface_auth_adds = []
            for l in re.findall(r"(?m)^(add\s+[^\n]+)$", text):
                if re.search(r"\b(auth=|area=|networks=|passive\b|priority=)", l):
                    if re.search(r"\b(vlan\-id=|bridge=|horizon=|name=|add\-default\-route=|use\-peer\-(dns|ntp)=|remote\-peer=|peer=)\b", l):
                        continue
                    orphan_iface_auth_adds.append(l)
            if orphan_iface_adds:
                # Remove orphans from original locations and normalize params
                text = re.sub(r"(?m)^add\s+[^\n]*\barea=\S+[^\n]*\n?", "", text)
                def normalize_orphan_ospf(l: str) -> str:
                    ln = re.sub(r"\binterface=", "interfaces=", l)
                    # If area missing and primary_area known, set it
                    if ' area=' not in ln and primary_area:
                        ln = ln.replace('add ', f'add area={primary_area} ', 1)
                    # disabled=no if missing
                    if ' disabled=' not in ln:
                        ln += ' disabled=no'
                    # md5 -> auth-id=1 if missing
                    if ' auth=md5' in ln and ' auth-id=' not in ln:
                        ln += ' auth-id=1'
                    return f"/routing ospf interface-template {ln}"
                for l in orphan_iface_adds:
                    ospf_iface_lines.append(normalize_orphan_ospf(l))
            if orphan_iface_auth_adds:
                # Exclude lines that are clearly not OSPF (e.g., contain radius-specific tokens)
                filtered = []
                for l in orphan_iface_auth_adds:
                    if re.search(r"\b(secret=|service=)\b", l):
                        continue
                    filtered.append(l)
                if filtered:
                    # Remove them from original positions
                    for l in filtered:
                        # Escape for regex removal
                        esc = re.escape(l)
                        text = re.sub(rf"(?m)^{esc}\n?", "", text)
                    # Normalize to OSPF interface-template add lines
                    for l in filtered:
                        ln = re.sub(r"\binterface=", "interfaces=", l)
                        if ' disabled=' not in ln:
                            ln += ' disabled=no'
                        if ' interfaces=' in ln and 'interfaces=loop0' not in ln and ' type=' not in ln:
                            ln += ' type=ptp'
                        if ' type=ptp' in ln and ' cost=' not in ln:
                            ln += ' cost=10'
                        if ' auth=md5' in ln and ' auth-id=' not in ln:
                            ln += ' auth-id=1'
                        ospf_iface_lines.append(f"/routing ospf interface-template {ln}")
            if ospf_iface_lines:
                # Remove any existing headers (with or without trailing text) and scattered add lines
                text = re.sub(r"(?m)^/routing ospf interface-template\b[^\n]*\n?", "", text)
                text = re.sub(r"(?m)^/routing ospf interface-template\s+add[^\n]*\n?", "", text)

                # Clean header prefixes and normalize token order for stable de-duplication
                def normalize_ospf_add_line(line: str) -> str:
                    line = re.sub(r"^/routing ospf interface-template\s+", "", line)
                    if not line.startswith('add '):
                        line = 'add ' + line
                    # Ensure interfaces/networks normalizations already applied
                    # Normalize token ordering for consistent de-dup
                    tokens = dict(re.findall(r"(\w[\w\.-]*)=([^\s]+)", line))
                    order = ['area','interfaces','networks','auth','auth-key','auth-id','type','cost','passive','priority','disabled','comment','address']
                    parts = ['add']
                    for k in order:
                        if k in tokens:
                            parts.append(f"{k}={tokens[k]}")
                    # Append any remaining tokens deterministically
                    for k in sorted(tokens.keys()):
                        if k not in order:
                            parts.append(f"{k}={tokens[k]}")
                    return ' '.join(parts)

                cleaned_lines = [normalize_ospf_add_line(l) for l in ospf_iface_lines]

                # De-duplicate while preserving order (by normalized content)
                seen = set()
                unique_lines = []
                for l in cleaned_lines:
                    if l not in seen:
                        seen.add(l)
                        unique_lines.append(l)

                consolidated = "/routing ospf interface-template\n" + "\n".join(unique_lines) + "\n"

                # Find best insertion point: after the last OSPF area/instance line
                insert_pos = 0
                last_matches = [m.end() for m in re.finditer(r"(?m)^/routing ospf (area|instance)\b[^\n]*$", text)]
                if last_matches:
                    insert_pos = last_matches[-1]
                else:
                    # If no area/instance found, append at end
                    insert_pos = len(text)

                text = text[:insert_pos] + ("\n" if insert_pos and text[insert_pos-1] != "\n" else "") + consolidated + text[insert_pos:]
                # Collapse accidental duplicate headers
                text = re.sub(r"(?m)^(?:/routing ospf interface-template\s*\n){2,}", "/routing ospf interface-template\n", text)

                # Enhance OSPF block lines using /ip address mappings for interfaces
                # Build network -> interface map from '/ip address add' lines
                net_to_iface = {}
                for ip_line in re.findall(r"(?m)^/ip address\s+add\b[^\n]*$", text):
                    m_net = re.search(r"\bnetwork=(\d+\.\d+\.\d+\.\d+/(?:\d+))", ip_line)
                    m_if = re.search(r"\binterface=([^\s]+)", ip_line)
                    if m_net and m_if:
                        net_to_iface[m_net.group(1)] = m_if.group(1)

                def process_ospf_block(match):
                    body = match.group(1)
                    seen_lines: set[str] = set()
                    out: list[str] = []

                    # Helper: final whitelist of OSPF params
                    def strip_non_ospf_params(s: str) -> str:
                        allowed = [
                            'area', 'interfaces', 'networks', 'auth', 'auth-key', 'auth-id',
                            'type', 'cost', 'passive', 'priority', 'disabled', 'comment', 'address'
                        ]
                        def repl(m):
                            key = m.group(1)
                            return '' if key not in allowed else m.group(0)
                        s = re.sub(r"\s(\w[\w\.-]*)=\S+", repl, s)
                        s = re.sub(r"\s{2,}", " ", s).rstrip()
                        return s

                    for ln in body.splitlines():
                        if not ln.strip():
                            continue
                        # Hard exclude non-OSPF content that may have slipped in
                        if re.search(r"\b(vlan\-id=|\bname=vlan|\bbridge=|\bhorizon=|\badd\-default\-route=|\buse\-peer\-(dns|ntp)=|\b(remote\.)?peer=|\bvpls|\bmac\-address=|\bmtu=|\bpw\-)", ln):
                            continue
                        # force interfaces= using network mapping if missing
                        if (' networks=' in ln or ' network=' in ln) and ' interfaces=' not in ln:
                            mnet = re.search(r"networks=(\d+\.\d+\.\d+\.\d+/(?:\d+))|network=(\d+\.\d+\.\d+\.\d+/(?:\d+))", ln)
                            if mnet:
                                net_val = mnet.group(1) or mnet.group(2)
                                iface = net_to_iface.get(net_val)
                                if iface:
                                    ln += f" interfaces={iface}"
                        # singular -> plural on OSPF lines
                        ln = re.sub(r"\binterface=", "interfaces=", ln)
                        # add type/cost defaults
                        if ' interfaces=' in ln and 'interfaces=loop0' not in ln and ' type=' not in ln:
                            ln += ' type=ptp'
                        if ' type=ptp' in ln and ' cost=' not in ln:
                            ln += ' cost=10'
                        if ' disabled=' not in ln:
                            ln += ' disabled=no'
                        # Whitelist
                        ln = strip_non_ospf_params(ln)
                        # de-dup exact lines
                        if ln and ln not in seen_lines:
                            seen_lines.add(ln)
                            out.append(ln)
                    return "/routing ospf interface-template\n" + "\n".join(out) + "\n"

                # Normalize ' network=' to ' networks=' within OSPF block lines
                text = re.sub(r"(?m)^/routing ospf interface-template\s+add\b[^\n]*\bnetwork=", lambda m: m.group(0).replace(' network=', ' networks='), text)

                text = re.sub(r"(?ms)^/routing ospf interface-template\s*\n((?:add[^\n]*\n)+)", process_ospf_block, text)

            # DNS vs address-lists: move any '/ip dns add address=' lines into firewall address-lists
            # Example wrong: /ip dns add address=1.2.3.4 list=SNMP
            # Correct:       /ip firewall address-list add address=1.2.3.4 list=SNMP
            def move_dns_address_adds(m):
                body = m.group(1)
                # keep only address and list keys
                addr = re.search(r"address=([^\s]+)", body)
                lst = re.search(r"list=([^\s]+)", body)
                if not addr or not lst:
                    return ''
                return f"/ip firewall address-list add address={addr.group(1)} list={lst.group(1)}"
            text = re.sub(r"(?m)^/ip dns\s+add\s+([^\n]+)$", move_dns_address_adds, text)

            # Consolidate RADIUS lines to live only under '/radius'
            # Capture original positions before removal for stable reinsertion
            radius_positions = [m.start() for m in re.finditer(r"(?m)^/radius\b.*$", text)]
            radius_adds = re.findall(r"(?m)^/radius\s+add\b[^\n]*$", text)
            orphan_radius_adds = re.findall(r"(?m)^(add\s+[^\n]*\baddress=\d+\.\d+\.\d+\.\d+[^\n]*(?:\bsecret=|\bservice=)[^\n]*)$", text)
            if radius_adds or orphan_radius_adds:
                # Remove existing header-only and add lines, plus orphan radius-style adds
                text = re.sub(r"(?m)^/radius\s*$\n?", "", text)
                text = re.sub(r"(?m)^/radius\s+add\b[^\n]*\n?", "", text)
                text = re.sub(r"(?m)^(add\s+[^\n]*\baddress=\d+\.\d+\.\d+\.\d+[^\n]*(?:\bsecret=|\bservice=)[^\n]*)\n?", "", text)
                # Remove any leftover header-only lines created by the removals
                text = re.sub(r"(?m)^/radius\s*$\n?", "", text)

                # De-duplicate and build radius block
                seen_r = set()
                merged = []
                for l in radius_adds + [f"/radius {l}" if not l.startswith('/radius') else l for l in orphan_radius_adds]:
                    # Normalize orphan to '/radius add ...'
                    if l.startswith('/radius add'):
                        norm = l
                    else:
                        norm = l.replace('/radius ', '/radius add ', 1) if l.startswith('/radius ') else f"/radius {l}"
                    norm = norm.replace('/radius add add ', '/radius add ')
                    # Strictly keep only valid RADIUS fields; exclude any OSPF-like tokens accidentally captured
                    if not re.search(r"\baddress=\d+\.\d+\.\d+\.\d+", norm):
                        continue
                    if not re.search(r"\b(secret=|service=)", norm):
                        continue
                    if re.search(r"\b(auth=|auth-key=|interfaces?=|area=|networks?=|type=ptp|cost=)", norm):
                        continue
                    if norm not in seen_r:
                        seen_r.add(norm)
                        merged.append(norm)
                if merged:
                    # Emit only 'add ...' lines under a single header
                    lines_only = [re.sub(r"^/radius\s+", "", x) for x in merged]
                    radius_block = "/radius\n" + "\n".join(lines_only) + "\n"
                    # Reinsertion point: earliest prior '/radius' position if any, else before first '/user ' or at top
                    if radius_positions:
                        ins = radius_positions[0]
                    else:
                        u = re.search(r"(?m)^/user\b", text)
                        ins = u.start() if u else 0
                    text = text[:ins] + radius_block + text[ins:]
                    # Collapse duplicate consecutive '/radius' headers
                    text = re.sub(r"(?m)^(?:/radius\s*\n){2,}", "/radius\n", text)
                    # De-duplicate identical radius add lines
                    def dedup_radius_block(m):
                        body = m.group(1)
                        seen = set()
                        out = []
                        for ln in body.splitlines():
                            if not ln.strip():
                                continue
                            if ln not in seen:
                                seen.add(ln)
                                out.append(ln)
                        return "/radius\n" + "\n".join(out) + "\n"
                    text = re.sub(r"(?ms)^/radius\s*\n((?:add[^\n]*\n)+)", dedup_radius_block, text)

            # --- VPLS normalizations (dynamic) ---
            # Rehome orphan VPLS 'add' lines missing the header
            text = re.sub(r"(?m)^(add\s+[^\n]*(?:cisco\-static\-id|cisco\-style\-id|remote\-peer|peer)=[^\n]*)$",
                          r"/interface vpls \1", text)
            def normalize_vpls_line(m):
                src = m.group(0)
                body = src.split(' ', 3)[-1]  # after '/interface vpls add'
                kv = dict(re.findall(r"([A-Za-z0-9_.\-]+)=([^\s]+)", body))
                # Derive identifiers
                peer = kv.get('peer') or kv.get('remote-peer') or ''
                name = kv.get('name', '')
                mac = kv.get('mac-address', '')
                disabled = kv.get('disabled', 'no')
                # static id from cisco-style-id or cisco-static-id or from name
                static_id_val = kv.get('cisco-style-id') or kv.get('cisco-static-id')
                if static_id_val is None:
                    m_name = re.search(r"vpls(\d+)", name or '')
                    static_id_val = m_name.group(1) if m_name else ''
                # bridge thousand grouping
                bridge_part = ''
                if static_id_val and static_id_val.isdigit():
                    base = (int(static_id_val) // 1000) * 1000
                    if base > 0:
                        bridge_part = f"bridge=bridge{base} "
                # pw-l2mtu from existing values
                pw_l2mtu = kv.get('pw-l2mtu')
                if not pw_l2mtu:
                    m_l2 = re.search(r"\b(advertised-)?l2mtu=(\d+)", body)
                    pw_l2mtu = m_l2.group(2) if m_l2 else '1580'
                mtu = kv.get('mtu', '1500')
                # Build canonical line
                parts = [
                    '/interface vpls add',
                    'arp=enabled',
                    bridge_part + 'bridge-horizon=1' if bridge_part else 'bridge-horizon=1',
                ]
                if static_id_val:
                    parts.append(f'cisco-static-id={static_id_val}')
                parts.append(f'disabled={disabled}')
                if mac:
                    parts.append(f'mac-address={mac}')
                parts.append(f'mtu={mtu}')
                if name:
                    parts.append(f'name={name}')
                if peer:
                    parts.append(f'peer={peer}')
                parts.append('pw-control-word=disabled')
                parts.append(f'pw-l2mtu={pw_l2mtu}')
                parts.append('pw-type=raw-ethernet')
                return ' '.join(parts).strip()

            # Remove ROS6-style tokens before rebuilding
            text = re.sub(r"\s\badvertised-l2mtu=\S+", "", text)
            text = re.sub(r"\s\bl2mtu=\S+", "", text)
            text = re.sub(r"\s\bcisco-style=yes\b", "", text)
            text = re.sub(r"\bcisco-style-id=(\d+)", r"cisco-static-id=\1", text)
            text = re.sub(r"(?m)^/interface vpls\s+add\b[^\n]*$", normalize_vpls_line, text)

            # --- LDP instance (for MPLS/VPLS) ---
            # If MPLS/VPLS is present, ensure an LDP instance uses the loopback/router-id
            if re.search(r"(?m)^/interface vpls\b|^/mpls\b", text) and lb_ip:
                def normalize_ldp_instance(m):
                    l = m.group(0)
                    if ' lsr-id=' not in l:
                        l += f' lsr-id={lb_ip}'
                    else:
                        l = re.sub(r"lsr-id=\S+", f"lsr-id={lb_ip}", l)
                    if ' transport-addresses=' not in l:
                        l += f' transport-addresses={lb_ip}'
                    else:
                        l = re.sub(r"transport-addresses=\S+", f"transport-addresses={lb_ip}", l)
                    if ' vrf=' not in l:
                        l += ' vrf=main'
                    if ' afi=' not in l:
                        l += ' afi=ip'
                    return l

                if re.search(r"(?m)^/mpls ldp instance\s+(?:add|set)\b", text):
                    text = re.sub(r"(?m)^/mpls ldp instance\s+(?:add|set)\b[^\n]*$", normalize_ldp_instance, text)
                else:
                    text += f"\n/mpls ldp instance add lsr-id={lb_ip} transport-addresses={lb_ip} vrf=main afi=ip"

            # --- Generic block consolidation & formatting ---
            # Goal: avoid scattered one-liners; group add-lines under a single header for safe sections
            # Normalize terminal-prompt artifacts from pasted CLI transcripts
            # 1) Strip leading router prompts like: [admin@RTR-XYZ] 
            text = re.sub(r"(?m)^\s*\[[^\]]+\]\s*", "", text)
            # 2) Convert '/path/subpath> add ...' → '/path subpath add ...'
            def fix_cli_path(m):
                p1 = m.group(1)
                p2 = m.group(2)
                rest = m.group(3)
                return f"/{p1} {p2} add {rest}".strip()
            text = re.sub(r"(?mi)^\s*/([a-z0-9\-]+)/([a-z0-9\-]+)>\s*add\s+(.*)$", fix_cli_path, text)
            # 3) Remove stray '>' characters that sometimes trail the header
            text = re.sub(r"(?m)^(/{1}[A-Za-z0-9\-]+(?:\s+[A-Za-z0-9\-]+)?)>\s*$", r"\1", text)

            # 4) Harden RADIUS: keep only real RADIUS server lines; re-home everything else
            def fix_radius_line(m):
                line = m.group(0)
                body = line.split(' ', 2)[-1]
                has_addr = 'address=' in body
                has_secret = 'secret=' in body
                has_service = 'service=' in body
                # Valid RADIUS server definition requires address and secret, service optional
                if has_addr and has_secret:
                    return line
                # Otherwise strip the '/radius ' prefix so orphan routing can re-home it
                return re.sub(r"^/radius\s+", "", line)

            text = re.sub(r"(?m)^/radius\s+add\b[^\n]*$", fix_radius_line, text)
            # Normalize BGP remote.address to strip CIDR if present (ROS7 expects pure IP)
            text = re.sub(r"(?m)(remote\.address=)(\d+\.\d+\.\d+\.\d+)/(?:3[0-2]|[12]?\d)", r"\1\2", text)
            # Re-home orphan lines missing their headers so we always have proper block headers
            # NAT orphans → '/ip firewall nat add ...'
            text = re.sub(r"(?m)^\s*(add\s+[^\n]*\b(chain=srcnat|chain=dstnat|action=(src\-nat|dst\-nat))\b[^\n]*)$",
                          r"/ip firewall nat \1", text)
            # Address-list orphans → '/ip firewall address-list add ...' (address and list tokens only, ignore src-address/dst-address/dst-address-list)
            # Require standalone tokens preceded by start or whitespace to avoid matching 'src-address=' or 'dst-address='
            text = re.sub(r"(?m)^\s*(add\s+[^\n]*(?:(?:(?:^|\s)list=\S+)\s+[^\n]*(?:(?:^|\s)address=\S+)|(?:(?:^|\s)address=\S+)\s+[^\n]*(?:(?:^|\s)list=\S+))[^\n]*)$",
                          r"/ip firewall address-list \1", text)
            # DHCP network orphans → '/ip dhcp-server network add ...'
            # Recognize typical network lines with address + dns-server(s) + gateway (+ optional netmask)
            text = re.sub(r"(?m)^\s*(add\s+[^\n]*\baddress=\S+[^\n]*\b(dns-server|dns-servers)=\S+[^\n]*\bgateway=\S+[^\n]*(?:\bnetmask=\S+)?[^\n]*)$",
                          r"/ip dhcp-server network \1", text)
            # Filter-rule orphans → '/ip firewall filter add ...'
            text = re.sub(r"(?m)^\s*(add\s+[^\n]*\bchain=(input|forward|output)\b[^\n]*\baction=\S+[^\n]*)$",
                          r"/ip firewall filter \1", text)
            # Mangle orphans → '/ip firewall mangle add ...' (only when clear mangle actions/marks are present)
            text = re.sub(r"(?m)^\s*(add\s+[^\n]*((?=([^\n]*\baction=(mark\-connection|mark\-packet|change\-dscp|jump)\b))|([^\n]*\bnew\-connection\-mark=)|([^\n]*\bnew\-packet\-mark=))[^\n]*)$",
                          r"/ip firewall mangle \1", text)
            # Queue tree orphans → '/queue tree add ...' (name + parent, but not firewall 'chain=')
            text = re.sub(r"(?m)^\s*(add\s+(?=.*\bname=)(?=.*\bparent=)(?!.*\bchain=)[^\n]*)$",
                          r"/queue tree \1", text)
            # Bridge port orphans → '/interface bridge port add ...'
            text = re.sub(r"(?m)^\s*(add\s+[^\n]*\bbridge=\S+\s+[^\n]*\binterface=\S+[^\n]*)$",
                          r"/interface bridge port \1", text)
            def consolidate_block(t: str, header: str) -> str:
                # Collect all '/header add ...' lines
                pattern_add = rf"(?m)^" + re.escape(header) + r"\s+add\b[^\n]*$"
                add_lines = re.findall(pattern_add, t)
                if not add_lines:
                    return t
                # Remove existing header-only lines and add-lines for this header
                t = re.sub(rf"(?m)^" + re.escape(header) + r"\s*$\n?", "", t)
                t = re.sub(pattern_add + "\n?", "", t)
                # Normalize collected lines to 'add ...' (strip header prefix)
                cleaned = [re.sub(rf"^" + re.escape(header) + r"\s+", "", ln) for ln in add_lines]
                # De-duplicate while preserving order
                seen = set()
                unique = []
                for ln in cleaned:
                    if ln not in seen:
                        seen.add(ln)
                        unique.append(ln)
                block = header + "\n" + "\n".join(unique) + "\n"
                # Insert block near the first occurrence of any sibling header, else append
                insert_pos = 0
                m = re.search(rf"(?m)^{re.escape(header.split()[0])}\\b", t)
                if m:
                    insert_pos = m.start()
                else:
                    insert_pos = len(t)
                # Ensure a blank line before block if needed
                prefix = "\n" if insert_pos and t[insert_pos-1] != "\n" else ""
                t = t[:insert_pos] + prefix + block + t[insert_pos:]
                return t

            # Safe sections to consolidate
            safe_headers = [
                '/interface vpls',
                '/routing bgp connection',
                '/routing filter',
                '/interface bridge port',
                '/ip firewall address-list',
                '/ip firewall filter',
                '/ip firewall nat',
                '/ip firewall mangle',
                '/ip firewall raw',
                '/ip dhcp-server network',
                '/queue tree'
            ]
            for hdr in safe_headers:
                text = consolidate_block(text, hdr)

            # Reassemble safe blocks in canonical order for consistent arrangement
            def extract_block(t: str, header: str) -> tuple[str, str]:
                m = re.search(rf"(?ms)^" + re.escape(header) + r"\s*\n(?:add[^\n]*\n)+", t)
                if not m:
                    return t, ''
                block = m.group(0)
                t = t.replace(block, '')
                return t, block.strip() + "\n"

            ordered_blocks = []
            remainder = text
            # Move '/routing bgp template set default ...' to live after the BGP connection block
            bgp_tmpl_lines = re.findall(r"(?m)^/routing bgp template\s+(?:set|add)\b[^\n]*$", remainder)
            if bgp_tmpl_lines:
                # strip from remainder to avoid appearing at top
                remainder = re.sub(r"(?m)^/routing bgp template\s+(?:set|add)\b[^\n]*\n?", "", remainder)
            for hdr in safe_headers:
                remainder, blk = extract_block(remainder, hdr)
                if blk:
                    ordered_blocks.append(blk.strip())

            # If we have bgp template lines, append them immediately after the BGP connection block
            if bgp_tmpl_lines:
                bgp_block_idx = next((i for i, b in enumerate(ordered_blocks) if b.startswith('/routing bgp connection\n')), None)
                tmpl_block = '/routing bgp template\n' + '\n'.join(sorted(set([re.sub(r"\\s+"," ",l).strip() for l in bgp_tmpl_lines]))) + '\n'
                if bgp_block_idx is not None:
                    ordered_blocks.insert(bgp_block_idx + 1, tmpl_block.strip())
                else:
                    # If no connection block exists, place near other routing blocks or at the end
                    ordered_blocks.append(tmpl_block.strip())

            # Ensure clean separation: single blank line between top-level headers for remainder
            lines = remainder.splitlines()
            out = []
            prev_was_header = False
            def is_header(l: str) -> bool:
                return l.startswith('/') and ' ' not in l.strip()
            for l in lines:
                if is_header(l):
                    if out and out[-1] != '':
                        out.append('')
                    out.append(l)
                    prev_was_header = True
                else:
                    out.append(l)
                    prev_was_header = False
            # Collapse multiple blank lines
            final = []
            blank = 0
            for l in out:
                if l.strip() == '':
                    blank += 1
                    if blank <= 2:
                        final.append('')
                else:
                    blank = 0
                    final.append(l)
            remainder_clean = "\n".join(final).strip()
            # Put remainder first, then ordered canonical blocks
            pieces = [p for p in [remainder_clean] + ordered_blocks if p]
            text = ("\n\n".join(pieces)).strip() + "\n"

            # Final safety: any remaining bare address-list lines must be fully-qualified
            # Convert stray 'add ... list=... address=...' or 'add ... address=... list=...' to '/ip firewall address-list add ...'
            text = re.sub(r"(?m)^\s*(add\s+[^\n]*(?:(?:(?:^|\s)list=\S+)\s+[^\n]*(?:(?:^|\s)address=\S+)|(?:(?:^|\s)address=\S+)\s+[^\n]*(?:(?:^|\s)list=\S+))[^\n]*)$",
                          r"/ip firewall address-list \1", text)
            text = re.sub(r"(?m)^\s*(add\s+[^\n]*\baddress=\S+[^\n]*\blist=\S+[^\n]*)$",
                          r"/ip firewall address-list \1", text)

            return text

        # INTELLIGENT DETECTION AND ANALYSIS
        # Define apply_intelligent_translation BEFORE using it
        def apply_intelligent_translation(config, source_device_info, source_syntax_info, target_syntax_info, target_device_info, target_version):
            translated = config
            print(f"[TRANSLATION] Starting intelligent translation...")
            
            # 1. Update device model and identity intelligently
            if source_device_info['model'] != 'unknown':
                translated = translated.replace(source_device_info['model'], target_device_info['model'])
                # Update any references to the old model
                old_model_short = source_device_info['model'].split('-')[0]  # Extract CCR1036 from CCR1036-12G-4S
                new_model_short = target_device_info['model'].split('-')[0]  # Extract CCR2004 from CCR2004-1G-12S+2XS
                translated = translated.replace(old_model_short, new_model_short)
                
                # Update system identity: switch model digits in identity to target device digits
                target_digits_match = re.search(r"(\d{3,4})", target_device_info['model'])
                target_digits = target_digits_match.group(1) if target_digits_match else None
                if target_digits:
                    # Specific patterns first
                    translated = re.sub(r"(?m)^(set\s+name=RTR\-MTRB\-)(\d{3,4})(\S*)$",
                                        rf"\1{target_digits}\3", translated)
                    translated = re.sub(r"(?m)^(set\s+name=RTR\-CCR)(\d{3,4})(\S*)$",
                                        rf"\1{target_digits}\3", translated)
                    # Generic fallback: any RTR-<segment>-<digits>
                    translated = re.sub(r"(?m)^(set\s+name=RTR\-[A-Za-z0-9]+\-)(\d{3,4})(\S*)$",
                                        rf"\1{target_digits}\3", translated)
                # Legacy replacement if identity is in the form RTR-<MODEL>-<...>
                identity_pattern = f"RTR-{old_model_short}-"
                if identity_pattern in translated:
                    translated = translated.replace(identity_pattern, f"RTR-{new_model_short}-")
            
            # 2. Update RouterOS version header intelligently
            version_patterns = [
                'by RouterOS 6.', 'RouterOS 6.',
                'by RouterOS 7.', 'RouterOS 7.',
                'by RouterOS 8.', 'RouterOS 8.'
            ]
            for pattern in version_patterns:
                if pattern in translated:
                    translated = translated.replace(pattern, f'by RouterOS {target_version}')
                    break
            
            # 3. Apply intelligent syntax changes
            if source_syntax_info['bgp_syntax'] != 'unknown' and target_syntax_info['bgp_peer'] != source_syntax_info['bgp_syntax']:
                print(f"[SYNTAX] Converting BGP: {source_syntax_info['bgp_syntax']} → {target_syntax_info['bgp_peer']}")
                translated = translated.replace('/routing bgp peer', '/routing bgp connection')
                # Convert parameters
                for old_param, new_param in target_syntax_info['bgp_params'].items():
                    if old_param != new_param:
                        translated = translated.replace(f'{old_param}=', f'{new_param}=')
            
            if source_syntax_info['ospf_syntax'] != 'unknown' and target_syntax_info['ospf_interface'] != source_syntax_info['ospf_syntax']:
                print(f"[SYNTAX] Converting OSPF: {source_syntax_info['ospf_syntax']} → {target_syntax_info['ospf_interface']}")
                translated = translated.replace('/routing ospf interface add', '/routing ospf interface-template add')
                translated = translated.replace('interface=', 'interfaces=')
            
            # 4. Apply bridge VLAN changes for RouterOS 7.x
            if target_syntax_info['bridge_vlan'] and 'bridge=lan-bridge' in translated:
                translated = translated.replace('bridge=lan-bridge', 'bridge=lan-bridge vlan-filtering=yes')
            
            # 5. Intelligent interface mapping (order-based, device-agnostic)
            def map_interfaces_dynamically(text: str, target_ports: list, mgmt_port: str, target_type: str) -> str:
                # Gather used interface tokens in order of appearance
                used = []
                for m in re.finditer(r"\b(ether\d+|sfp-sfpplus\d+|sfp28-\d+|sfp\d+)\b", text):
                    name = m.group(1)
                    if name not in used:
                        used.append(name)
                # Prepare target port sequence excluding management if present
                target_seq = [p for p in target_ports if p != mgmt_port]
                # Prefer SFP28 on CCR2216 (no qsfp28 usage)
                target_seq = [p for p in target_seq if not p.startswith('qsfp28')]
                # Build mapping: skip mapping for mgmt-like ports (ether1 etc)
                mapping = {}
                tgt_idx = 0
                for src in used:
                    # Skip management port mapping unless target device has only 1 ethernet port (like CCR2004, CCR2216)
                    should_skip_mgmt = (src == mgmt_port and len([p for p in target_ports if p.startswith('ether')]) > 1)
                    if should_skip_mgmt:
                        continue
                    if tgt_idx < len(target_seq):
                        mapping[src] = target_seq[tgt_idx]
                        tgt_idx += 1
                if not mapping:
                    return text
                # Apply replacements safely (longest names first)
                for src in sorted(mapping.keys(), key=len, reverse=True):
                    dst = mapping[src]
                    text = re.sub(rf"\b{re.escape(src)}\b", dst, text)
                # Port name normalization: convert legacy port names to target device port format
                target_port_prefix = None
                if any(p.startswith('sfp28-') for p in target_seq):
                    target_port_prefix = 'sfp28'
                elif any(p.startswith('sfp-sfpplus') for p in target_seq):
                    target_port_prefix = 'sfp-sfpplus'
                elif any(p.startswith('sfp') and not p.startswith('sfp-sfpplus') and not p.startswith('sfp28') for p in target_seq):
                    target_port_prefix = 'sfp'
                
                # Convert legacy port names to target device format if needed
                if target_port_prefix:
                    # Convert sfp-sfpplusN to target format (if target uses sfp28-N)
                    if target_port_prefix == 'sfp28':
                        for i in range(1, 13):
                            text = re.sub(rf"\bsfp\-sfpplus{i}\b", f"sfp28-{i}", text)
                    # Convert old SFP ports (sfp1, sfp2, etc.) to target format
                    if target_port_prefix in ['sfp28', 'sfp-sfpplus']:
                        for i in range(1, 5):
                            old_pattern = rf"\bsfp{i}\b(?!\d)"
                            new_port = f"{target_port_prefix}-{i}" if target_port_prefix == 'sfp-sfpplus' else f"sfp28-{i}"
                            text = re.sub(old_pattern, new_port, text)
                
                return text

            target_ports = target_device_info.get('ports', [])
            mgmt_port = target_device_info.get('management', '')
            if target_ports:
                print(f"[INTERFACE] Dynamic mapping using target ports: {', '.join(target_ports)}")
                translated = map_interfaces_dynamically(translated, target_ports, mgmt_port, target_device_info.get('type',''))
                # For devices with only 1 ethernet port (mgmt only), map remaining ether ports to available SFP ports
                ethernet_ports = [p for p in target_ports if p.startswith('ether')]
                if len(ethernet_ports) == 1:  # Only management ethernet
                    # Find available SFP ports in target device
                    sfp_ports = [p for p in target_ports if p.startswith('sfp') and p != mgmt_port]
                    if sfp_ports:
                        # Replace any remaining ether{2+} occurrences with next available SFP port
                        non_mgmt_ethers = re.findall(r"\bether([2-9]|1[0-9])\b", translated)
                        if non_mgmt_ethers:
                            # Find available SFP port numbers
                            available_sfp = [p for p in sfp_ports if any(re.search(rf'\b{p}\b', translated))]
                            remaining_sfp = [p for p in sfp_ports if p not in available_sfp]
                            
                            if remaining_sfp:
                                def repl(match):
                                    return remaining_sfp.pop(0) if remaining_sfp else match.group(0)
                                translated = re.sub(r"\bether([2-9]|1[0-9])\b", repl, translated, count=len(remaining_sfp))

                # Force ether1 to be management-only: move any address/OSPF/BGP usage off ether1 to first data port
                first_data_port = next((p for p in target_ports if p != mgmt_port and not p.startswith('qsfp')), None)
                if first_data_port and mgmt_port:
                    # Move IP addresses
                    translated = re.sub(rf"(?m)^(add\s+address=\S+\s+comment=\S*\s*interface=){re.escape(mgmt_port)}(\b)",
                                        rf"\1{first_data_port}\2", translated)
                    translated = re.sub(rf"(?m)^(add\s+address=\S+\s+interface=){re.escape(mgmt_port)}(\b)",
                                        rf"\1{first_data_port}\2", translated)
                    # Move OSPF interface-template lines
                    translated = re.sub(rf"(?m)^(add\s+[^\n]*\binterfaces=){re.escape(mgmt_port)}(\b)",
                                        rf"\1{first_data_port}\2", translated)
                    # Move queue-tree parents if targeting ether1
                    translated = re.sub(rf"(?m)^(add\s+[^\n]*\bparent=){re.escape(mgmt_port)}(\b)",
                                        rf"\1{first_data_port}\2", translated)

            # 5b. OSPF strict normalization (ROS6 → ROS7)
            def normalize_ospf_line(l: str) -> str:
                l = l.replace('/routing ospf interface add', '/routing ospf interface-template add')
                l = l.replace('/routing ospf network add', '/routing ospf interface-template add')
                l = l.replace(' interface=', ' interfaces=')
                l = l.replace(' authentication=', ' auth=')
                l = l.replace(' authentication-key=', ' auth-key=')
                # network= → networks=
                l = re.sub(r"\bnetwork=", 'networks=', l)
                # add defaults where missing
                if l.startswith('/routing ospf interface-template add'):
                    if ' auth-id=' not in l and ' auth=' in l:
                        l += ' auth-id=1'
                    if ' type=' not in l and 'interfaces=' in l:
                        l += ' type=ptp'
                    if ' disabled=' not in l:
                        l += ' disabled=no'
                return l

            translated = '\n'.join([normalize_ospf_line(ln) for ln in translated.splitlines()])

            # 5c. Attach OSPF interface-templates to interfaces derived from IP networks
            # Build network→interface map from '/ip address add' lines
            net_to_if = {}
            for m in re.finditer(r"(?m)^/ip address\s+add\s+address=(\d+\.\d+\.\d+\.\d+)/(\d{1,2})[^\n]*\binterface=(\S+)", translated):
                ip = m.group(1)
                plen = int(m.group(2))
                iface = m.group(3)
                try:
                    network = str(ipaddress.ip_network(f"{ip}/{plen}", strict=False))
                    net_to_if[network] = iface
                except Exception:
                    continue

            def ospf_attach(m):
                line = m.group(0)
                # if already has interfaces= leave it
                if ' interfaces=' in line:
                    return line
                nets = re.findall(r"networks=(\d+\.\d+\.\d+\.\d+)/(\d{1,2})", line)
                for ip, plen in nets:
                    try:
                        n = str(ipaddress.ip_network(f"{ip}/{plen}", strict=False))
                    except Exception:
                        continue
                    iface = net_to_if.get(n)
                    if iface:
                        # insert interfaces=iface after add token
                        return re.sub(r"^/routing ospf interface-template\s+add\s+", f"/routing ospf interface-template add interfaces={iface} ", line)
                return line

            translated = re.sub(r"(?m)^/routing ospf interface-template\s+add\b[^\n]*$", ospf_attach, translated)
            
            # 6. Update update-source to use IP instead of interface for RouterOS 7.x (no hardcoded IPs)
            if target_version.startswith('7.'):
                # Migrate key to v7 style first
                translated = translated.replace('update-source=', 'update.source=')
                # Prefer loopback/router-id if available
                lb_ip_dynamic = extract_loopback_ip(translated)
                if lb_ip_dynamic:
                    translated = re.sub(r"update\.source=([A-Za-z0-9_.:-]+)", f"update.source={lb_ip_dynamic}", translated)
            
            print(f"[TRANSLATION] Intelligent translation completed")
            return translated

        print(f"[INTELLIGENT ANALYSIS] Analyzing source config...")
        source_syntax_info = detect_routeros_syntax(source_config)
        source_device_info = detect_source_device(source_config)
        target_device_info = get_target_device_info(target_device)
        target_syntax_info = get_target_syntax(target_version)
        
        print(f"[DETECTED] Source: {source_syntax_info['version']} on {source_device_info['model']}")
        print(f"[TARGET] Converting to: {target_version} on {target_device_info['model']}")
        print(f"[SYNTAX] BGP: {source_syntax_info['bgp_syntax']} → {target_syntax_info['bgp_peer']}")
        print(f"[SYNTAX] OSPF: {source_syntax_info['ospf_syntax']} → {target_syntax_info['ospf_interface']}")
        
        # BYPASS AI FOR LARGE CONFIGS (prevent timeouts)
        config_size = len(source_config.split('\n'))
        config_size_mb = len(source_config.encode('utf-8')) / (1024 * 1024)
        
        print(f"[CONFIG SIZE] Lines: {config_size}, Size: {config_size_mb:.2f}MB")
        
        # For very large configs, skip AI entirely
        if config_size > 800 or config_size_mb > 2.0:  # Lowered threshold for better performance
            print(f"[BYPASS AI] Large config ({config_size} lines, {config_size_mb:.2f}MB) - using intelligent translation only")
            translated = apply_intelligent_translation(source_config, source_device_info, source_syntax_info, target_syntax_info, target_device_info, target_version)
            validation = validate_translation(source_config, translated)
            return jsonify({
                'success': True,
                'translated_config': translated,
                'validation': validation,
                'bypass_ai': True,
                'message': f'Large config ({config_size} lines, {config_size_mb:.2f}MB) - used intelligent translation for speed'
            })
        
        # If both are v7 AND same exact device, skip AI for speed
        # BUT if device changed, we MUST use AI to properly map interfaces (e.g., sfp-sfpplus → sfp28)
        if is_source_v7 and is_target_v7 and same_exact_device:
            print(f"[FAST MODE] Same device, ROS7→ROS7 - using intelligent translation only (no AI needed)")
            translated_fast = apply_intelligent_translation(
                source_config,
                source_device_info,
                detect_routeros_syntax(source_config),
                get_target_syntax(target_version),
                target_device_info,
                target_version
            )
            translated_fast = postprocess_to_v7(translated_fast, target_version)
            validation_fast = validate_translation(source_config, translated_fast)
            return jsonify({
                'success': True,
                'translated_config': translated_fast,
                'validation': validation_fast,
                'fast_mode': True,
                'message': 'ROS7→ROS7, same device - optimized translation (no AI needed)'
            })
        elif is_source_v7 and is_target_v7 and not same_exact_device:
            print(f"[AI MODE] Device change: {source_device_info['model']} → {target_device_info['model']} (ROS7→ROS7 but hardware differs - using AI for proper port mapping)")
            # Continue to AI translation below

        # INTELLIGENT DYNAMIC TRANSLATION FUNCTION
        # (Function already defined above, no need to redefine)

        training_context = build_training_context()
        compliance_note = ""
        if HAS_COMPLIANCE:
            compliance_note = """
MANDATORY COMPLIANCE (RFC-09-10-25):
- All configurations MUST include NextLink compliance standards
- The backend will automatically add compliance blocks after translation
- Ensure DNS servers are 142.147.112.3,142.147.112.19
- Ensure firewall rules, IP services, NTP, SNMP, and logging follow NextLink standards
- Compliance will be validated and enforced automatically
"""
        
        system_prompt = f"""You are a RouterOS config translator with deep knowledge of RouterOS syntax differences.

CRITICAL PRESERVATION RULES (MANDATORY - NO EXCEPTIONS):
1. COPY EVERY SINGLE LINE from source config - DO NOT SKIP ANY LINES
2. PRESERVE ALL IP ADDRESSES EXACTLY as provided - DO NOT MODIFY OR REMOVE
3. PRESERVE ALL PASSWORDS, SECRETS, AND AUTHENTICATION KEYS EXACTLY
4. PRESERVE ALL USER ACCOUNTS, GROUPS, AND PERMISSIONS EXACTLY
5. PRESERVE ALL FIREWALL RULES, NAT RULES, MANGLE RULES EXACTLY
6. PRESERVE ALL VLAN IDs, BRIDGE NAMES, INTERFACE NAMES (except hardware port mapping)
7. PRESERVE ALL ROUTING PROTOCOL CONFIGURATIONS (areas, AS numbers, router IDs, network statements)
8. PRESERVE ALL COMMENTS AND DOCUMENTATION
9. DO NOT REMOVE, MODIFY, OR SUMMARIZE ANY LINES - COPY EVERYTHING
10. DO NOT CHANGE VALUES - ONLY CHANGE SYNTAX/COMMAND STRUCTURE

TRANSLATION SCOPE (ONLY THESE CHANGES ALLOWED):
- Apply RouterOS {source_syntax_info['version']} → {target_version} syntax changes ONLY
- Update device model references to {target_device_info['model']}
- Map hardware interfaces to {target_device.upper()} ports (sfp-sfpplus1 → appropriate port)
- Update command syntax (e.g., /routing bgp peer → /routing bgp connection)
- Update parameter names (e.g., update-source → update.source)

FORBIDDEN ACTIONS (NEVER DO THESE):
- DO NOT remove any configuration lines
- DO NOT modify IP addresses, passwords, or secrets
- DO NOT change VLAN IDs or network addresses
- DO NOT summarize or combine multiple rules
- DO NOT remove comments or documentation
{compliance_note}
SYNTAX CHANGES NEEDED:
- BGP: {source_syntax_info['bgp_syntax']} → {target_syntax_info['bgp_peer']}
- OSPF: {source_syntax_info['ospf_syntax']} → {target_syntax_info['ospf_interface']}
- Parameters: {target_syntax_info['bgp_params']}

HARDWARE CHANGES (INTERFACE MAPPING ONLY):
- Model: {target_device_info['model']}
- Ports: {', '.join(target_device_info['ports'])}
- Management: {target_device_info['management']}
- Map source device ports to target device ports (e.g., sfp-sfpplus1 → sfp28-1 if needed)

REMEMBER: Your job is SYNTAX TRANSLATION ONLY. Preserve ALL data values exactly."""

        if training_context:
            system_prompt += "\n\n" + training_context

        syntax_rules = get_syntax_rules(target_version)

        user_prompt = f"""Translate this RouterOS config from source device to {target_device.upper()} for RouterOS {target_version}:

{source_config}

Output (copy every line, update device model to {target_device.upper()}):"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            translated = call_ai(messages, max_tokens=16000, task_type='translation', config_size=len(source_config))  # Smart model selection
        except Exception as e:
            print(f"[AI ERROR] {str(e)} - Using intelligent fallback")
            # Use intelligent fallback translation
            translated = apply_intelligent_translation(source_config, source_device_info, source_syntax_info, target_syntax_info, target_device_info, target_version)
            

        # Clean up any markdown formatting
        translated = translated.replace('```routeros', '').replace('```', '').strip()

        # Port name normalization: convert sfp-sfpplusN to target device port format if needed
        # This handles upgrades from CCR2004 (sfp-sfpplus) to devices that use sfp28- ports
        target_ports_list = target_device_info.get('ports', [])
        if any(p.startswith('sfp28-') for p in target_ports_list):
            # Target device uses sfp28- ports, convert sfp-sfpplusN to sfp28-N
            for i in range(1, 13):
                translated = re.sub(rf"\bsfp\-sfpplus{i}\b", f"sfp28-{i}", translated)

        # Post-process to enforce v7 syntax regardless of AI path
        translated = postprocess_to_v7(translated, target_version)

        # Validate translation
        validation = validate_translation(source_config, translated)
        
        # If important information is lost, use intelligent fallback
        should_fallback = False
        fallback_reason = []
        
        if validation.get('missing_ips', []) and len(validation['missing_ips']) > 50:
            should_fallback = True
            fallback_reason.append(f"Too many IPs lost ({len(validation['missing_ips'])})")
        
        if validation.get('missing_secrets', []) and len(validation['missing_secrets']) > 0:
            should_fallback = True
            fallback_reason.append(f"Missing secrets ({len(validation['missing_secrets'])})")
        
        if validation.get('missing_users', []) and len(validation['missing_users']) > 0:
            should_fallback = True
            fallback_reason.append(f"Missing users ({len(validation['missing_users'])})")
        
        if should_fallback:
            print(f"[INTELLIGENT FALLBACK] Information loss detected: {', '.join(fallback_reason)} - using intelligent translation")
            translated = apply_intelligent_translation(source_config, source_device_info, source_syntax_info, target_syntax_info, target_device_info, target_version)
            translated = postprocess_to_v7(translated, target_version)
            validation = validate_translation(source_config, translated)
        
        # FORCE INTELLIGENT FALLBACK FOR LARGE CONFIGS (prevent timeouts)
        config_size = len(source_config.split('\n'))
        if config_size > 500:  # Large configs
            print(f"[LARGE CONFIG] Detected {config_size} lines - using intelligent translation to prevent timeout")
            translated = apply_intelligent_translation(source_config, source_device_info, source_syntax_info, target_syntax_info, target_device_info, target_version)
            translated = postprocess_to_v7(translated, target_version)
            validation = validate_translation(source_config, translated)

        # ========================================
        # RFC-09-10-25 COMPLIANCE ENFORCEMENT
        # ========================================
        # Extract loopback IP from translated config for compliance blocks
        loopback_ip = None
        loopback_match = re.search(r'/ip address\s+add address=([0-9.]+/[0-9]+)\s+interface=loop0', translated, re.IGNORECASE)
        if not loopback_match:
            # Try alternative patterns
            loopback_match = re.search(r'interface=loop0.*?address=([0-9.]+/[0-9]+)', translated, re.IGNORECASE)
        if loopback_match:
            loopback_ip = loopback_match.group(1)
        
        # If loopback not found, try to extract from source config
        if not loopback_ip:
            source_loopback_match = re.search(r'/ip address\s+add address=([0-9.]+/[0-9]+)\s+interface=loop0', source_config, re.IGNORECASE)
            if source_loopback_match:
                loopback_ip = source_loopback_match.group(1)
        
        # Apply compliance if available
        compliance_validation = None
        if HAS_COMPLIANCE:
            print("[COMPLIANCE] Enforcing RFC-09-10-25 compliance standards...")
            try:
                # Get compliance blocks
                compliance_blocks = get_all_compliance_blocks(loopback_ip or "10.0.0.1/32")
                
                # Inject compliance into translated config
                translated = inject_compliance_blocks(translated, compliance_blocks)
                
                # Validate compliance
                compliance_validation = validate_compliance(translated)
                
                if not compliance_validation['compliant']:
                    print(f"[COMPLIANCE WARNING] {len(compliance_validation['missing_items'])} compliance items missing")
                else:
                    print("[COMPLIANCE] ✅ Configuration is compliant")
                    
            except Exception as e:
                print(f"[COMPLIANCE ERROR] Failed to apply compliance: {e}")
                compliance_validation = {'compliant': False, 'error': str(e)}

        return jsonify({
            'success': True,
            'translated_config': translated,
            'validation': validation,
            'compliance': compliance_validation
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========================================
# ENDPOINT 4: Apply Compliance to Config
# ========================================

@app.route('/api/apply-compliance', methods=['POST'])
def apply_compliance():
    """
    Apply RFC-09-10-25 compliance standards to a RouterOS configuration.
    Used by both Non-MPLS and MPLS Enterprise config generators.
    
    IMPORTANT: This endpoint is ADDITIVE and NON-DESTRUCTIVE:
    - Adds compliance blocks without removing existing configurations
    - Skips frontend-only tabs (Tarana, 6GHz) that are production-ready
    - Preserves all tab-specific functionality
    - Does not override existing firewall rules, IP services, or other configs
    """
    try:
        data = request.get_json(force=True)
        config = data.get('config', '')
        loopback_ip = data.get('loopback_ip', '')
        
        if not config:
            return jsonify({'success': False, 'error': 'No configuration provided'}), 400
        
        if not HAS_COMPLIANCE:
            return jsonify({
                'success': True,
                'config': config,
                'compliance': {'compliant': False, 'error': 'Compliance reference not available'}
            })
        
        # Check if this is a frontend-only tab (Tarana, 6GHz) - these are production-ready
        config_lower = config.lower()
        is_tarana_config = ('tarana' in config_lower or 'sector' in config_lower or ('alpha' in config_lower and 'beta' in config_lower))
        is_6ghz_config = ('6ghz' in config_lower or '6ghz switch' in config_lower)
        
        if is_tarana_config or is_6ghz_config:
            print("[COMPLIANCE] Skipping compliance injection for frontend-only tab (Tarana/6GHz - production ready, self-contained)")
            return jsonify({
                'success': True,
                'config': config,
                'compliance': {
                    'compliant': True,
                    'note': 'Frontend-only tab (production ready) - compliance not needed'
                }
            })
        
        # Extract loopback IP from config if not provided
        if not loopback_ip:
            loopback_match = re.search(r'/ip address\s+add address=([0-9.]+/[0-9]+)\s+interface=loop0', config, re.IGNORECASE)
            if loopback_match:
                loopback_ip = loopback_match.group(1)
            else:
                # Try alternative pattern
                loopback_match = re.search(r'interface=loop0.*?address=([0-9.]+/[0-9]+)', config, re.IGNORECASE)
                if loopback_match:
                    loopback_ip = loopback_match.group(1)
        
        if not loopback_ip:
            loopback_ip = "10.0.0.1/32"  # Default fallback
        
        print(f"[COMPLIANCE] Applying RFC-09-10-25 compliance to configuration (additive, non-destructive)...")
        
        # Get compliance blocks
        compliance_blocks = get_all_compliance_blocks(loopback_ip)
        
        # Inject compliance into config (additive, preserves existing configs)
        compliant_config = inject_compliance_blocks(config, compliance_blocks)
        
        # Validate compliance
        compliance_validation = validate_compliance(compliant_config)
        
        if not compliance_validation['compliant']:
            print(f"[COMPLIANCE WARNING] {len(compliance_validation['missing_items'])} compliance items missing")
        else:
            print("[COMPLIANCE] ✅ Configuration is compliant")
        
        return jsonify({
            'success': True,
            'config': compliant_config,
            'compliance': compliance_validation
        })
        
    except Exception as e:
        print(f"[COMPLIANCE ERROR] Failed to apply compliance: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'config': config  # Return original config on error - preserves functionality
        }), 500

# ========================================
# ENDPOINT 5: AI Config Explanation
# ========================================

@app.route('/api/explain-config', methods=['POST'])
def explain_config():
    """
    Explains what a config section does (for training/documentation)
    """
    try:
        data = request.json
        config_section = data.get('config', '')

        system_prompt = """You are a RouterOS configuration explainer.
Explain what each section does in simple terms for network administrators.
Include:
- Purpose of each command
- Security implications
- Performance impact
- RFC standards involved"""

        user_prompt = f"""Explain this RouterOS configuration:

```
{config_section}
```

Provide clear explanations for NOC staff."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        explanation = call_ai(messages, max_tokens=2000)

        return jsonify({
            'success': True,
            'explanation': explanation
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========================================
# ENDPOINT 5: AI Auto-Fill From Export
# ========================================

@app.route('/api/autofill-from-export', methods=['POST'])
def autofill_from_export():
    """
    Parses an exported config and auto-fills the form fields
    Most useful feature for NOC workflow!
    """
    try:
        data = request.json
        exported_config = data.get('exported_config', '')
        target_form = data.get('target_form', 'tower')  # Which form to fill

        system_prompt = """You are a RouterOS configuration parser.
Extract relevant fields from an exported configuration and map them to form fields.

Return JSON format with extracted values:
{
  "site_name": "extracted value",
  "router_id": "x.x.x.x",
  "loopback_ip": "x.x.x.x/32",
  "uplinks": [{"interface": "ether1", "ip": "x.x.x.x/30"}],
  "ospf_area": "backbone",
  "bgp_as": "65000",
  "vlans": ["1000", "2000", "3000"],
  ...
}
"""

        user_prompt = f"""Parse this exported RouterOS configuration and extract values for the {target_form} form:

```
{exported_config}
```

Return JSON with all extractable fields."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        result = call_ai(messages, max_tokens=3000)

        try:
            parsed_fields = json.loads(result)
        except:
            parsed_fields = {"error": "Could not parse config", "raw": result}

        return jsonify({
            'success': True,
            'fields': parsed_fields
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========================================
# ENDPOINT 6: Non‑MPLS Enterprise Generator
# ========================================

def _cidr_details_gen(cidr: str) -> dict:
    net = ipaddress.ip_network(cidr, strict=False)
    hosts = list(net.hosts())
    first_host = str(hosts[0]) if hosts else str(net.network_address)
    last_host = str(hosts[-1]) if hosts else str(net.broadcast_address)
    
    # For /30 networks: only 2 usable IPs (gateway and customer)
    # The user provides the gateway IP, so pool should be customer IP only (gateway + 1)
    if net.prefixlen == 30 and len(hosts) >= 2:
        # Gateway is hosts[0], customer is hosts[1]
        pool_start = str(hosts[1])  # Customer IP (gateway + 1)
        pool_end = str(hosts[1])    # Same IP for single-IP pool
    elif len(hosts) > 3:
        # For larger networks, exclude gateway (first) and broadcast (last)
        pool_start = str(hosts[1])
        pool_end = str(hosts[-2])
    else:
        # Fallback: use first_host as pool (shouldn't happen for /30)
        pool_start = first_host
        pool_end = last_host
    
    return {
        'network': str(net.network_address),
        'prefix': net.prefixlen,
        'router_ip': first_host,
        'first_host': first_host,
        'last_host': last_host,
        'pool_start': pool_start,
        'pool_end': pool_end,
        'broadcast': str(net.broadcast_address),
    }

@app.route('/api/gen-enterprise-non-mpls', methods=['POST'])
def gen_enterprise_non_mpls():
    try:
        data = request.get_json(force=True)
        device = (data.get('device') or 'RB5009').upper()
        target_version = data.get('target_version', '7.19.4')
        public_cidr = data['public_cidr']
        bh_cidr = data['bh_cidr']
        loopback_ip = data['loopback_ip']  # /32 expected
        uplink_if = data.get('uplink_interface', 'sfp-sfpplus1')
        public_port = data.get('public_port', 'ether7')
        nat_port = data.get('nat_port', 'ether8')
        # Use environment variables or form data - RFC-09-10-25 Compliance defaults
        # Default to NextLink compliance DNS servers (142.147.112.3, 142.147.112.19)
        dns1 = data.get('dns1') or os.getenv('NEXTLINK_DNS_PRIMARY', '142.147.112.3')
        dns2 = data.get('dns2') or os.getenv('NEXTLINK_DNS_SECONDARY', '142.147.112.19')
        if not dns1 or not dns2:
            return jsonify({'success': False, 'error': 'DNS servers must be configured. Set NEXTLINK_DNS_PRIMARY and NEXTLINK_DNS_SECONDARY environment variables or configure in nextlink_constants.js'}), 400
        snmp_community = data.get('snmp_community', 'CHANGE_ME')
        syslog_ip = data.get('syslog_ip')
        coords = data.get('coords')
        identity = data.get('identity', f"RTR-{device}.AUTO-GEN")
        uplink_comment = data.get('uplink_comment', '').strip()  # Uplink comment/location for backhaul

        pub = _cidr_details_gen(public_cidr)
        bh = _cidr_details_gen(bh_cidr)
        private_cidr = data.get('private_cidr', '')  # e.g., 192.168.88.1/24
        private_ip_range = data.get('private_pool', '')  # e.g., 192.168.88.10-192.168.88.254
        
        # Extract exact router IPs from user-provided CIDRs (use the IP they provided, not calculated first_host)
        pub_router_ip_exact = public_cidr.split('/')[0]  # Use exact IP from user input
        bh_router_ip_exact = bh_cidr.split('/')[0]  # Use exact IP from user input
        
        if not syslog_ip:
            syslog_ip = loopback_ip.split('/')[0]
        
        # Determine speed syntax based on RouterOS version
        def get_speed_syntax(version):
            """Determine speed syntax based on RouterOS version"""
            if version.startswith('7.16') or version.startswith('7.19'):
                return '1G-baseX'  # For SFP ports
            return '1G-baseX'  # Default
        
        speed_syntax = get_speed_syntax(target_version)
        loopback_ip_clean = loopback_ip.replace('/32', '').strip()
        
        # Parse private CIDR if provided
        private_network = ''
        private_gateway = ''
        if private_cidr:
            private_parts = private_cidr.split('/')
            if len(private_parts) == 2:
                private_ip = private_parts[0]
                private_prefix = private_parts[1]
                private_net = _cidr_details_gen(private_cidr)
                private_network = private_net['network']
                private_gateway = private_ip  # Use provided IP as gateway
        
        # Use standard reference blocks if available
        standard_blocks = {}
        if HAS_REFERENCE:
            try:
                standard_blocks = get_all_standard_blocks()
            except Exception as e:
                print(f"[WARN] Could not load standard blocks: {e}")
        
        # Build config blocks in proper order
        blocks = []
        
        # System Identity
        blocks.append(f"/system identity\nset name={identity}\n")
        
        # Queue Type
        blocks.append("/queue type\nset default-small pfifo-limit=50\n")
        
        # Interface Bridge
        blocks.append("/interface bridge\nadd name=loop0\nadd name=nat-bridge priority=0x1\nadd name=public-bridge priority=0x1\n")
        
        # Interface Ethernet (with speed for uplink if SFP)
        ethernet_block = f"/interface ethernet\n"
        ethernet_block += f"set [ find default-name={public_port} ] comment=\"CX HANDOFF\"\n"
        ethernet_block += f"set [ find default-name={nat_port} ] comment=NAT\n"
        # Add uplink interface comment - Use uplink comment if provided, otherwise use identity
        uplink_comment_value = uplink_comment if uplink_comment else identity
        if uplink_if.startswith('sfp'):
            # Determine speed based on RouterOS version
            speed = get_speed_syntax(target_version)
            ethernet_block += f"set [ find default-name={uplink_if} ] auto-negotiation=no comment={uplink_comment_value} speed={speed}\n"
        else:
            # Non-SFP port - still add comment
            ethernet_block += f"set [ find default-name={uplink_if} ] comment={uplink_comment_value}\n"
        blocks.append(ethernet_block)
        
        # Interface Bridge Port
        blocks.append("/interface bridge port\n" +
                      f"add bridge=public-bridge interface={public_port}\n" +
                      f"add bridge=nat-bridge interface={nat_port}\n")
        
        # IP Addresses (with proper network calculation)
        ip_block = "/ip address\n"
        ip_block += f"add address={loopback_ip_clean} comment=loop0 interface=loop0 network={loopback_ip_clean}\n"
        
        # Public IP - use exact IP provided by user, calculate network
        pub_router_ip = pub_router_ip_exact  # Use exact user-provided IP
        pub_network = pub['network']
        ip_block += f"add address={pub_router_ip}/{pub['prefix']} comment=\"PUBLIC(S)\" interface=public-bridge network={pub_network}\n"
        
        # Private IP - use provided or calculate
        private_base = ''  # Initialize for use in firewall NAT later
        if private_cidr and private_gateway:
            ip_block += f"add address={private_gateway}/{private_parts[1]} comment=PRIVATES interface=nat-bridge network={private_network}\n"
            # Extract base for firewall NAT
            private_base = private_network.rsplit('.', 1)[0] if '.' in private_network else private_network.rsplit('/', 1)[0].rsplit('.', 1)[0]
        else:
            # Fallback to calculated private
            private_base = pub['first_host'].rsplit('.', 1)[0]
            ip_block += f"add address={private_base}.1/24 comment=PRIVATES interface=nat-bridge network={private_base}.0\n"
        
        # Backhaul IP address - use exact IP provided by user
        # Use uplink comment if provided, otherwise use identity
        bh_router_ip = bh_router_ip_exact  # Use exact user-provided IP
        bh_network = bh['network']
        ip_block += f"add address={bh_router_ip}/{bh['prefix']} comment={uplink_comment_value} interface={uplink_if} network={bh_network}\n"
        blocks.append(ip_block)
        
        # IP Pool
        pool_block = "/ip pool\n"
        # Public pool - use provided range or calculate
        # For /30: pool_start and pool_end are the same (customer IP only, excluding gateway)
        if pub.get('pool_start') and pub.get('pool_end'):
            if pub['pool_start'] == pub['pool_end']:
                # Single IP pool (e.g., /30 networks)
                pool_block += f"add name=public ranges={pub['pool_start']}\n"
            else:
                # Range pool
                pool_block += f"add name=public ranges={pub['pool_start']}-{pub['pool_end']}\n"
        else:
            pool_block += f"add name=public ranges={pub['router_ip']}\n"
        # Private pool
        if private_ip_range:
            pool_block += f"add name=private ranges={private_ip_range}\n"
        else:
            private_base = pub['first_host'].rsplit('.', 1)[0]
            pool_block += f"add name=private ranges={private_base}.10-{private_base}.254\n"
        blocks.append(pool_block)
        
        # Queue Tree
        blocks.append("/queue tree\n" +
                      f"add max-limit=200M name=UPLOAD parent={uplink_if}\n" +
                      "add max-limit=200M name=DOWNLOAD-PUB parent=public-bridge\n" +
                      "add max-limit=200M name=DOWNLOAD-NAT parent=nat-bridge\n" +
                      "add name=VOIP-UP packet-mark=VOIP parent=UPLOAD priority=1\n" +
                      "add name=VOIP-DOWN-PUB packet-mark=VOIP parent=DOWNLOAD-PUB priority=1\n" +
                      "add name=VOIP-DOWN-NAT packet-mark=VOIP parent=DOWNLOAD-NAT priority=1\n" +
                      "add name=ALL-DOWN-PUB packet-mark=ALL parent=DOWNLOAD-PUB\n" +
                      "add name=ALL-DOWN-NAT packet-mark=ALL parent=DOWNLOAD-NAT\n" +
                      "add name=ALL-UP packet-mark=ALL parent=UPLOAD\n")
        
        # IP Neighbor Discovery (tab-specific, not compliance)
        if standard_blocks.get('ip_neighbor_discovery'):
            blocks.append(standard_blocks['ip_neighbor_discovery'])
        
        # DHCP Server (tab-specific configuration)
        blocks.append("/ip dhcp-server\n" +
                      f"add address-pool=public interface=public-bridge lease-time=1h name=public-server\n" +
                      f"add address-pool=private interface=nat-bridge lease-time=1h name=nat-server\n")
        
        # DHCP Server Network (tab-specific configuration)
        dhcp_net_block = "/ip dhcp-server network\n"
        # Public DHCP network
        pub_gateway = pub_router_ip
        dhcp_net_block += f"add address={pub_network}/{pub['prefix']} dns-server={dns1},{dns2} gateway={pub_gateway}\n"
        # Private DHCP network
        if private_cidr and private_gateway:
            dhcp_net_block += f"add address={private_network}/{private_parts[1]} comment=PRIVATES dns-server={dns1},{dns2} gateway={private_gateway} netmask={private_parts[1]}\n"
        else:
            private_base = pub['first_host'].rsplit('.', 1)[0]
            dhcp_net_block += f"add address={private_base}.0/24 comment=PRIVATES dns-server={dns1},{dns2} gateway={private_base}.1 netmask=24\n"
        blocks.append(dhcp_net_block)
        
        # Firewall NAT (tab-specific rules - SMTP, NTP, private NAT)
        # NOTE: Compliance will add additional NAT rules, but these are tab-specific
        blocks.append("/ip firewall nat\n" +
                      f"add action=src-nat chain=srcnat packet-mark=SMTP to-addresses={loopback_ip_clean}\n" +
                      f"add action=src-nat chain=srcnat packet-mark=NTP to-addresses={loopback_ip_clean}\n" +
                      f"add action=src-nat chain=srcnat src-address={private_base}.0/24 to-addresses={pub_router_ip}\n")
        
        # Firewall Service Port (tab-specific)
        blocks.append("/ip firewall service-port\nset sip disabled=yes\n")
        
        # IP Route (tab-specific configuration)
        # For /29 or /30, gateway is usually first host (network + 1)
        bh_gateway = bh.get('router_ip', bh['first_host'])
        # If backhaul IP is provided, use that as gateway
        if 'gateway_ip' in data and data['gateway_ip']:
            bh_gateway = data['gateway_ip'].split('/')[0] if '/' in data['gateway_ip'] else data['gateway_ip']
        blocks.append(f"/ip route\nadd disabled=no distance=1 dst-address=0.0.0.0/0 gateway={bh_gateway} routing-table=main scope=30 suppress-hw-offload=no target-scope=10\n")
        
        # SNMP (tab-specific - location and basic settings)
        # NOTE: Compliance will add SNMP community and additional settings
        loc = f" location=\"{coords}\"" if coords else ""
        blocks.append(f"/snmp\nset enabled=yes src-address={loopback_ip_clean} trap-community={snmp_community}{loc}\n")
        
        # NOTE: Compliance script will handle:
        # - /ip firewall address-list (all lists)
        # - /ip firewall filter (all input/forward rules)
        # - /ip firewall raw (all raw rules)
        # - /ip dns (DNS servers)
        # - /ip service (all service settings)
        # - /system logging action and /system logging (logging configuration)
        # - /user group (all user groups)
        # - /user aaa (RADIUS settings)
        # - /system clock and /system ntp client (time/NTP)
        # - /system routerboard settings (auto-upgrade)
        # - Additional firewall NAT rules (unauth proxy, SSH redirect)
        # - Firewall mangle rules
        # - DHCP options
        # - RADIUS configuration
        # - LDP filters

        cfg = "\n\n".join(blocks)
        
        # ========================================
        # RFC-09-10-25 COMPLIANCE ENFORCEMENT
        # ========================================
        if HAS_COMPLIANCE:
            try:
                print("[COMPLIANCE] Adding RFC-09-10-25 compliance to new configuration...")
                compliance_blocks = get_all_compliance_blocks(loopback_ip)
                cfg = inject_compliance_blocks(cfg, compliance_blocks)
                
                # Validate compliance
                compliance_validation = validate_compliance(cfg)
                if not compliance_validation['compliant']:
                    print(f"[COMPLIANCE WARNING] {len(compliance_validation['missing_items'])} compliance items missing")
                else:
                    print("[COMPLIANCE] ✅ Configuration is compliant")
            except Exception as e:
                print(f"[COMPLIANCE ERROR] Failed to add compliance: {e}")
        
        # Normalize and deduplicate configuration before returning
        cfg = normalize_config(cfg)
        return jsonify({'success': True, 'config': cfg, 'device': device, 'version': target_version})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# ========================================
# HELPER FUNCTIONS
# ========================================

def get_syntax_rules(target_version):
    """Returns syntax change rules for target RouterOS version"""
    if target_version.startswith('7.'):
        return """V7 KEY CHANGES:
- OSPF: Use /routing ospf interface-template (not /routing ospf interface)
- BGP: Use /routing bgp connection (not /routing bgp peer)
- MOST SYNTAX STAYS THE SAME - only change if broken"""
    return "Keep syntax as-is"

def inject_compliance_blocks(config: str, compliance_blocks: dict) -> str:
    """
    Intelligently inject compliance blocks into a RouterOS configuration.
    Checks if compliance was already applied to avoid duplicates.
    
    IMPORTANT: Compliance blocks use RouterOS 'rem' commands to remove existing entries
    and then re-add them with compliance standards. If compliance section already exists,
    we skip to avoid duplication.
    
    Args:
        config: Existing RouterOS configuration
        compliance_blocks: Dictionary of compliance blocks from get_all_compliance_blocks()
        
    Returns:
        Updated configuration with compliance blocks (only if not already present)
    """
    # Check if config is from a frontend-only tab (Tarana, 6GHz) that shouldn't get compliance
    config_lower = config.lower()
    is_tarana_config = ('tarana' in config_lower or 'sector' in config_lower or 'alpha' in config_lower or 'beta' in config_lower or 'gamma' in config_lower)
    is_6ghz_config = ('6ghz' in config_lower or '6ghz switch' in config_lower or 'vlan3000' in config_lower or 'vlan4000' in config_lower)
    
    if is_tarana_config or is_6ghz_config:
        print("[COMPLIANCE] Skipping compliance injection for frontend-only tab (Tarana/6GHz - production ready)")
        return config
    
    # Check if compliance section already exists (to avoid double-injection)
    # Look for the compliance header comment in the last 3000 characters (where it would be appended)
    if "# RFC-09-10-25 COMPLIANCE STANDARDS" in config or "RFC-09-10-25 COMPLIANCE STANDARDS" in config[-3000:]:
        print("[COMPLIANCE] Compliance section already exists, skipping duplicate injection")
        return config
    
    # Append compliance blocks at the end (they use 'rem' commands to handle existing entries)
    compliance_section = "\n\n# ========================================\n# RFC-09-10-25 COMPLIANCE STANDARDS\n# ========================================\n# These blocks ensure NextLink policy compliance\n# They use 'rem' commands to remove existing entries and re-add with compliance standards\n# ========================================\n\n"
    
    # Add compliance blocks in order
    compliance_order = [
        'ip_services', 'dns', 'firewall_address_lists', 
        'firewall_filter_input', 'firewall_raw', 'firewall_forward',
        'firewall_nat', 'firewall_mangle', 'clock_ntp', 'snmp',
        'system_settings', 'vpls_edge', 'logging', 'user_aaa',
        'user_groups', 'dhcp_options', 'radius', 'ldp_filters'
    ]
    
    for key in compliance_order:
        if key in compliance_blocks:
            compliance_section += f"# {key.upper().replace('_', ' ')}\n"
            compliance_section += compliance_blocks[key]
            compliance_section += "\n\n"
    
    return config.rstrip() + "\n" + compliance_section

def validate_translation(source, translated):
    """Comprehensive validation to ensure all important information is preserved.
    Validates IP addresses, passwords, users, firewall rules, and routing configs.
    Normalizes /32 to bare IP to avoid false negatives on ROS7 fields like remote.address.
    """

    def strip_noise(text: str) -> str:
        # Remove router prompts
        text = re.sub(r"(?m)^\s*\[[^\]]+\]\s*", "", text)
        # Drop full-line comments
        text = re.sub(r"(?m)^\s*#.*$", "", text)
        # Remove /system script blocks (very noisy and may embed many IPs in strings)
        lines = text.splitlines()
        out = []
        in_script = False
        for l in lines:
            if l.startswith('/system script'):
                in_script = True
                continue
            if in_script and l.startswith('/'):
                in_script = False
            if in_script:
                continue
            out.append(l)
        return "\n".join(out)

    def extract_ips(text: str) -> set[str]:
        text = strip_noise(text)
        ips = set(re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b", text))
        # Normalize /32 to bare IP
        norm = set()
        for ip in ips:
            if ip.endswith('/32'):
                norm.add(ip[:-3])
            else:
                norm.add(ip)
        return norm

    source_ips = extract_ips(source)
    translated_ips = extract_ips(translated)
    missing_ips = source_ips - translated_ips
    
    # Additional validation: Check for preserved passwords/secrets
    def extract_secrets(text: str) -> set:
        # Extract password=, secret=, auth-key= values (but not the actual values for security)
        secrets = set(re.findall(r'\b(password|secret|auth-key|auth-id)=[^\s]+', text, re.IGNORECASE))
        return secrets
    
    source_secrets = extract_secrets(source)
    translated_secrets = extract_secrets(translated)
    missing_secrets = source_secrets - translated_secrets
    
    # Check for preserved user accounts
    def extract_users(text: str) -> set:
        users = set(re.findall(r'/user\s+(?:add|set)\s+name=([^\s]+)', text, re.IGNORECASE))
        return users
    
    source_users = extract_users(source)
    translated_users = extract_users(translated)
    missing_users = source_users - translated_users
    
    # Check firewall rule count preservation
    source_fw_rules = len(re.findall(r'/ip firewall\s+(?:filter|nat|mangle|raw)\s+(?:add|set)', source, re.IGNORECASE))
    translated_fw_rules = len(re.findall(r'/ip firewall\s+(?:filter|nat|mangle|raw)\s+(?:add|set)', translated, re.IGNORECASE))
    
    is_valid = len(missing_ips) == 0 and len(missing_secrets) == 0 and len(missing_users) == 0
    
    validation_result = {
        "valid": is_valid,
        "source_ip_count": len(source_ips),
        "translated_ip_count": len(translated_ips),
        "missing_ips": sorted(list(missing_ips)),
        "source_secret_count": len(source_secrets),
        "translated_secret_count": len(translated_secrets),
        "missing_secrets": sorted(list(missing_secrets)),
        "source_user_count": len(source_users),
        "translated_user_count": len(translated_users),
        "missing_users": sorted(list(missing_users)),
        "source_firewall_rules": source_fw_rules,
        "translated_firewall_rules": translated_fw_rules,
        "firewall_rules_preserved": translated_fw_rules >= source_fw_rules * 0.95  # Allow 5% tolerance for consolidation
    }
    
    if not is_valid:
        print(f"[VALIDATION WARNING] Missing information detected:")
        if missing_ips:
            print(f"  - Missing IPs: {len(missing_ips)}")
        if missing_secrets:
            print(f"  - Missing secrets: {len(missing_secrets)}")
        if missing_users:
            print(f"  - Missing users: {len(missing_users)}")
        if not validation_result["firewall_rules_preserved"]:
            print(f"  - Firewall rules: {source_fw_rules} → {translated_fw_rules}")
    
    return validation_result

# ========================================
# ENDPOINT 5: Tarana Config Generation & Validation
# ========================================

@app.route('/api/gen-tarana-config', methods=['POST'])
def gen_tarana_config():
    """
    Generates and validates Tarana sector configuration with AI-powered network calculation
    """
    try:
        data = request.get_json(force=True)
        raw_config = data.get('config', '')
        device = data.get('device', 'ccr2004')
        routeros_version = data.get('routeros_version', '7.19.4')
        
        if not raw_config:
            return jsonify({'error': 'No configuration provided'}), 400
        
        # Extract UNICORNMGMT CIDR from config to validate network calculation
        unicorn_cidr_match = re.search(r'address=(\d+\.\d+\.\d+\.\d+/\d+).*comment=UNICORNMGMT', raw_config)
        if unicorn_cidr_match:
            unicorn_cidr = unicorn_cidr_match.group(1)
            
            # Calculate network address using Nextlink convention: network = IP - 1
            try:
                import ipaddress
                # Parse the CIDR - extract IP and prefix
                cidr_parts = unicorn_cidr.split('/')
                user_ip = cidr_parts[0]
                prefix_len = int(cidr_parts[1]) if len(cidr_parts) > 1 else 29
                
                # Nextlink convention: Network = Gateway IP - 1
                # Example: Gateway 10.246.21.64 → Network 10.246.21.63
                ip_obj = ipaddress.IPv4Address(user_ip)
                network_obj = ipaddress.IPv4Address(int(ip_obj) - 1)
                network_addr = str(network_obj)
                
                print(f"[TARANA] User IP (Gateway): {user_ip}, Prefix: /{prefix_len}")
                print(f"[TARANA] Calculated Network (IP-1): {network_addr}/{prefix_len}")
                
                # Fix network address in config - replace both the IP address line and OSPF line
                # First, fix /ip address line - preserve user's IP but fix network parameter
                raw_config = re.sub(
                    r'(add address=)(\d+\.\d+\.\d+\.\d+)(/\d+ comment=UNICORNMGMT interface=UNICORNMGMT network=)(\d+\.\d+\.\d+\.\d+)',
                    rf'\1\2/{prefix_len}\3{network_addr}',
                    raw_config
                )
                
                # Fix OSPF networks parameter to use calculated network address
                raw_config = re.sub(
                    r'(networks=)(\d+\.\d+\.\d+\.\d+/\d+)',
                    rf'\1{network_addr}/{prefix_len}',
                    raw_config
                )
                
                print(f"[TARANA] Fixed network address: {network_addr}/{prefix_len}")
            except Exception as e:
                print(f"[TARANA] Network calculation error: {e}")
        
        # Use AI to validate and enhance the configuration
        training_context = build_training_context()
        system_prompt = f"""You are a Nextlink NOC MikroTik RouterOS configuration expert specializing in Tarana sector configurations.

Your task:
1. **CRITICAL**: Fix network address calculations using proper CIDR subnet mathematics
2. Ensure proper RouterOS v{routeros_version} syntax
3. Verify all bridge port assignments are correct
4. Check VLAN naming consistency
5. Ensure proper formatting and spacing
6. Validate IP addresses and network calculations

**CRITICAL NETWORK CALCULATION RULES (NEXTLINK CONVENTION):**
- **Nextlink Convention**: Network = Gateway IP - 1
- Example: Gateway IP 10.246.21.64/29 → Network = 10.246.21.63
- The address parameter keeps the user's IP (gateway)
- The network parameter is always IP - 1
- OSPF networks parameter MUST use (IP - 1)/prefix, not the gateway IP
- This is a Nextlink-specific convention for UNICORNMGMT networks

**VERIFICATION:**
- Check /ip address lines: network= parameter must be the calculated network address
- Check /routing ospf interface-template: networks= parameter must be network_address/prefix (not IP_address/prefix)

Return ONLY the corrected RouterOS configuration with proper network addresses calculated. NO explanations, NO markdown code blocks, just pure RouterOS commands."""
        
        if training_context:
            system_prompt += "\n\n" + training_context
        
        user_prompt = f"""Validate and correct this Tarana sector configuration for {device.upper()} running RouterOS {routeros_version}:

{raw_config}

Return the corrected configuration with proper network calculations and formatting."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            corrected_config = call_ai(messages, max_tokens=4000, task_type='validation')
            # Clean up any markdown formatting
            corrected_config = corrected_config.replace('```routeros', '').replace('```', '').strip()
            
            # Fallback to original if AI fails
            if not corrected_config or len(corrected_config) < 100:
                corrected_config = raw_config
        except Exception as e:
            print(f"[TARANA AI] Error: {e} - Using corrected network calculation")
            corrected_config = raw_config
        
        # Normalize and deduplicate before returning
        corrected_config = normalize_config(corrected_config)
        return jsonify({
            'success': True,
            'config': corrected_config,
            'device': device,
            'version': routeros_version
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========================================
# HEALTH CHECK
# ========================================

@app.route('/api/get-config-policies', methods=['GET'])
def get_config_policies():
    """Get list of available configuration policies with optional category filtering"""
    try:
        # Reload policies if requested
        if request.args.get('reload') == 'true':
            global CONFIG_POLICIES
            CONFIG_POLICIES = load_config_policies()
        
        # Filter by category if requested
        category_filter = request.args.get('category')
        
        policies_list = []
        for policy_name, policy_data in CONFIG_POLICIES.items():
            # Skip if category filter doesn't match
            if category_filter and policy_data.get('category') != category_filter:
                continue
            
            policies_list.append({
                'name': policy_name,
                'category': policy_data.get('category', 'unknown'),
                'filename': policy_data.get('filename', ''),
                'path': policy_data.get('path', ''),
                'relative_path': policy_data.get('relative_path', ''),
                'type': policy_data.get('type', 'markdown'),
                'description': policy_data.get('content', '')[:300] + '...' if len(policy_data.get('content', '')) > 300 else policy_data.get('content', '')
            })
        
        # Get unique categories
        categories = sorted(set(p.get('category', 'unknown') for p in CONFIG_POLICIES.values()))
        
        return jsonify({
            'success': True,
            'policies': policies_list,
            'count': len(policies_list),
            'total_policies': len(CONFIG_POLICIES),
            'categories': categories,
            'filtered_by': category_filter if category_filter else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-config-policy/<policy_name>', methods=['GET'])
def get_config_policy(policy_name):
    """Get a specific configuration policy by name"""
    try:
        if policy_name in CONFIG_POLICIES:
            return jsonify({
                'success': True,
                'policy_name': policy_name,
                'content': CONFIG_POLICIES[policy_name]['content'],
                'path': CONFIG_POLICIES[policy_name].get('path', '')
            })
        else:
            return jsonify({'error': f'Policy "{policy_name}" not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-config-policy-bundle', methods=['GET'])
def get_config_policy_bundle():
    """Return merged policy text for selected keys and optional references.
    Query params:
      keys: comma-separated policy keys (as listed by /api/get-config-policies)
      include: comma-separated extras: compliance,enterprise
    """
    try:
        keys_param = request.args.get('keys', '').strip()
        include_param = request.args.get('include', '').strip().lower()
        keys = [k.strip() for k in keys_param.split(',') if k.strip()] if keys_param else []
        includes = set([i.strip() for i in include_param.split(',') if i.strip()]) if include_param else set()

        parts = []
        for k in keys:
            p = CONFIG_POLICIES.get(k)
            if p and p.get('content'):
                parts.append(f"# POLICY: {k}\n\n{p['content'].strip()}\n")

        if 'compliance' in includes and 'compliance-reference' in CONFIG_POLICIES:
            parts.append(f"# REFERENCE: compliance\n\n{CONFIG_POLICIES['compliance-reference']['content'].strip()}\n")
        if 'enterprise' in includes and 'enterprise-reference' in CONFIG_POLICIES:
            parts.append(f"# REFERENCE: enterprise\n\n{CONFIG_POLICIES['enterprise-reference']['content'].strip()}\n")

        merged = "\n\n".join(parts).strip()
        return jsonify({'success': True, 'keys': keys, 'include': list(includes), 'content': merged})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reload-config-policies', methods=['POST'])
def reload_config_policies():
    """Reload configuration policies from disk"""
    try:
        global CONFIG_POLICIES
        CONFIG_POLICIES = load_config_policies()
        return jsonify({
            'success': True,
            'message': f'Reloaded {len(CONFIG_POLICIES)} policies',
            'policies': list(CONFIG_POLICIES.keys())
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Check if API server is running and configured"""
    # Check if Ollama is available
    ollama_available = False
    if AI_PROVIDER == 'ollama':
        try:
            resp = requests.get(f"{OLLAMA_API_URL}/api/tags", timeout=2)
            ollama_available = resp.status_code == 200
        except:
            pass
    
    return jsonify({
        'status': 'online',
        'ai_provider': AI_PROVIDER,
        'api_key_configured': bool(OPENAI_API_KEY) if AI_PROVIDER == 'openai' else None,
        'ollama_available': ollama_available if AI_PROVIDER == 'ollama' else None,
        'ollama_model': OLLAMA_MODEL if AI_PROVIDER == 'ollama' else None,
        'timestamp': datetime.now().isoformat()
    })

# ========================================
# RUN SERVER
# ========================================

# ========================================
# ENDPOINT 6: Completed Configs Storage
# ========================================

CONFIGS_DB_PATH = SECURE_DATA_DIR / "completed_configs.db"

def init_configs_db():
    """Initialize completed configs database in secure location"""
    conn = sqlite3.connect(str(CONFIGS_DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS completed_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_type TEXT NOT NULL,
            device_name TEXT,
            device_type TEXT,
            customer_code TEXT,
            loopback_ip TEXT,
            routeros_version TEXT,
            config_content TEXT NOT NULL,
            port_mapping TEXT,
            metadata TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT
        )
    ''')
    
    # Create indexes for faster searching
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_config_type ON completed_configs(config_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_customer_code ON completed_configs(customer_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON completed_configs(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_type ON completed_configs(device_type)')
    
    conn.commit()
    conn.close()
    print(f"[CONFIGS] Database initialized: {CONFIGS_DB_PATH}")

def extract_port_mapping(config_content):
    """Extract port mapping information from config"""
    port_mapping = {}
    
    # Extract interface ethernet settings
    ethernet_pattern = r'/interface ethernet\s+set\s+\[.*?default-name=([^\]]+)\].*?comment=([^\s\n]+)'
    ethernet_matches = re.findall(ethernet_pattern, config_content, re.MULTILINE | re.DOTALL)
    for port, comment in ethernet_matches:
        port_mapping[port.strip()] = {
            'comment': comment.strip(),
            'type': 'ethernet'
        }
    
    # Extract IP addresses with interfaces
    ip_pattern = r'/ip address\s+add\s+address=([^\s]+)\s+interface=([^\s\n]+)'
    ip_matches = re.findall(ip_pattern, config_content, re.MULTILINE)
    for ip, interface in ip_matches:
        if interface not in port_mapping:
            port_mapping[interface] = {}
        port_mapping[interface]['ip_address'] = ip.strip()
    
    # Extract bridge ports
    bridge_pattern = r'/interface bridge port\s+add\s+bridge=([^\s]+)\s+interface=([^\s\n]+)'
    bridge_matches = re.findall(bridge_pattern, config_content, re.MULTILINE)
    for bridge, interface in bridge_matches:
        if interface not in port_mapping:
            port_mapping[interface] = {}
        if 'bridges' not in port_mapping[interface]:
            port_mapping[interface]['bridges'] = []
        port_mapping[interface]['bridges'].append(bridge.strip())
    
    return port_mapping

@app.route('/api/save-completed-config', methods=['POST'])
def save_completed_config():
    """Save a completed configuration to the database"""
    try:
        init_configs_db()
        data = request.get_json(force=True)
        
        config_type = data.get('config_type', 'unknown')  # 'tower', 'enterprise', 'mpls-enterprise'
        device_name = data.get('device_name', '')
        device_type = data.get('device_type', '')
        customer_code = data.get('customer_code', '')
        loopback_ip = data.get('loopback_ip', '')
        routeros_version = data.get('routeros_version', '')
        config_content = data.get('config_content', '')
        
        if not config_content:
            return jsonify({'error': 'No configuration content provided'}), 400
        
        # Extract port mapping
        port_mapping = extract_port_mapping(config_content)
        port_mapping_json = json.dumps(port_mapping) if port_mapping else None
        
        # Store metadata
        metadata = {
            'site_name': data.get('site_name', ''),
            'router_id': data.get('router_id', ''),
            'lan_bridge_ip': data.get('lan_bridge_ip', ''),
            'ospf_area': data.get('ospf_area', ''),
            'bgp_peers': data.get('bgp_peers', []),
            'uplinks': data.get('uplinks', [])
        }
        metadata_json = json.dumps(metadata)
        
        # Get current time in Central Standard Time (CST/CDT)
        if HAS_PYTZ:
            cst_now = datetime.now(CST)
        else:
            # Fallback: calculate CST offset manually (UTC-6 for CST, UTC-5 for CDT)
            utc_now = datetime.utcnow()
            # Simple approximation: March-November is CDT (UTC-5), rest is CST (UTC-6)
            month = utc_now.month
            is_dst = 3 <= month <= 10  # Approximate DST period
            offset_hours = -5 if is_dst else -6
            from datetime import timedelta
            cst_now = utc_now + timedelta(hours=offset_hours)
        
        cst_timestamp = cst_now.strftime('%Y-%m-%d %H:%M:%S')
        
        conn = sqlite3.connect(str(CONFIGS_DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO completed_configs 
            (config_type, device_name, device_type, customer_code, loopback_ip, routeros_version, 
             config_content, port_mapping, metadata, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (config_type, device_name, device_type, customer_code, loopback_ip, routeros_version,
              config_content, port_mapping_json, metadata_json, data.get('created_by', 'user'), cst_timestamp))
        
        config_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'config_id': config_id,
            'message': 'Configuration saved successfully'
        })
        
    except Exception as e:
        print(f"[ERROR] Failed to save config: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-completed-configs', methods=['GET'])
def get_completed_configs():
    """Get all completed configurations with optional filtering"""
    try:
        init_configs_db()
        
        search_term = request.args.get('search', '').strip()
        year_filter = request.args.get('year', '').strip()
        type_filter = request.args.get('type', '').strip()
        
        conn = sqlite3.connect(str(CONFIGS_DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM completed_configs WHERE 1=1'
        params = []
        
        if type_filter:
            query += ' AND config_type = ?'
            params.append(type_filter)
        
        if year_filter:
            query += ' AND strftime("%Y", created_at) = ?'
            params.append(year_filter)
        
        if search_term:
            query += ' AND (device_name LIKE ? OR customer_code LIKE ? OR device_type LIKE ? OR loopback_ip LIKE ? OR config_content LIKE ?)'
            search_pattern = f'%{search_term}%'
            params.extend([search_pattern] * 5)
        
        query += ' ORDER BY created_at DESC'
        
        cursor.execute(query, params)
        configs = [dict(row) for row in cursor.fetchall()]
        
        # Get unique years
        cursor.execute('SELECT DISTINCT strftime("%Y", created_at) as year FROM completed_configs ORDER BY year DESC')
        years = [row[0] for row in cursor.fetchall() if row[0]]
        
        conn.close()
        
        return jsonify({
            'configs': configs,
            'years': years
        })
        
    except Exception as e:
        print(f"[ERROR] Failed to get configs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-completed-config/<int:config_id>', methods=['GET'])
def get_completed_config(config_id):
    """Get a specific completed configuration by ID"""
    try:
        init_configs_db()
        
        conn = sqlite3.connect(str(CONFIGS_DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM completed_configs WHERE id = ?', (config_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Configuration not found'}), 404
        
        config = dict(row)
        
        # Parse JSON fields
        if config.get('port_mapping'):
            try:
                config['port_mapping'] = json.loads(config['port_mapping'])
            except:
                config['port_mapping'] = {}
        
        if config.get('metadata'):
            try:
                config['metadata'] = json.loads(config['metadata'])
            except:
                config['metadata'] = {}
        
        return jsonify(config)
        
    except Exception as e:
        print(f"[ERROR] Failed to get config: {e}")
        return jsonify({'error': str(e)}), 500

# Initialize database on startup
init_configs_db()

if __name__ == '__main__':
    print("\n" + "="*50)
    print("NOC Config Maker - AI Backend Server")
    print("="*50)
    print(f"AI Provider: {AI_PROVIDER.upper()}")
    
    if AI_PROVIDER == 'ollama':
        print(f"Ollama Model: {OLLAMA_MODEL}")
        print(f"Ollama URL: {OLLAMA_API_URL}")
        print("\n[!] Make sure Ollama is installed and running!")
        print("    Install: https://ollama.com/download")
        print(f"    Then run: ollama pull {OLLAMA_MODEL}")
    else:
        print(f"OpenAI API Key: {'[CONFIGURED]' if OPENAI_API_KEY else '[MISSING]'}")
    
    print("\nEndpoints:")
    print("  POST /api/validate-config     - Validate RouterOS config")
    print("  POST /api/suggest-config      - Get AI suggestions")
    print("  POST /api/translate-config    - Translate between versions")
    print("  POST /api/apply-compliance    - Apply RFC-09-10-25 compliance standards")
    print("  POST /api/explain-config      - Explain config sections")
    print("  POST /api/autofill-from-export - Parse exported config")
    print("  GET  /api/get-config-policies - List available config policies")
    print("  GET  /api/get-config-policy/<name> - Get specific policy")
    print("  POST /api/reload-config-policies - Reload policies from disk")
    print("  GET  /api/health              - Health check")
    
    if HAS_COMPLIANCE:
        print("\n[COMPLIANCE] ✅ RFC-09-10-25 compliance enforcement is ENABLED")
        print("            All configs (Non-MPLS, MPLS, Upgrades) will include compliance standards")
    else:
        print("\n[WARN] ⚠️  RFC-09-10-25 compliance enforcement is DISABLED")
        print("       (nextlink_compliance_reference.py not found)")
    print("\nStarting server on http://localhost:5000")
    print("="*50 + "\n")
    
    # Run Flask server
    app.run(host='0.0.0.0', port=5000, debug=True)

