"""Capture VouchApp screenshots in headless mode, then assemble into a GIF."""
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Must run vouch from the fixture repo
FIXTURE_DIR = ROOT / "fixtures" / "todo_app"
os.chdir(FIXTURE_DIR)

os.environ["VOUCH_CACHE_ONLY"] = "1"
os.environ["VOUCH_CACHE_DIR"] = str(ROOT / "fixtures" / "responses")

from vouch.diff_input import resolve_mode, get_unified_diff
from vouch.llm import analyze, semantic_postprocess
from vouch.models import ReviewItem
from vouch.parser import parse_raw_hunks
from vouch.tui import VouchApp


def build_items():
    spec = resolve_mode([])
    diff = get_unified_diff(spec)
    raw = parse_raw_hunks(diff)
    sem = semantic_postprocess(raw)
    analyses = analyze(sem)
    by_id = {a.id: a for a in analyses}
    items = []
    for s in sem:
        a = by_id.get(s.id)
        if a is None:
            continue
        items.append(ReviewItem(semantic=s, analysis=a))
    items.sort(key=lambda x: {"high": 0, "med": 1, "low": 2}[x.analysis.risk])
    return items


async def capture():
    items = build_items()
    print(f"Built {len(items)} review items")

    app = VouchApp(items, on_send=lambda _: None, on_progress=lambda a, b: None)

    frames_dir = Path(tempfile.mkdtemp(prefix="vouch-demo-"))
    frame_idx = 0

    async with app.run_test(size=(120, 35)) as pilot:
        await pilot.pause()

        # Frame 0: initial view
        svg = app.export_screenshot()
        (frames_dir / f"frame_{frame_idx:03d}.svg").write_text(svg)
        print(f"  frame {frame_idx}: initial view")
        frame_idx += 1

        # Frame 1: move down
        await pilot.press("j")
        await pilot.pause()
        svg = app.export_screenshot()
        (frames_dir / f"frame_{frame_idx:03d}.svg").write_text(svg)
        print(f"  frame {frame_idx}: cursor down")
        frame_idx += 1

        # Frame 2: enter detail
        await pilot.press("enter")
        await pilot.pause()
        svg = app.export_screenshot()
        (frames_dir / f"frame_{frame_idx:03d}.svg").write_text(svg)
        print(f"  frame {frame_idx}: detail view")
        frame_idx += 1

        # Frame 3: back to queue
        await pilot.press("escape")
        await pilot.pause()
        svg = app.export_screenshot()
        (frames_dir / f"frame_{frame_idx:03d}.svg").write_text(svg)
        print(f"  frame {frame_idx}: back to queue")
        frame_idx += 1

        # Frame 4: accept item
        await pilot.press("a")
        await pilot.pause()
        svg = app.export_screenshot()
        (frames_dir / f"frame_{frame_idx:03d}.svg").write_text(svg)
        print(f"  frame {frame_idx}: accepted")
        frame_idx += 1

    print(f"\nCaptured {frame_idx} SVG frames in {frames_dir}")

    # Convert SVG -> PNG via qlmanage (macOS) or rsvg-convert
    png_paths = []
    has_rsvg = subprocess.run(["which", "rsvg-convert"], capture_output=True).returncode == 0

    for i in range(frame_idx):
        svg_path = frames_dir / f"frame_{i:03d}.svg"
        if has_rsvg:
            png_path = frames_dir / f"frame_{i:03d}.png"
            subprocess.run(
                ["rsvg-convert", "-w", "2400", str(svg_path), "-o", str(png_path)],
                check=True, capture_output=True,
            )
        else:
            subprocess.run(
                ["qlmanage", "-t", "-s", "2400", "-o", str(frames_dir), str(svg_path)],
                check=True, capture_output=True,
            )
            png_path = frames_dir / f"frame_{i:03d}.svg.png"
        png_paths.append(str(png_path))

    print(f"Converted {len(png_paths)} PNGs")

    # Assemble GIF with ffmpeg
    gif_path = ROOT / "demo.gif"
    durations = [2.5, 2, 3, 2, 2.5]
    concat_file = frames_dir / "concat.txt"
    with open(concat_file, "w") as f:
        for png, dur in zip(png_paths, durations):
            f.write(f"file '{png}'\nduration {dur}\n")
        f.write(f"file '{png_paths[-1]}'\n")

    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-vf", "fps=1,scale=1200:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer",
            str(gif_path),
        ],
        check=True, capture_output=True,
    )

    print(f"\nGenerated: {gif_path} ({gif_path.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    asyncio.run(capture())
