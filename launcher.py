#!/usr/bin/env python3
"""FontoGo local launcher.

Serves the HTML prototype on localhost and checks GitHub for updates.
For safety, updates are only fast-forwarded when the checkout is clean.
Set FONTOGO_DISABLE_UPDATES=1 to skip the update check.
"""
from __future__ import annotations
import http.server
import os
import socketserver
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
REPO = "sergeshi/FontoGo"
BRANCH = "main"
PORT = int(os.environ.get("FONTOGO_PORT", "8765"))


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=20)


def check_updates() -> None:
    if os.environ.get("FONTOGO_DISABLE_UPDATES") == "1":
        print("[FontoGo] Update check disabled by environment.")
        return
    if not (ROOT / ".git").exists():
        print("[FontoGo] No .git directory; skipping self-update.")
        return
    status = git("status", "--porcelain")
    if status.returncode != 0:
        print("[FontoGo] Git status failed; skipping update.")
        return
    if status.stdout.strip():
        print("[FontoGo] Local changes detected. Not updating to protect your work.")
        return
    try:
        print("[FontoGo] Checking GitHub for updates…")
        fetch = git("fetch", "--quiet", "origin", BRANCH)
        if fetch.returncode != 0:
            print("[FontoGo] Git fetch failed; continuing with current version.")
            return
        local = git("rev-parse", "HEAD").stdout.strip()
        remote = git("rev-parse", f"origin/{BRANCH}").stdout.strip()
        if not local or not remote or local == remote:
            print("[FontoGo] Already up to date.")
            return
        ancestor = git("merge-base", "--is-ancestor", "HEAD", f"origin/{BRANCH}")
        if ancestor.returncode != 0:
            print("[FontoGo] Remote history diverged; no automatic update was applied.")
            return
        pull = git("merge", "--ff-only", f"origin/{BRANCH}")
        if pull.returncode == 0:
            print("[FontoGo] Updated to latest fast-forward commit.")
        else:
            print("[FontoGo] Update failed safely; continuing with current version.")
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(f"[FontoGo] Update check unavailable ({exc}); continuing offline.")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        print("[HTTP] " + (fmt % args))


def main() -> int:
    check_updates()
    os.chdir(ROOT)
    try:
        with socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler) as server:
            server.daemon_threads = True
            url = f"http://127.0.0.1:{PORT}/"
            print(f"[FontoGo] Running at {url} (Ctrl+C to stop)")
            threading.Timer(0.8, lambda: webbrowser.open(url)).start()
            server.serve_forever()
    except OSError as exc:
        print(f"[FontoGo] Cannot start local server on port {PORT}: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n[FontoGo] Closed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
