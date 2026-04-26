# vhs tape — deterministic 30s demo
# Run: vhs scripts/demo.tape
# Output: docs/demo.gif
#
# Uses VOUCH_CACHE_ONLY=1 so no network/API key is required.

Output docs/demo.gif

Set Shell "bash"
Set FontSize 14
Set Width 1200
Set Height 720
Set Theme "Catppuccin Mocha"
Set TypingSpeed 40ms
Set PlaybackSpeed 1.0

# Land in the fixture repo with the demo env preloaded
Hide
Type "cd fixtures/todo_app"
Enter
Type "export VOUCH_CACHE_ONLY=1 VOUCH_CACHE_DIR=$(pwd)/../responses"
Enter
Type "clear"
Enter
Show

# Show the diff that vouch is about to review
Type "git diff --stat HEAD"
Sleep 500ms
Enter
Sleep 2s

# Launch vouch
Type "vouch"
Sleep 500ms
Enter
Sleep 4s

# Walk through a couple of cards
Type "j"
Sleep 1500ms
Type "j"
Sleep 1500ms

# Reject one with a reason
Type "r"
Sleep 800ms
Type "race condition: needs lock around counter"
Sleep 600ms
Enter
Sleep 1500ms

# Accept-all-low
Type "A"
Sleep 1500ms

# Send rejects back (fallback to clipboard/stdout outside cmux)
Type "s"
Sleep 2500ms

# Quit
Type "q"
Sleep 1500ms
