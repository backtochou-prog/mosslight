"""Serve the project folder so the live viewer can fetch its data: python3 preview/serve.py"""
import http.server, os, sys
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
print(f"open http://localhost:{port}/preview/world.html")
http.server.ThreadingHTTPServer(("127.0.0.1", port), http.server.SimpleHTTPRequestHandler).serve_forever()
