#!/usr/bin/env python3
"""
Simple HTTP server to serve NOC-configMaker.html
This resolves CORS issues when opening HTML files directly from file system
"""
import http.server
import socketserver
import webbrowser
import os
from pathlib import Path

PORT = 8000

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers to allow API requests
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def main():
    # Change to the script's directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    Handler = MyHTTPRequestHandler
    
    # Bind to all interfaces (0.0.0.0) to allow network access
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print("=" * 60)
        print("NOC Config Maker - HTTP Server")
        print("=" * 60)
        print(f"\n✅ Server running on http://localhost:{PORT}")
        print(f"📄 Open: http://localhost:{PORT}/NOC-configMaker.html")
        
        # Get local IP address for network access
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            print(f"🌐 Network access: http://{local_ip}:{PORT}/NOC-configMaker.html")
        except:
            print(f"🌐 Network access: http://<your-ip>:{PORT}/NOC-configMaker.html")
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

