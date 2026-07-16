#!/usr/bin/env python3
"""
Local server for the JobLink dashboard + its chart-reading assistant.

The Groq API key is read from the environment and never reaches the browser:
the page calls /api/chat on this server, and this server calls Groq.

Run:
    export GROQ_API_KEY=gsk_your_key_here
    python3 serve.py

Then open http://localhost:8765
"""

import json
import os
import sys
import urllib.error
import urllib.request
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = int(os.environ.get("PORT", "8765"))
HOST = os.environ.get("HOST", "127.0.0.1")  # cloud hosts set HOST=0.0.0.0
KEY = os.environ.get("GROQ_API_KEY", "").strip()
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"  # the vision model on Groq
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
ROOT = os.path.dirname(os.path.abspath(__file__))

MAX_BODY = 24 * 1024 * 1024  # screenshots arrive as base64; leave room


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def guess_type(self, path):
        # The dashboard HTML has no <meta charset> (it's authored to be wrapped
        # elsewhere), so declare UTF-8 here or the browser mis-decodes em-dashes
        # and middots into mojibake.
        t = super().guess_type(path)
        base = t[0] if isinstance(t, tuple) else t
        if base in ("text/html", "text/plain", "text/css", "application/javascript", "text/javascript"):
            return base + "; charset=utf-8"
        return t

    def do_GET(self):
        if self.path.split("?")[0] == "/api/health":
            return self._json(200, {"ok": bool(KEY), "model": MODEL})
        if self.path in ("/", ""):
            self.path = "/dashboard.html"
        return super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] != "/api/chat":
            return self._json(404, {"error": "not found"})
        if not KEY:
            return self._json(500, {"error": "GROQ_API_KEY is not set. Stop the server, export it, and restart."})

        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._json(400, {"error": "bad content length"})
        if length <= 0 or length > MAX_BODY:
            return self._json(413, {"error": "request too large — try a smaller screenshot"})

        try:
            payload = json.loads(self.rfile.read(length))
            messages = payload["messages"]
        except Exception:
            return self._json(400, {"error": "malformed request"})

        body = json.dumps({
            "model": MODEL,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.2,
        }).encode()

        req = urllib.request.Request(GROQ_URL, data=body, headers={
            "Authorization": "Bearer " + KEY,
            "Content-Type": "application/json",
            # Groq sits behind Cloudflare, which 403s (error 1010) the default
            # urllib user-agent. Any real UA string gets through.
            "User-Agent": "joblink-dashboard/1.0",
        })

        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.load(r)
            return self._json(200, {
                "reply": data["choices"][0]["message"]["content"],
                "usage": data.get("usage", {}),
            })
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            try:
                detail = json.loads(detail).get("error", {}).get("message", detail)
            except Exception:
                pass
            return self._json(e.code, {"error": f"Groq returned {e.code}: {detail}"})
        except Exception as e:
            return self._json(502, {"error": f"Could not reach Groq: {e}"})

    def _json(self, code, obj):
        raw = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt, *args):
        if "/api/" in (args[0] if args else ""):
            sys.stderr.write("  %s\n" % (fmt % args))


if __name__ == "__main__":
    if not KEY:
        print("! GROQ_API_KEY is not set — the dashboard will load, but the assistant will be hidden.")
        print("  export GROQ_API_KEY=gsk_...   then restart.\n")
    print(f"JobLink dashboard  →  http://localhost:{PORT}")
    print(f"assistant model    →  {MODEL}")
    print("Ctrl+C to stop.\n")
    try:
        HTTPServer((HOST, PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
