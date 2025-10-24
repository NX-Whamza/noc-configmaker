# Timeout and Size Limit Increases

## Problem
Ollama was timing out on large config files: "Ollama request timed out. The model might be too large or your system is under load."

## Solution: Increased ALL Timeouts and Limits

### 1. Backend (api_server.py)
**Ollama Request Timeout:**
- OLD: 120 seconds (2 minutes)
- NEW: 300 seconds (5 minutes)
- Location: Line 85

**Max Tokens (Output Size):**
- OLD: 4000 tokens default, 6000 for translation
- NEW: 16000 tokens default
- This allows for much larger RouterOS configs
- Location: Lines 124, 392

### 2. Frontend (NOC-configMaker.html)
**Fetch Timeout:**
- OLD: No explicit timeout (browser default ~30s)
- NEW: 300 seconds (5 minutes) with AbortController
- Location: Lines 6965-6982

**Status Message:**
- Updated to say "1-3 minutes" instead of "30-60 seconds"
- More realistic for large configs

### 3. Error Handling
Added proper handling for timeout errors:
- Detects AbortError and shows clear message
- Clears timeout when request completes successfully
- Better error messages for resource issues

## Why These Values?
- **5 minutes timeout**: Large RouterOS configs can be 2000+ lines
- **16000 tokens**: Allows output of configs up to ~12KB (plenty for any RouterOS device)
- **First run**: Ollama loads model into memory (15-30 seconds)
- **Subsequent runs**: Faster (5-15 seconds typically)

## Testing Recommendations
1. Small config (100 lines): Should complete in 10-20 seconds
2. Medium config (500 lines): Should complete in 30-60 seconds
3. Large config (1500+ lines): May take 1-3 minutes
4. If still timing out: Check system resources (CPU, RAM)

## What to Do If Still Slow
1. Close other applications (free RAM)
2. Check Ollama is using GPU if available
3. Consider smaller model (llama3.2:3b) for faster responses
4. Check system isn't thermal throttling (CPU overheating)

