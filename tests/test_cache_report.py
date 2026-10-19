"""Tests for scripts/cache_report.py, run the way Claude Code runs it: JSON on stdin, data dir in env.

    python3 -m unittest discover -s tests -v
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

HOOK = os.path.join(os.path.dirname(__file__), "..", "scripts", "cache_report.py")


def assistant(msg_id, read=0, w5=0, w1=0, fresh=10, out=5, model="claude-sonnet-5-5", sidechain=False):
    return {
        "isSidechain": sidechain,
        "message": {
            "id": msg_id, "role": "assistant", "model": model,
            "usage": {
                "input_tokens": fresh, "cache_read_input_tokens": read, "output_tokens": out,
                "cache_creation_input_tokens": w5 + w1,
                "cache_creation": {"ephemeral_5m_input_tokens": w5, "ephemeral_1h_input_tokens": w1},
            },
        },
    }


class CacheReportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = os.path.join(self.tmp.name, "data")
        self.transcript = os.path.join(self.tmp.name, "sess1.jsonl")

    def write_transcript(self, records):
        with open(self.transcript, "w") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")

    def run_hook(self, env=None, session="sess1"):
        e = dict(os.environ, CLAUDE_PLUGIN_DATA=self.data, **(env or {}))
        return subprocess.run(
            [sys.executable, "-I", HOOK], input=json.dumps({"transcript_path": self.transcript, "session_id": session}),
            capture_output=True, text=True, env=e, timeout=30,
        )

    def rows(self, name="cache-usage.jsonl"):
        path = os.path.join(self.data, name)
        if not os.path.exists(path):
            return []
        with open(path) as fh:
            return [json.loads(l) for l in fh]

    def test_main_row_has_ieq_and_ttl_and_is_deduplicated(self):
        self.write_transcript([assistant("m1", read=1000, w1=200, fresh=10, out=4)])
        self.run_hook()
        self.run_hook()  # Stop fires every turn; the same response must not be recorded twice
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        # sonnet-5-5 reads cost 0.05x: 10*1 + 200*2 + 1000*0.05 = 460 (output is not part of the main-row ieq)
        self.assertEqual(rows[0]["ieq"], 460)
        self.assertEqual(rows[0]["ttl_s"], 3600)
        self.assertIsNone(rows[0]["gap_s"])

    def test_read_weight_depends_on_model(self):
        self.write_transcript([assistant("m1", read=1000, w1=0, fresh=0, model="claude-haiku-4-5")])
        self.run_hook()
        self.assertEqual(self.rows()[0]["ieq"], 100)  # general rule 0.1x for models without a listed exception

    def test_ttl_defaults_to_5m_without_1h_writes(self):
        self.write_transcript([assistant("m1", read=100, w5=50)])
        self.run_hook()
        self.assertEqual(self.rows()[0]["ttl_s"], 300)

    def test_idle_gap_beyond_ttl_is_named_in_the_warning(self):
        os.makedirs(self.data)
        old = {"ts": int(time.time()) - 4000, "session": "sess1", "msg": "m0", "write_1h": 5, "write_5m": 0}
        with open(os.path.join(self.data, "cache-usage.jsonl"), "w") as fh:
            fh.write(json.dumps(old) + "\n")
        self.write_transcript([assistant("m1", read=100, w1=50_000)])
        out = self.run_hook().stdout
        self.assertIn("idle", json.loads(out)["systemMessage"])
        self.assertIn("exceeded the 60 min TTL", out)

    def test_broken_prefix_without_idle_gap_blames_prefix_changes(self):
        self.write_transcript([assistant("m1", read=100, w1=50_000)])
        out = self.run_hook().stdout
        self.assertIn("model/MCP/CLAUDE.md change", out)
        self.assertNotIn("idle", out)

    def test_threshold_is_configurable_by_env(self):
        self.write_transcript([assistant("m1", read=100, w1=50_000)])
        out = self.run_hook(env={"SUDOLANG_CACHE_BREAK_MIN_WRITE": "100000"}).stdout
        self.assertEqual(out.strip(), "")

    def test_subagent_snapshot_with_type_and_sdd_jobs_and_mtime_skip(self):
        self.write_transcript([assistant("m1", read=100, w1=10)])
        sub = os.path.join(self.tmp.name, "sess1", "subagents")
        os.makedirs(sub)
        agent = os.path.join(sub, "agent-abc.jsonl")
        with open(agent, "w") as fh:
            for rec in (assistant("a1", read=500, w1=100, sidechain=True),
                        assistant("a1", read=500, w1=100, sidechain=True),  # streamed repeat of the same response
                        assistant("a2", read=700, w5=50, fresh=20, out=7, sidechain=True),
                        {"message": {"role": "user", "content": '{"job":"sdd-1792416624601"}'}}):
                fh.write(json.dumps(rec) + "\n")
        with open(os.path.join(sub, "agent-abc.meta.json"), "w") as fh:
            json.dump({"agentType": "sdd-opencode-runner"}, fh)
        self.run_hook()
        rows = self.rows("cache-usage-subagents.jsonl")
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual((r["agent_id"], r["agent_type"], r["calls"]), ("abc", "sdd-opencode-runner", 2))
        self.assertEqual((r["read"], r["write_1h"], r["write_5m"]), (1200, 100, 50))
        self.assertEqual(r["jobs"], ["sdd-1792416624601"])
        self.run_hook()  # file unchanged -> no new snapshot
        self.assertEqual(len(self.rows("cache-usage-subagents.jsonl")), 1)
        os.utime(agent, (time.time() + 10, time.time() + 10))  # file changed -> new snapshot
        self.run_hook()
        self.assertEqual(len(self.rows("cache-usage-subagents.jsonl")), 2)


    def test_jobs_are_only_attributed_to_agents_that_handle_sdd_jobs(self):
        self.write_transcript([assistant("m1", read=100, w1=10)])
        sub = os.path.join(self.tmp.name, "sess1", "subagents")
        os.makedirs(sub)
        with open(os.path.join(sub, "agent-xyz.jsonl"), "w") as fh:
            fh.write(json.dumps(assistant("a1", read=5, sidechain=True)) + "\n")
            fh.write(json.dumps({"message": {"role": "user", "content": "log mentions sdd-1792416624601"}}) + "\n")
        with open(os.path.join(sub, "agent-xyz.meta.json"), "w") as fh:
            json.dump({"agentType": "Explore"}, fh)
        self.run_hook()
        self.assertEqual(self.rows("cache-usage-subagents.jsonl")[0]["jobs"], [])

    def test_hook_never_fails_on_garbage(self):
        e = dict(os.environ, CLAUDE_PLUGIN_DATA=self.data)
        for stdin in ("", "not json", json.dumps({"transcript_path": "/nonexistent"})):
            p = subprocess.run([sys.executable, "-I", HOOK], input=stdin, capture_output=True, text=True, env=e)
            self.assertEqual(p.returncode, 0)


if __name__ == "__main__":
    unittest.main()
