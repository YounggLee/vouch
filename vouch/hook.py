import json
import subprocess
import sys

from vouch import cmux


def stop(args=None) -> int:
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
    return 0
