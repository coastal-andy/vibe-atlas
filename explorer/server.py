"""Vibe Atlas local server.

Serves the project folder and adds a few local-only endpoints:
  GET  /api/saved            -> {folder: [filenames]} of images saved under refs/images/
  POST /api/save             -> {"items":[{"url","folder","name"}]} downloads images into refs/images/<folder>/
  POST /api/pins             -> stores the full Pinterest pin list at refs/pinterest_all_pins.json
  POST /api/export           -> {"name","dataUrl"} writes a poster PNG into posters/

Binds to 127.0.0.1 only. Downloads are limited to Pinterest's and archive.org's image hosts.
Run from the project root:  python3 explorer/server.py
"""
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES = os.path.join(ROOT, "refs", "images")
POSTERS = os.path.join(ROOT, "posters")
PORT = int(os.environ.get("PORT", "8765"))
ALLOWED_HOSTS = re.compile(r"^(i\.pinimg\.com|archive\.org|([a-z0-9-]+\.)*archive\.org|[0-9]+\.media\.tumblr\.com)$")
PIN_ORIGINS = {"https://www.pinterest.com", "https://pinterest.com"}
INGEST_TARGETS = {"cari": "refs/cari.json", "gurafiku": "refs/gurafiku.json"}
SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def safe_name(s, default="item"):
    s = SAFE.sub("-", s or "").strip("-.")
    return s[:120] or default


def fetch_to(url, path):
    host = urllib.parse.urlparse(url).hostname or ""
    if not ALLOWED_HOSTS.match(host):
        return "host not allowed"
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return "exists"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (VibeAtlas local)"})
    last = None
    for attempt in range(4):  # flaky connections: retry with backoff
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                final_host = urllib.parse.urlparse(r.geturl()).hostname or ""
                if not ALLOWED_HOSTS.match(final_host):
                    return "redirected to disallowed host"
                data = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 410):
                return "error: HTTP %d" % e.code
            last = e
        except Exception as e:
            last = e
        time.sleep(1.5 * (attempt + 1))
    else:
        return "error: %s" % last
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)
    return "saved"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, fmt, *args):
        if "/api/" in (self.path or ""):
            sys.stderr.write("%s\n" % (fmt % args))

    def _cors(self):
        origin = self.headers.get("Origin", "")
        if origin in PIN_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Private-Network", "true")

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _body(self, limit=50_000_000):
        n = int(self.headers.get("Content-Length", "0"))
        if n > limit:
            raise ValueError("body too large")
        raw = self.rfile.read(n)
        ctype = self.headers.get("Content-Type", "")
        if "application/x-www-form-urlencoded" in ctype:
            return json.loads(urllib.parse.parse_qs(raw.decode())["payload"][0])
        return json.loads(raw or b"{}")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/saved"):
            out = {}
            if os.path.isdir(IMAGES):
                for folder in sorted(os.listdir(IMAGES)):
                    p = os.path.join(IMAGES, folder)
                    if os.path.isdir(p):
                        out[folder] = sorted(f for f in os.listdir(p) if not f.endswith(".part"))
            return self._json(200, out)
        return super().do_GET()

    def do_POST(self):
        try:
            if self.path == "/api/pins":
                if self.headers.get("Origin", "") not in PIN_ORIGINS | {"null", ""} and not self.headers.get("Origin", "").startswith("http://127.0.0.1") and not self.headers.get("Origin", "").startswith("http://localhost"):
                    return self._json(403, {"error": "origin not allowed"})
                data = self._body()
                if not isinstance(data, dict) or "pins" not in data:
                    return self._json(400, {"error": "expected {pins: [...]}"})
                with open(os.path.join(ROOT, "refs", "pinterest_all_pins.json"), "w") as f:
                    json.dump(data, f)
                if "text/html" in self.headers.get("Accept", ""):
                    body = f"<p>Saved {len(data['pins'])} pins. You can close this tab.</p>".encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(body)
                    return
                return self._json(200, {"saved": len(data["pins"])})

            if self.path.startswith("/api/ingest"):
                target = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("target", [""])[0]
                if target not in INGEST_TARGETS:
                    return self._json(400, {"error": "unknown target"})
                data = self._body()
                with open(os.path.join(ROOT, INGEST_TARGETS[target]), "w") as f:
                    json.dump(data, f)
                return self._json(200, {"saved": len(data.get("items", [])), "target": target})

            if self.path == "/api/save":
                items = self._body().get("items", [])[:500]

                def one(it):
                    folder = safe_name(it.get("folder"), "misc")
                    url = it.get("url", "")
                    ext = os.path.splitext(urllib.parse.urlparse(url).path)[1][:5] or ".jpg"
                    name = safe_name(it.get("name") or os.path.basename(urllib.parse.urlparse(url).path))
                    if not name.lower().endswith(ext.lower()):
                        name += ext
                    path = os.path.join(IMAGES, folder, name)
                    try:
                        status = fetch_to(url, path)
                    except Exception as e:  # network errors are reported per item
                        status = "error: %s" % e
                    return {"url": url, "status": status, "local": f"/refs/images/{folder}/{name}" if status in ("saved", "exists") else None}

                with ThreadPoolExecutor(max_workers=6) as ex:
                    results = list(ex.map(one, items))
                return self._json(200, {"results": results})

            if self.path == "/api/export":
                data = self._body()
                m = re.match(r"^data:image/png;base64,(.+)$", data.get("dataUrl", ""))
                if not m:
                    return self._json(400, {"error": "expected a PNG data URL"})
                os.makedirs(POSTERS, exist_ok=True)
                name = safe_name(data.get("name"), "poster") + ".png"
                with open(os.path.join(POSTERS, name), "wb") as f:
                    f.write(base64.b64decode(m.group(1)))
                return self._json(200, {"path": f"posters/{name}"})

            return self._json(404, {"error": "unknown endpoint"})
        except Exception as e:
            return self._json(500, {"error": str(e)})


if __name__ == "__main__":
    os.chdir(ROOT)
    print(f"Vibe Atlas on http://127.0.0.1:{PORT}/explorer/")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
