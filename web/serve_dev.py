#!/usr/bin/env python3
"""Drop-in replacement for `python3 -m http.server 5500` that adds
`Cache-Control: no-store` to every response.

Why this exists: plain http.server sends no Cache-Control header at all,
which leaves browsers (and Cloudflare, when this is exposed through the
test tunnel) free to apply their own heuristic caching to style.css/the JS
modules - which is exactly what turned several real CSS/JS fixes into
hours of "it's still not showing up" during mobile testing, since a
version-query-string on one <script src="main.js"> tag doesn't cover the
dozen other files main.js itself `import`s with plain relative paths (each
one is its own cacheable request). No-store on every response here closes
that off at the root instead of chasing it file by file.

Usage: same as http.server - `python3 serve_dev.py` (defaults to port
5500) or `python3 serve_dev.py 5500`.
"""
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5500
    HTTPServer(("", port), NoCacheHandler).serve_forever()
