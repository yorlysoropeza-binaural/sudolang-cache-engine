# Context Hygiene — SudoLang Constraints

You keep the cached prefix stable and the live context small, because the largest costs are a large
fixed prefix and prefix breaks, not output tokens.

## Constraints

- MUST NOT switch model or effort mid-session unless the work genuinely needs it; each switch rewrites
  the cache for the whole conversation.
- MUST NOT connect or remove MCP servers mid-session when their tools are not deferred; it invalidates
  tools, system and messages.
- Edits to CLAUDE.md/AGENTS.md take effect on reload and cost a cache write; batch them.
- Parallel worktrees do not share a cache: do not spawn one per small task.
- Large fixed context belongs in skills (loaded on demand) or nested CLAUDE.md, not in the root
  CLAUDE.md. Target a root CLAUDE.md under 200 lines.
- Keep the always-listed skill set small: each description is paid every turn. Mark manual-only skills
  `disable-model-invocation: true`, scope version/module skills with `paths:`, and use `context: fork`
  for skills with verbose output. Use `/skill-doctor` to find never-invoked skills.
- Compact or `/clear` between tasks, not after a long idle: past the TTL a compact re-reads the whole
  history uncached. Prefer `/rewind` over compact when abandoning a path.
- Filter tool output before it reaches context (limit `Read` ranges, `bashOutputMaxChars`, a
  `PreToolUse` hook that trims test logs, `MAX_MCP_OUTPUT_TOKENS` for verbose MCP servers).
- Do not run `/loop` for periodic reports inside a long session; each firing resends the context. Use a
  fresh headless run.

## Measure

`cache-usage.jsonl` (Stop hook) gives per-response `read`/`write_5m`/`write_1h`/`ctx`. A response with a
large write and low read marks a prefix break; find its cause with `/usage`. Baseline alert: initial
context above 60k tokens.
