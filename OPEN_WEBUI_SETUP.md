# Open WebUI Setup for NOC Config Maker

## Current Status ✅
- **Our Backend**: Running on `http://localhost:5000` (AI API with smart model selection)
- **Open WebUI**: Starting on `http://localhost:3000` (Chat interface)

## Configuration Steps

### 1. Open WebUI Setup
1. Go to `http://localhost:3000`
2. Click **Settings** (gear icon)
3. Go to **Connections** tab
4. Add new connection:
   - **Provider**: `OpenAI (Custom)`
   - **Base URL**: `http://localhost:5000/v1`
   - **API Key**: `noc-local` (any non-empty value)
   - **Model**: `noc-local`

### 2. Test the Connection
1. Create a new chat
2. Ask: "What do you know about MikroTik RouterOS?"
3. The AI should respond using our enhanced backend with MikroTik documentation

## What Our Backend Provides
- **Smart Model Selection**: Auto-chooses best model for each task
- **MikroTik Knowledge**: Official RouterOS, OSPF, BGP, Firewall docs
- **RouterOS Expertise**: Translation, validation, suggestions
- **Nextlink Standards**: Your company's naming and configuration rules

## Troubleshooting
- If Open WebUI shows "Connection failed": Check that our backend is running on port 5000
- If responses are slow: First request loads the AI model (normal)
- If no response: Check backend logs for errors

## Next Steps
Once connected, you can:
1. **Chat with RouterOS expert AI** for configuration help
2. **Create Nextlink policies** using the AI's knowledge
3. **Translate configs** between RouterOS versions
4. **Validate configurations** before deployment
