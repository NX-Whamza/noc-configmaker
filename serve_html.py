#!/usr/bin/env python3
"""
Secure HTTP server to serve ONLY NOC-configMaker.html
Blocks directory listing and all other files for safety.
"""
import http.server
import socketserver
import webbrowser
import os
from pathlib import Path

PORT = 8000
ALLOWED_FILE = "NOC-configMaker.html"


class SecureHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def list_directory(self, path):
        self.send_error(403, "Forbidden")
        return None

    def do_GET(self):
        path = self.path.split('?')[0]
        clean_path = path.lstrip('/').strip()

        blocked_paths = {
            'secure_data', '.git', '__pycache__', '.env', 'api_server.py',
            'nextlink_compliance_reference.py', 'nextlink_enterprise_reference.py',
            'nextlink_constants.js', 'chat_history.db', 'completed_configs.db'
        }
        blocked_extensions = {'.db', '.py', '.js', '.md', '.bat', '.env', '.secret', '.key'}

        if '..' in clean_path or (clean_path and clean_path != ALLOWED_FILE and '/' in clean_path):
            self.send_error(404, "File not found")
            return

        if any(blocked in clean_path.lower() for blocked in blocked_paths):
            self.send_error(404, "File not found")
            return

        if any(clean_path.lower().endswith(ext) for ext in blocked_extensions):
            self.send_error(404, "File not found")
            return

        if clean_path == "" or clean_path == "/":
            self.send_response(302)
            self.send_header('Location', f'/{ALLOWED_FILE}')
            self.end_headers()
            return

        if clean_path == ALLOWED_FILE:
            file_path = Path(ALLOWED_FILE)
            if not file_path.exists() or not file_path.is_file():
                self.send_error(404, "File not found")
                return
            with open(file_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404, "File not found")

    def do_HEAD(self):
        path = self.path.split('?')[0]
        clean_path = path.lstrip('/').strip()
        if '..' in clean_path or (clean_path and clean_path != ALLOWED_FILE and '/' in clean_path):
            self.send_error(404, "File not found")
            return
        if clean_path == "" or clean_path == "/":
            self.send_response(302)
            self.send_header('Location', f'/{ALLOWED_FILE}')
            self.end_headers()
        elif clean_path == ALLOWED_FILE:
            file_path = Path(ALLOWED_FILE)
            if file_path.exists() and file_path.is_file():
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(file_path.stat().st_size))
                self.end_headers()
            else:
                self.send_error(404, "File not found")
        else:
            self.send_error(404, "File not found")

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('X-XSS-Protection', '1; mode=block')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def log_message(self, format, *args):
        # Only log successful access to the UI file
        if args and len(args) >= 2 and args[0] == 'GET' and (args[1] == f'/{ALLOWED_FILE}' or args[1] == '/'):
            super().log_message(format, *args)
        # Suppress noisy 404 logs


def main():
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    Handler = SecureHTTPRequestHandler
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print("=" * 60)
        print("NOC Config Maker - Secure HTTP Server")
        print("=" * 60)
        print(f"\nServer running on http://localhost:{PORT}")
        print(f"Open: http://localhost:{PORT}/NOC-configMaker.html")
        print("\nSECURITY ENABLED:")
        print("   - Directory listing: BLOCKED (403)")
        print("   - File browsing: BLOCKED (404)")
        print(f"   - Only {ALLOWED_FILE} is accessible")
        print("   - All other files/directories are hidden")

        # Resolve local IP for LAN access
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            print(f"\nNetwork access: http://{local_ip}:{PORT}/NOC-configMaker.html")
        except Exception:
            print(f"\nNetwork access: http://<your-ip>:{PORT}/NOC-configMaker.html")

        print("\nKeep this window open while using the tool")
        print("   Press Ctrl+C to stop the server\n")
        print("=" * 60)

        try:
            webbrowser.open(f'http://localhost:{PORT}/NOC-configMaker.html')
        except Exception:
            pass

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == '__main__':
    main()

