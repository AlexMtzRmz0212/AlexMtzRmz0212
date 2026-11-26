"""Local preview of this profile README, rendered by GitHub's own Markdown API.

Run DEV.bat (or: python preview.py). Opens http://localhost:5183 and reloads the page
whenever README.md or a file in assets/ changes. Standard library only.

README.md is sent to api.github.com/markdown to render it (no login needed: 60 renders
an hour, and an unchanged file is never sent twice). Set GITHUB_TOKEN to raise the limit.
Images made by the GitHub Actions workflows show their last committed version.
"""

import hashlib
import html
import json
import os
import sys
import threading
import urllib.error
import urllib.request
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

PORT = 5183
ROOT = os.path.dirname(os.path.abspath(__file__))
README = os.path.join(ROOT, "README.md")
REPO = "AlexMtzRmz0212/AlexMtzRmz0212"

_cache: dict[str, str] = {}


def render(markdown: str) -> str:
    key = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    if key in _cache:
        return _cache[key]
    body = json.dumps({"text": markdown, "mode": "gfm", "context": REPO}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/markdown",
        data=body,
        headers={
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "profile-readme-preview",
        },
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=20) as res:
        out = res.read().decode("utf-8")
    _cache.clear()
    _cache[key] = out
    return out


def stamp() -> str:
    """Changes whenever README.md or anything in assets/ changes."""
    parts = []
    for folder, _dirs, files in os.walk(ROOT):
        if ".git" in folder:
            continue
        for f in files:
            if f == "README.md" or folder.startswith(os.path.join(ROOT, "assets")):
                p = os.path.join(folder, f)
                try:
                    parts.append(f"{p}:{os.stat(p).st_mtime_ns}")
                except OSError:
                    pass
    return hashlib.md5("|".join(sorted(parts)).encode()).hexdigest()


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Profile README preview</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/github-markdown-css@5/github-markdown.min.css">
<style>
  :root {{ color-scheme: light dark; }}
  body {{ margin: 0; background: #f6f8fa; font: 14px -apple-system, "Segoe UI", sans-serif; }}
  @media (prefers-color-scheme: dark) {{ body {{ background: #010409; }} }}
  .bar {{ position: sticky; top: 0; z-index: 1; display: flex; gap: 8px; align-items: center;
         padding: 8px 16px; background: rgba(127,127,127,.12); backdrop-filter: blur(8px); color: #8b949e; }}
  .bar b {{ color: inherit; font-weight: 600; margin-right: auto; }}
  .bar button {{ padding: 4px 10px; border: 1px solid rgba(127,127,127,.4); border-radius: 6px;
                background: transparent; color: inherit; cursor: pointer; }}
  .bar button[aria-pressed=true] {{ background: rgba(127,127,127,.25); }}
  main {{ box-sizing: border-box; margin: 24px auto 64px; padding: 24px 32px; border: 1px solid rgba(127,127,127,.3);
          border-radius: 6px; max-width: 896px; }}
  body.full main {{ max-width: none; margin: 16px; }}
  .error {{ color: #f85149; white-space: pre-wrap; }}
</style>
</head>
<body>
<div class="bar">
  <b>README.md preview &middot; refreshes when you save</b>
  <button id="w" aria-pressed="false">Full width</button>
</div>
<main class="markdown-body">{content}</main>
<script>
  const w = document.getElementById('w');
  const set = (on) => {{ document.body.classList.toggle('full', on); w.setAttribute('aria-pressed', on); localStorage.full = on ? '1' : ''; }};
  set(!!localStorage.full);
  w.onclick = () => set(!document.body.classList.contains('full'));
  let last = '{stamp}';
  setInterval(async () => {{
    try {{
      const s = await (await fetch('/__stamp', {{ cache: 'no-store' }})).text();
      if (s !== last) location.reload();
    }} catch {{}}
  }}, 1000);
</script>
</body>
</html>"""


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            return self.send_page()
        if path == "/__stamp":
            return self.send_text(stamp(), "text/plain")
        return super().do_GET()

    def send_page(self):
        current = stamp()
        try:
            with open(README, encoding="utf-8") as f:
                content = render(f.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")
            content = f'<p class="error">GitHub could not render README.md ({e.code}).\n{html.escape(detail)}</p>'
        except Exception as e:  # offline, timeout, missing file
            content = f'<p class="error">Could not render README.md: {html.escape(str(e))}</p>'
        self.send_text(PAGE.format(content=content, stamp=current), "text/html")

    def send_text(self, text: str, ctype: str):
        data = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")  # edited SVGs show up on reload
        super().end_headers()

    def log_message(self, fmt, *args):
        if "/__stamp" not in (str(args[0]) if args else ""):
            sys.stderr.write("%s\n" % (fmt % args))


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), partial(Handler, directory=ROOT))
    url = f"http://localhost:{PORT}/"
    print(f"Previewing README.md at {url}  (close this window to stop)")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.5, webbrowser.open, [url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
