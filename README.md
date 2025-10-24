# 🚀 NOC Config Maker - AI-Powered RouterOS Configuration Tool

## 🎯 Overview
An intelligent configuration generator for MikroTik RouterOS devices with AI-powered validation, translation, and chat assistance.

## ✨ Features

### 🤖 **AI-Powered Configuration**
- **Smart Config Generation** - AI creates RouterOS configs from minimal input
- **Auto-Validation** - Validates configurations before deployment
- **Version Translation** - Converts RouterOS v6 to v7 syntax
- **AI Suggestions** - Intelligent recommendations for optimization

### 💬 **Chat Memory System**
- **Persistent Memory** - Remembers all conversations across sessions
- **User Context** - Learns your preferences and working style
- **Session Management** - Multiple users with individual chat histories
- **Export Capability** - Save chat history as JSON

### 🏢 **Enterprise Features**
- **Non-MPLS Enterprise** - Simplified configs for enterprise customers
- **Tower MikroTik** - Specialized tower configurations
- **MPLS/VPLS** - Advanced MPLS configurations
- **Upgrade Existing** - Migrate existing configs to newer versions

### 🔧 **Technical Capabilities**
- **RouterOS v6→v7 Migration** - Automated syntax conversion
- **OSPF/BGP Translation** - Protocol-specific upgrades
- **Firewall Rules** - Dynamic firewall generation
- **IP Management** - CIDR parsing and DHCP pools
- **SNMP/DNS/NTP** - Standard network services

## 🚀 Quick Start

### **Option 1: Local Development**
```bash
# Clone the repository
git clone https://github.com/yourusername/noc-configmaker.git
cd noc-configmaker

# Install dependencies
pip install -r requirements.txt

# Start the backend
start_backend.bat

# Open the tool
# Navigate to http://localhost:5000/chat for AI chat
# Or use the HTML tool directly
```

### **Option 2: Dedicated AI Server**
```bash
# On your dedicated server PC
deploy_ai_server.bat

# On your client machine
client_setup.bat
```

## 📁 Project Structure

```
noc-configmaker/
├── api_server.py              # Flask backend with AI integration
├── NOC-configMaker.html      # Main configuration tool UI
├── requirements.txt          # Python dependencies
├── start_backend.bat         # Local development startup
├── start_webui.bat          # Open WebUI integration
├── deploy_ai_server.bat     # Dedicated server deployment
├── client_setup.bat         # Client configuration
├── ros-migration-trainer-v3/ # AI training data
│   ├── ai-consistency-rules.json
│   ├── nextlink-styleguide.md
│   ├── routing-ospf.json
│   ├── routing-bgp.json
│   └── ... (more training files)
├── chat_history.db          # SQLite chat database
└── docs/                   # Documentation
```

## 🤖 AI Models Supported

- **phi3:mini** - Fast, reliable for most tasks
- **qwen2.5-coder:7b** - Excellent for complex translations
- **llama3.2:3b** - Quick tasks and simple chat

## 🔌 API Endpoints

### **Configuration Generation**
- `POST /api/validate-config` - Validate RouterOS config
- `POST /api/suggest-config` - Get AI suggestions
- `POST /api/translate-config` - Translate between versions
- `POST /api/autofill-from-export` - Parse exported config

### **Chat & Memory**
- `POST /api/chat` - Chat with AI (with memory)
- `GET /api/chat/history/{session_id}` - Get chat history
- `GET /api/chat/context/{session_id}` - Get user context
- `POST /api/chat/context/{session_id}` - Update user context
- `GET /api/chat/export/{session_id}` - Export chat history

### **OpenAI-Compatible**
- `GET /v1/models` - List available models
- `POST /v1/chat/completions` - OpenAI-compatible chat

## 🎯 Usage Examples

### **Generate Enterprise Configuration**
```javascript
fetch('/api/gen-enterprise-non-mpls', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        device: 'CCR2004',
        version: '7.15',
        customer: 'Acme Corp',
        loopback: '10.0.0.1',
        public_ip: '203.0.113.1',
        backhaul_ip: '192.168.1.0/24'
    })
})
```

### **Chat with Memory**
```javascript
fetch('/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        message: "Help me configure OSPF",
        session_id: "user123"
    })
})
```

### **Translate RouterOS v6 to v7**
```javascript
fetch('/api/translate-config', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        config: "/routing ospf area add area-id=0.0.0.0",
        target_version: "7"
    })
})
```

## 🔧 Configuration

### **Environment Variables**
```bash
AI_PROVIDER=ollama                    # AI provider (ollama/openai)
OLLAMA_MODEL=phi3:mini               # Default Ollama model
ROS_TRAINING_DIR=./ros-migration-trainer-v3  # Training data directory
```

### **Open WebUI Integration**
1. Install Open WebUI: `start_webui.bat`
2. Configure provider: OpenAI (custom)
3. Base URL: `http://localhost:5000/v1`
4. API Key: `noc-local`
5. Model: `noc-local`

## 📊 Training Data

The AI is trained on:
- **RouterOS Documentation** - Official MikroTik docs
- **Nextlink Standards** - Company-specific conventions
- **Migration Rules** - v6→v7 syntax mappings
- **Best Practices** - Network engineering standards

## 🚀 Deployment Options

### **Local Development**
- Single machine setup
- All services on localhost
- Perfect for testing and development

### **Dedicated AI Server**
- Separate PC for AI workloads
- Accessible from anywhere
- Better performance for large configs
- Centralized chat history

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check the `docs/` folder
- **Issues**: Create a GitHub issue
- **Chat**: Use the built-in AI chat for help

## 🎯 Roadmap

- [ ] Web-based configuration interface
- [ ] Multi-tenant support
- [ ] Advanced analytics
- [ ] Integration with network monitoring
- [ ] Automated testing framework

---

**Built with ❤️ for Network Engineers**