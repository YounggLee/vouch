"""Curated `vouch help` output. Distinct from argparse's terse `--help`."""
import sys


_HELP = """\
vouch — closed-loop AI diff reviewer

USAGE
  vouch                       review uncommitted changes (default)
  vouch <commit>              review a single commit (e.g. HEAD, abc123, HEAD~3)
  vouch <a>..<b>              review a commit range (e.g. main..HEAD)
  vouch --pr <number>         review a GitHub PR
  vouch <pr-url>              same, with full URL
  vouch help                  show this guide
  vouch --help                terse argparse usage

INPUT MODES
  uncommitted   git diff HEAD                  working-tree changes
  commit        git show --format= <ref>       a single commit
  range         git diff <a>..<b>              all commits between two refs
  pr            gh pr diff <number>            a GitHub PR (needs gh auth)

KEY BINDINGS (TUI)
  j / k           move down / up in the queue
  a               accept the highlighted item
  A               accept all 🟢 low-risk items at once
  r               reject (modal prompts for a one-line reason)
  s               quit and send rejects to the source agent
  q               quit
  Enter           focus the diff pane (then ↑/↓ PgUp/PgDn to scroll)
  Esc             focus back to the queue

REJECT DELIVERY (in priority order)
  1. gh pr comment    when running in --pr mode
  2. cmux send        when --source-surface / VOUCH_SOURCE_SURFACE / CMUX_SURFACE_ID is set
  3. clipboard        pbcopy / wl-copy / xclip auto-detected
  4. stdout           if all of the above fail

ENVIRONMENT
  GEMINI_API_KEY        Gemini API key. Loaded from .env if present.
  VOUCH_MODEL           Gemini model id (default: gemini-3-flash-preview).
  VOUCH_CACHE_DIR       Response cache directory (default: fixtures/responses).
  VOUCH_CACHE_ONLY=1    Cache-only mode — never call Gemini. Errors on cache miss.
  VOUCH_SOURCE_SURFACE  Default reject-target cmux surface ref.

EXAMPLES
  # Review what you're about to commit
  vouch

  # Review the last 3 commits before pushing
  vouch HEAD~3..HEAD

  # Review a teammate's PR before approving
  vouch --pr 42

  # Demo with deterministic cached responses
  ./scripts/demo.sh

TROUBLESHOOTING
  "command not found: vouch"
      Activate the venv:  source .venv/bin/activate
      Or call directly:   /path/to/.venv/bin/vouch

  "vouch: no changes to review"
      Working tree is clean. Stage some changes, or pass a ref/range/PR.

  "VOUCH_CACHE_ONLY=1 but no cached response"
      Demo cache is missing. Run from the project root:
        git checkout HEAD -- fixtures/responses/

  "API key was reported as leaked"
      Rotate GEMINI_API_KEY in .env. Google auto-disables exposed keys.

LINKS
  Repo:     https://github.com/YounggLee/vouch
  Fixtures: https://github.com/YounggLee/vouch-fixtures
"""


def show() -> int:
    sys.stdout.write(_HELP)
    return 0
