#!/usr/bin/env python3
"""Stop hook: record real prompt-cache usage of the main thread and of its subagents.

Reads the session transcript (path arrives as JSON on stdin).
- Main thread: takes the latest assistant response's `usage`, appends one JSON line to
  `${CLAUDE_PLUGIN_DATA}/cache-usage.jsonl` and, only when the cache prefix looks broken (large cache
  write, little cache read), prints a `systemMessage` warning.
- Subagents: Claude Code keeps each one in `<session>/subagents/agent-<id>.jsonl` (+ `.meta.json`), not in
  the main transcript. Their totals go to `cache-usage-subagents.jsonl`, one snapshot row per agent whenever
  its totals change (take the last row per `agent_id`). Rows carry the agent type and any SDD job ids
  (`sdd-<epoch ms>`) seen in the agent's transcript, so they can be joined with `src/.sdd/logs/metrics.jsonl`.

Never blocks and never fails the turn: any error exits 0 silently. Read-only over transcripts; the main
transcript is read only from its tail and unchanged subagent files are skipped by mtime, so the cost per
turn stays small.

Thresholds are overridable with env vars (defaults below):
  SUDOLANG_CACHE_TAIL_BYTES, SUDOLANG_CACHE_BREAK_MIN_WRITE, SUDOLANG_CACHE_BREAK_MAX_READ_RATIO,
  SUDOLANG_CACHE_CTX_WARN
"""
import glob
import json
import os
import re
import sys
import time

# Price of each bucket relative to base input (input-equivalent tokens, "ieq"). Same weights as
# scripts/sdd_token_usage.py in docker-multi, except cache reads, which depend on the model (read_weight).
# Trend metric only, not dollars; check current prices before quoting costs.
WEIGHTS = {"in": 1.0, "cw5m": 1.25, "cw1h": 2.0, "cr": 0.1, "out": 5.0}
TTL_5M = 300
TTL_1H = 3600
JOB_RE = re.compile(r"sdd-\d{10,}")
# Only these agents dispatch or judge SDD jobs. Any other agent (e.g. Explore) merely mentions job ids it
# read in logs, which would create false job<->cost correlations.
JOB_AGENT_TYPES = {"sdd-opencode-runner", "sdd-judge", "sdd-lead"}
MAX_SUBAGENT_BYTES = 3_000_000


def _env_num(name, default, cast):
    try:
        return cast(os.environ[name])
    except (KeyError, ValueError):
        return default


TAIL_BYTES = _env_num("SUDOLANG_CACHE_TAIL_BYTES", 600_000, int)
BREAK_MIN_WRITE = _env_num("SUDOLANG_CACHE_BREAK_MIN_WRITE", 30_000, int)  # tokens written in one response
BREAK_MAX_READ_RATIO = _env_num("SUDOLANG_CACHE_BREAK_MAX_READ_RATIO", 0.5, float)  # read / (read + write)
CTX_WARN = _env_num("SUDOLANG_CACHE_CTX_WARN", 60_000, int)  # same baseline alert as sdd_token_usage.py


def read_weight(model):
    """Cache-read price relative to base input. 0.1 is the general rule; the docs list cheaper reads for the
    newest models (checked against the prompt-caching page on 2026-10-19). Unknown model -> general rule."""
    m = model or ""
    if "fable-5-1" in m or "mythos-5-1" in m:
        return 0.025
    if "opus-5-5" in m or "sonnet-5-5" in m:
        return 0.05
    return WEIGHTS["cr"]


def ieq(read, w5, w1, fresh, out=0, model=None):
    return int(fresh * WEIGHTS["in"] + w5 * WEIGHTS["cw5m"] + w1 * WEIGHTS["cw1h"]
               + read * read_weight(model) + out * WEIGHTS["out"])


def split_usage(usage):
    cc = usage.get("cache_creation") or {}
    w1 = cc.get("ephemeral_1h_input_tokens", 0)
    w5 = cc.get("ephemeral_5m_input_tokens", 0)
    write = usage.get("cache_creation_input_tokens", w1 + w5)
    return {
        "read": usage.get("cache_read_input_tokens", 0),
        "w5": w5,
        "w1": w1,
        "write": write,
        "fresh": usage.get("input_tokens", 0),
        "out": usage.get("output_tokens", 0),
    }


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


def subagent_totals(path):
    """Aggregate one subagent transcript. Responses repeat across streamed records: keep the last per id."""
    by_id = {}
    models = set()
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        text = fh.read(MAX_SUBAGENT_BYTES)
    for line in text.splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        msg = rec.get("message") or {}
        if msg.get("role") == "assistant" and msg.get("usage"):
            u = split_usage(msg["usage"])
            u["model"] = msg.get("model")
            by_id[msg.get("id") or f"anon{len(by_id)}"] = u
            if msg.get("model"):
                models.add(msg["model"])
    tot = {"calls": len(by_id), "read": 0, "w5": 0, "w1": 0, "fresh": 0, "out": 0, "ctx_max": 0, "ieq": 0}
    for u in by_id.values():
        for k in ("read", "w5", "w1", "fresh", "out"):
            tot[k] += u[k]
        tot["ieq"] += ieq(u["read"], u["w5"], u["w1"], u["fresh"], u["out"], u["model"])
        tot["ctx_max"] = max(tot["ctx_max"], u["fresh"] + u["read"] + u["write"])
    tot["models"] = sorted(models)
    tot["jobs"] = sorted(set(JOB_RE.findall(text)))[:5]
    return tot


def record_subagents(transcript_path, data_dir):
    sub_dir = os.path.splitext(transcript_path)[0] + "/subagents"
    files = glob.glob(os.path.join(sub_dir, "agent-*.jsonl"))
    if not files:
        return
    state_path = os.path.join(data_dir, "subagents-state.json")
    try:
        with open(state_path, encoding="utf-8") as fh:
            state = json.load(fh)
    except (OSError, ValueError):
        state = {}
    rows = []
    for path in files:
        agent_id = os.path.basename(path)[len("agent-"):-len(".jsonl")]
        mtime = int(os.path.getmtime(path))
        if state.get(agent_id) == mtime:
            continue  # unchanged since the last snapshot
        tot = subagent_totals(path)
        state[agent_id] = mtime
        if not tot["calls"]:
            continue
        agent_type = ""
        try:
            with open(path[:-len(".jsonl")] + ".meta.json", encoding="utf-8") as fh:
                agent_type = json.load(fh).get("agentType", "")
        except (OSError, ValueError):
            pass
        total_in = tot["fresh"] + tot["read"] + tot["w5"] + tot["w1"]
        rows.append({
            "ts": int(time.time()),
            "session": os.path.basename(os.path.splitext(transcript_path)[0]),
            "agent_id": agent_id,
            "agent_type": agent_type,
            "models": tot["models"],
            "calls": tot["calls"],
            "read": tot["read"],
            "write_5m": tot["w5"],
            "write_1h": tot["w1"],
            "fresh": tot["fresh"],
            "out": tot["out"],
            "ctx_max": tot["ctx_max"],
            "hit": round(tot["read"] / total_in, 3) if total_in else 0.0,
            "ieq": tot["ieq"],
            "jobs": tot["jobs"] if agent_type in JOB_AGENT_TYPES else [],
        })
    if rows:
        with open(os.path.join(data_dir, "cache-usage-subagents.jsonl"), "a", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump(state, fh)


def previous_row(out, session):
    """Last recorded main-thread row of this session (from the file tail), for idle-gap detection."""
    try:
        with open(out, "rb") as fh:
            fh.seek(max(0, os.path.getsize(out) - 65536))
            lines = fh.read().decode("utf-8", errors="ignore").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("session") == session:
            return row
    return None


def main():
    try:
        payload = json.load(sys.stdin)
        data_dir = os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.expanduser(
            "~/.claude/plugins/data/sudolang-cache-engine"
        )
        os.makedirs(data_dir, exist_ok=True)
        try:
            record_subagents(payload["transcript_path"], data_dir)
        except Exception:
            pass  # subagent accounting must not stop the main-thread record
        found = last_usage(payload["transcript_path"])
        if not found:
            return
        msg_id, model, usage = found
        u = split_usage(usage)
        read, write, fresh = u["read"], u["write"], u["fresh"]
        ctx = fresh + read + write
        now = int(time.time())
        out = os.path.join(data_dir, "cache-usage.jsonl")
        # Append once per response id: Stop fires every turn but the last response may repeat.
        try:
            with open(out, "rb") as fh:
                fh.seek(max(0, os.path.getsize(out) - 4096))
                if msg_id and msg_id.encode() in fh.read():
                    return
        except OSError:
            pass
        prev = previous_row(out, payload.get("session_id"))
        gap = now - prev["ts"] if prev else None
        # The TTL is a property of the breakpoint, not of the plan: infer it from what this session writes.
        ttl = TTL_1H if (u["w1"] or (prev and prev.get("write_1h"))) else TTL_5M
        row = {
            "ts": now,
            "session": payload.get("session_id"),
            "msg": msg_id,
            "model": model,
            "ctx": ctx,
            "read": read,
            "write_5m": u["w5"],
            "write_1h": u["w1"],
            "fresh": fresh,
            "ieq": ieq(read, u["w5"], u["w1"], fresh, model=model),
            "gap_s": gap,
            "ttl_s": ttl,
        }
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        notes = []
        ratio = read / (read + write) if (read + write) else 1.0
        if write >= BREAK_MIN_WRITE and ratio < BREAK_MAX_READ_RATIO:
            if gap is not None and gap > ttl:
                cause = f"idle {gap // 60} min exceeded the {ttl // 60} min TTL"
            else:
                cause = "model/MCP/CLAUDE.md change, or a TTL shorter than assumed"
            notes.append(f"cache prefix likely broken: wrote {write:,} tokens, read {read:,} ({cause})")
        if ctx > CTX_WARN and read == 0 and write == 0:
            notes.append(f"context {ctx:,} tokens is uncached")
        if notes:
            print(json.dumps({"systemMessage": "[cache-engine] " + "; ".join(notes)}))
    except Exception:
        pass  # a metrics hook must never disturb the session


if __name__ == "__main__":
    main()
