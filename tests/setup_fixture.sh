#!/usr/bin/env bash
# Clone vouch-fixtures and apply pending.diff so the fixture repo is ready
# for vouch's 4 input modes.
#
# Usage:
#   tests/setup_fixture.sh                # default /tmp/vouch-fixtures
#   tests/setup_fixture.sh /custom/path
set -euo pipefail
DIR="${1:-/tmp/vouch-fixtures}"
URL="https://github.com/YounggLee/vouch-fixtures"

if [ ! -d "$DIR" ]; then
  git clone "$URL" "$DIR"
fi
cd "$DIR"
git fetch -q origin
git checkout -q main
git reset -q --hard origin/main
git clean -qfd
git apply pending.diff
echo "fixture ready at $DIR"
echo "  - main + pending.diff applied (uncommitted mode)"
echo "  - feature/auth has 3 commits (commit/range mode)"
echo "  - PR #1 open (--pr mode)"
