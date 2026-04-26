import argparse
import sys
from typing import List

from vouch import cmux
from vouch.diff_input import resolve_mode, get_unified_diff
from vouch.feedback import build_reject_prompt
from vouch.llm import analyze, semantic_postprocess
from vouch.models import ReviewItem
from vouch.parser import parse_raw_hunks
from vouch.tui import VouchApp


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    parser = argparse.ArgumentParser(prog="vouch", description="closed-loop AI diff reviewer")
    parser.add_argument("rev", nargs="?", help="commit, range (a..b), PR url, or omit for uncommitted")
    parser.add_argument("--pr", dest="pr", help="PR number")
    parser.add_argument("--source-surface", dest="source", help="cmux surface ref of source agent")
    args = parser.parse_args(argv)

    spec_args = []
    if args.pr:
        spec_args = ["--pr", args.pr]
    elif args.rev:
        spec_args = [args.rev]
    spec = resolve_mode(spec_args)

    cmux.set_status("vouch", "loading diff", icon="hourglass")
    diff = get_unified_diff(spec)
    raw = parse_raw_hunks(diff)
    if not raw:
        cmux.clear_status("vouch")
        print("vouch: no changes to review")
        return 0

    cmux.set_status("vouch", f"analyzing {len(raw)} hunks", icon="hammer")
    cmux.set_progress(0.2, "semantic")
    sem = semantic_postprocess(raw)
    cmux.set_progress(0.6, "analyzing")
    analyses = analyze(sem)
    cmux.set_progress(0.9, "ready")

    by_id = {a.id: a for a in analyses}
    items: List[ReviewItem] = []
    for s in sem:
        a = by_id.get(s.id)
        if a is None:
            continue
        items.append(ReviewItem(semantic=s, analysis=a))
    items.sort(key=lambda x: {"high": 0, "med": 1, "low": 2}[x.analysis.risk])

    cmux.set_status("vouch", f"review · {len(items)} items", icon="shield-check")

    source = cmux.discover_source_surface(args.source)

    def on_send(rejects: List[ReviewItem]) -> None:
        prompt = build_reject_prompt(rejects)
        if not prompt:
            return
        channel = cmux.deliver_reject(prompt, source)
        if channel == "cmux":
            cmux.notify("vouch", f"sent {len(rejects)} rejects to source")

    def on_progress(decided: int, total: int) -> None:
        cmux.set_progress(decided / total if total else 0, f"{decided}/{total}")

    VouchApp(items, on_send, on_progress).run()

    cmux.set_progress(1.0, "done")
    cmux.set_status("vouch", "review complete", icon="check")
    return 0
