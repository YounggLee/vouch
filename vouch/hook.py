import json
import re
import subprocess
import sys

from vouch import cmux


_SURFACE_REF_RE = re.compile(r"surface:[A-Za-z0-9-]+")


def stop(args=None) -> int:
    source_surface = cmux.discover_source_surface(None)
    try:
        payload = sys.stdin.read()
        if payload:
            json.loads(payload)
    except Exception:
        pass
    ws = cmux.workspace_id()
    if not ws:
        print("[vouch hook] no CMUX_WORKSPACE_ID — skip auto-launch", file=sys.stderr)
        return 0
    cmux.notify("vouch", "Claude session stopped — launching review")
    new_pane = subprocess.run(
        ["cmux", "new-surface", "--type", "terminal", "--workspace", ws],
        capture_output=True,
        text=True,
    )
    if new_pane.returncode != 0:
        print("[vouch hook] new-surface failed:", new_pane.stderr, file=sys.stderr)
        return 1
    m = _SURFACE_REF_RE.search(new_pane.stdout)
    if not m:
        print(f"[vouch hook] could not parse surface ref from: {new_pane.stdout!r}", file=sys.stderr)
        return 0
    new_surface = m.group(0)
    cmd = "vouch"
    if source_surface:
        cmd = f"vouch --source-surface {source_surface}"
    send = subprocess.run(
        ["cmux", "send", "--workspace", ws, "--surface", new_surface, f"{cmd}\n"],
        capture_output=True,
        text=True,
    )
    if send.returncode != 0:
        print(f"[vouch hook] send to {new_surface} failed:", send.stderr, file=sys.stderr)
        return 1
    return 0
