#!/usr/bin/env python3
"""Stop hook: record real prompt-cache usage of the last main-thread response.

Reads the session transcript (path arrives as JSON on stdin), takes the latest assistant
response's `usage`, appends one JSON line to `${CLAUDE_PLUGIN_DATA}/cache-usage.jsonl` and, only
when the cache prefix looks broken (large cache write, little cache read), prints a
`systemMessage` warning. Never blocks and never fails the turn: any error exits 0 silently.

Read-only over the transcript; reads only its tail so the cost per turn stays constant.
"""
import json
import os
import sys
import time

TAIL_BYTES = 600_000
BREAK_MIN_WRITE = 30_000  # tokens written to cache in one response
BREAK_MAX_READ_RATIO = 0.5  # cache_read / (cache_read + cache_creation)
CTX_WARN = 60_000  # same baseline alert as sdd_token_usage.py


def last_usage(path):
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        fh.seek(max(0, size - TAIL_BYTES))
        raw = fh.read().decode("utf-8", errors="ignore")
    found = None
    for line in raw.splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue  # first line of the tail may be cut mid-record
        msg = rec.get("message") or {}
        if rec.get("isSidechain") or msg.get("role") != "assistant":
            continue
        if msg.get("usage"):
            found = (msg.get("id"), msg.get("model"), msg["usage"])
    return found


def main():
    try:
        payload = json.load(sys.stdin)
        found = last_usage(payload["transcript_path"])
        if not found:
            return
        msg_id, model, usage = found
        cc = usage.get("cache_creation") or {}
        write_1h = cc.get("ephemeral_1h_input_tokens", 0)
        write_5m = cc.get("ephemeral_5m_input_tokens", 0)
        write = usage.get("cache_creation_input_tokens", write_1h + write_5m)
        read = usage.get("cache_read_input_tokens", 0)
        fresh = usage.get("input_tokens", 0)
        ctx = fresh + read + write
        row = {
            "ts": int(time.time()),
            "session": payload.get("session_id"),
            "msg": msg_id,
            "model": model,
            "ctx": ctx,
            "read": read,
            "write_5m": write_5m,
            "write_1h": write_1h,
            "fresh": fresh,
        }
        data_dir = os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.expanduser(
            "~/.claude/plugins/data/sudolang-cache-engine"
        )
        os.makedirs(data_dir, exist_ok=True)
        out = os.path.join(data_dir, "cache-usage.jsonl")
        # Append once per response id: Stop fires every turn but the last response may repeat.
        try:
            with open(out, "rb") as fh:
                fh.seek(max(0, os.path.getsize(out) - 4096))
                if msg_id and msg_id.encode() in fh.read():
                    return
        except OSError:
            pass
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        notes = []
        ratio = read / (read + write) if (read + write) else 1.0
        if write >= BREAK_MIN_WRITE and ratio < BREAK_MAX_READ_RATIO:
            notes.append(
                f"cache prefix likely broken: wrote {write:,} tokens, read {read:,} "
                "(model/MCP/CLAUDE.md change, or idle past the TTL)"
            )
        if ctx > CTX_WARN and read == 0 and write == 0:
            notes.append(f"context {ctx:,} tokens is uncached")
        if notes:
            print(json.dumps({"systemMessage": "[cache-engine] " + "; ".join(notes)}))
    except Exception:
        pass  # a metrics hook must never disturb the session


if __name__ == "__main__":
    main()
