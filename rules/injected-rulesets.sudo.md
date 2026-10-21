# Injected Rulesets — SudoLang Constraints

You append a fixed ruleset (for example `scripts/lean-change.md`, added by an OpenCode plugin) to the system
prompt of selected agents. It sits in the stable front of every prompt, so it must never become volatile.

## Constraints

- MUST be byte-identical on every turn and every dispatch of the same stage: read it from a file; never build
  it from dates, ids, paths or counters.
- MUST pin its mode per job or stage (environment variable, e.g. `SDD_LEAN_MODE`) and record the mode in the
  dispatch metric and handoff. Switching it mid-job rewrites the cached prefix and makes rounds incomparable.
- MUST scope it by agent: editors only. Never inject into orchestrators, judges or relays that return
  structured output.
- MUST also add it to the compaction context, or the compaction request loses the ruleset and the prefix.
- MUST NOT keep its mode in a global state file shared between sessions.
- MUST NOT claim savings from byte counts or from a vendor benchmark; run a pre-registered A/B (diff lines,
  provider tokens, rounds to PASS, tests, coverage) before turning it on.
- OpenCode jobs are outside the Claude cache hooks: the evidence is the `lean` field in `metrics.jsonl` plus
  `opencode stats`, never the Claude-side cache counters.

## Verify

Diff the injected text between two dispatches of the same stage (must be identical). Check the plugin source
for network, process and global-state use. Re-check the `experimental.*` hooks after an OpenCode upgrade.
