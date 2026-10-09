#!/usr/bin/env bash
# Compare the plugin source (this repo) with the copy Claude Code actually loads.
# Default: show the diff and exit 1 if they differ. --apply: copy source over the installed copy.
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${SUDOLANG_INSTALLED:-$HOME/.claude/plugins/cache/local/sudolang-cache-engine/1.0.0}"
PATHS=(agents commands hooks rules scripts skills .claude-plugin README.md)

[ -d "$DEST" ] || { echo "installed copy not found: $DEST" >&2; exit 2; }

if [ "${1:-}" = "--apply" ]; then
  for p in "${PATHS[@]}"; do
    [ -e "$SRC/$p" ] || continue
    rm -rf "${DEST:?}/$p"
    cp -r "$SRC/$p" "$DEST/$p"
  done
  rm -f "$DEST/settings.json"  # removed from source: Claude Code ignores plugin settings except agent/subagentStatusLine
  chmod +x "$DEST/scripts/"*.sh "$DEST/scripts/"*.py 2>/dev/null || true
  echo "synced $SRC -> $DEST"
  exit 0
fi

rc=0
for p in "${PATHS[@]}"; do
  [ -e "$SRC/$p" ] || continue
  diff -r "$SRC/$p" "$DEST/$p" || rc=1
done
[ -e "$DEST/settings.json" ] && { echo "stale settings.json in installed copy"; rc=1; }
[ $rc -eq 0 ] && echo "in sync" || echo "OUT OF SYNC: run $0 --apply"
exit $rc
