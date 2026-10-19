# sudolang-cache-engine

Claude Code plugin: **prompt-authoring guidance** for cache-friendly agent system prompts and
`Task()`/dispatch handoffs, written in SudoLang. It does not implement or measure real prompt
caching — it never reads live cache telemetry (`cache_creation_input_tokens`/
`cache_read_input_tokens`) and every agent/command here explicitly refuses to fabricate a
hit-rate or token-savings number. Treat it as a style guide + two audit tools, not a caching
mechanism.

## What's in here

- `rules/*.sudo.md` — the actual guidance, one file per concern:
  - `cache-architecture.sudo.md` — Frente Estable / Fondo Volátil (stable-front/volatile-tail)
    prompt layout.
  - `temporal-layering.sudo.md` — what must never appear in a stable block (dates, UUIDs, job
    IDs) vs. what belongs in the dynamic tail.
  - `stigmergic-coordination.sudo.md` — coordinate agents via shared artifacts referenced by
    path, never by pasting content.
  - `progressive-disclosure.sudo.md` — keep agent system prompts small, push deep reference
    material into a Skill loaded on demand. Largely documents Claude Code's native
    Skills-on-demand mechanism rather than adding new capability — see AGENTS.md rule 155 for
    where this overlaps.
  - `fork-agent-patterns.sudo.md` — when to use `Agent(subagent_type:"fork")` vs. a fresh named
    subagent. Also documents native Claude Code behavior, not something this plugin implements.
  - `ttl-management.sudo.md` — real Anthropic prompt-cache TTL mechanics (5min default / 1h
    extended, refreshed on every hit) and the append-only convention this repo's SDD pipeline
    follows because of it.
- `skills/cache-engine/SKILL.md` — the umbrella skill tying the rules together.
- `agents/cache-analyzer.md` / `agents/cache-optimizer.md` — a read-only scanner and a
  rewriter for cache-unfriendly prompt templates.
- `commands/cache-audit.md` / `cache-optimize.md` / `cache-test.md` — on-demand slash commands
  wrapping the two agents plus a stable-block drift diff between two template variants.

## Scope, explicitly

- Telemetry is minimal: a `Stop` hook (`hooks/hooks.json` → `scripts/cache_report.py`) appends
  real per-response cache usage to `${CLAUDE_PLUGIN_DATA}/cache-usage.jsonl` and warns on a
  probable prefix break. Everything else (`/cache-audit`, `/cache-test`) is static analysis.
- No enforcement: no CI check or pre-commit wiring — the commands only run when invoked by hand.
- `rules/` is a reference directory, not a Claude Code plugin component: it is not auto-injected.
  The umbrella skill points to each rule.
- No plugin `settings.json`: Claude Code only honors `agent` and `subagentStatusLine` there.

## Two copies exist — keep them in sync manually

The source of truth for editing is this git submodule
(`docker-multi/sudolang-cache-engine/`). Claude Code actually loads plugin content from an
**installed copy** at `~/.claude/plugins/cache/local/sudolang-cache-engine/1.0.0/` (a real copy,
not a symlink). Editing only the submodule has no runtime effect until you copy the changed
paths over the installed copy. Run `scripts/sync-plugin.sh` (diff by default, `--apply` to copy);
it covers `agents/`, `commands/`, `hooks/`, `rules/`, `scripts/`, `skills/`, `README.md` and the whole
`.claude-plugin/` directory (not `tests/`: they only run from the source repo). See `docker-multi/CLAUDE.md`'s "SudoLang
Cache Engine plugin" section for the full detail and the incident that surfaced this.

## Where the actionable guidance is actually used

See `docker-multi/AGENTS.md` rule 155 and the `sdd-*` skills under
`docker-multi/src/.opencode/skills/` for the concrete `Context {}` schemas this plugin's
principles inform (`sdd-builder`, `sdd-qc`, `sdd-lead`'s OpenCode dispatch,
`sdd-metrics-reporter`).
