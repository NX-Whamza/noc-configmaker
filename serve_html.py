#!/usr/bin/env python3
"""
Secure HTTP server to serve ONLY NOC-configMaker.html
SECURITY: Blocks directory listing, blocks all other files, only serves the UI
"""
import http.server
import socketserver
import webbrowser
import os
from pathlib import Path

PORT = 8000

# Only file that can be served
ALLOWED_FILE = "NOC-configMaker.html"

class SecureHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Secure handler that only serves NOC-configMaker.html and blocks everything else"""
    
    def list_directory(self, path):
        """BLOCK directory listing completely - return 403 Forbidden"""
        self.send_error(403, "Forbidden")
        return None
    
    def do_GET(self):
        """Only allow access to NOC-configMaker.html, block everything else"""
        # Parse the requested path - CRITICAL: Do this FIRST before parent class touches anything
        path = self.path.split('?')[0]  # Remove query string
        clean_path = path.lstrip('/').strip()
        
        # Block any path traversal attempts immediately
        # Also block sensitive directories and file types
        blocked_paths = ['secure_data', '.git', '__pycache__', '.env', 'api_server.py', 
                         'nextlink_compliance_reference.py', 'nextlink_enterprise_reference.py',
                         'nextlink_constants.js', 'chat_history.db', 'completed_configs.db']
        blocked_extensions = ['.db', '.py', '.js', '.md', '.bat', '.env', '.secret', '.key']
        
        if '..' in clean_path or (clean_path and clean_path != ALLOWED_FILE and '/' in clean_path):
            self.send_error(404, "File not found")
            return
        
        # Block access to sensitive directories and files
        if any(blocked in clean_path.lower() for blocked in blocked_paths):
            self.send_error(404, "File not found")
            return
        
        # Block sensitive file extensions
        if any(clean_path.lower().endswith(ext) for ext in blocked_extensions):
            self.send_error(404, "File not found")
            return
        
        # Handle root path - redirect IMMEDIATELY (don't let parent class see it)
        if clean_path == "" or clean_path == "/" or not clean_path:
            self.send_response(302)
            self.send_header('Location', f'/{ALLOWED_FILE}')
            self.end_headers()
            return
        
        # Only allow the exact file name
        if clean_path == ALLOWED_FILE:
            # Serve the allowed file directly
            try:
                file_path = Path(ALLOWED_FILE)
                if not file_path.exists() or not file_path.is_file():
                    self.send_error(404, "File not found")
                    return
                
                # Read and serve the file
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception:
                self.send_error(500, "Internal server error")
        else:
            # Block ALL other files, directories, and paths - return 404
            # This prevents directory listing and file browsing
            self.send_error(404, "File not found")
    
    def do_HEAD(self):
        """Handle HEAD requests - same security restrictions as GET"""
        path = self.path.split('?')[0]
        clean_path = path.lstrip('/').strip()
        
        # Block path traversal
        if '..' in clean_path or (clean_path and clean_path != ALLOWED_FILE and '/' in clean_path):
            self.send_error(404, "File not found")
            return
        
        # Root path redirect
        if clean_path == "" or clean_path == "/" or not clean_path:
            self.send_response(302)
            self.send_header('Location', f'/{ALLOWED_FILE}')
            self.end_headers()
        elif clean_path == ALLOWED_FILE:
            try:
                file_path = Path(ALLOWED_FILE)
                if file_path.exists() and file_path.is_file():
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(file_path.stat().st_size))
                    self.end_headers()
                else:
                    self.send_error(404, "File not found")
            except:
                self.send_error(404, "File not found")
        else:
            self.send_error(404, "File not found")
    
    def end_headers(self):
        """Add security headers and CORS"""
        # Security headers
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('X-XSS-Protection', '1; mode=block')
        # CORS headers for API requests (from frontend)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def log_message(self, format, *args):
        """Custom logging - hide sensitive paths"""
        # Only log successful access to the UI file
        if args[0] == "GET" and (args[1] == f"/{ALLOWED_FILE}" or args[1] == "/"):
            super().log_message(format, *args)
        # Silently ignore blocked requests (don't log 404s to avoid information leakage)

def main():
    # Change to the script's directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    Handler = SecureHTTPRequestHandler
    
    # Bind to all interfaces (0.0.0.0) to allow network access
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print("=" * 60)
        print("NOC Config Maker - Secure HTTP Server")
        print("=" * 60)
        print(f"\n✅ Server running on http://localhost:{PORT}")
        print(f"📄 Open: http://localhost:{PORT}/NOC-configMaker.html")
        print(f"\n🔒 SECURITY ENABLED:")
        print(f"   ✓ Directory listing: BLOCKED (403)")
        print(f"   ✓ File browsing: BLOCKED (404)")
        print(f"   ✓ Only {ALLOWED_FILE} is accessible")
        print(f"   ✓ All other files/directories are hidden")
        
        # Get local IP address for network access
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            print(f"\n🌐 Network access: http://{local_ip}:{PORT}/NOC-configMaker.html")
        except:
            print(f"\n🌐 Network access: http://<your-ip>:{PORT}/NOC-configMaker.html")
        print("\n⚠️  Keep this window open while using the tool")
        print("   Press Ctrl+C to stop the server\n")
        print("=" * 60)
        
        # Auto-open browser
        try:
            webbrowser.open(f'http://localhost:{PORT}/NOC-configMaker.html')
        except:
            pass
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n🛑 Server stopped.")

if __name__ == '__main__':
    main()

