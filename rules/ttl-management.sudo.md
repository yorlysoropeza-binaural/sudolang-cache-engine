# TTL Management — SudoLang Constraints

You document real Anthropic prompt-cache mechanics and the append-only convention for state updates
that keeps a long-running agent conversation cache-friendly. Incident narratives and dated decisions
live in `skills/cache-engine-history` (loaded on demand), not here.

## Request layout and prefix invalidation

A request is cached as one prefix in this order: **tools → system → messages**. A byte that changes at
one level invalidates that level and everything after it. Consequences:

- Changing the tool set (adding/removing an MCP server whose tools are not deferred) invalidates system and messages.
- Changing system content (CLAUDE.md edit applied on reload, model switch, effort switch) invalidates messages.
- Appending a message invalidates nothing before it.
- The cache is keyed per working directory: parallel worktrees do not share a prefix.

## TTL and cost (verify prices against the current pricing page before quoting numbers)

| Breakpoint type | TTL | Write cost vs base input | Read cost vs base input |
|-----------------|-----|--------------------------|--------------------------|
| Default ephemeral | 5 min | ≈1.25x | ≈0.1x |
| Extended (`ENABLE_PROMPT_CACHING_1H`, `promptCacheTtl`) | 1 h | ≈2x | ≈0.1x |

- TTL is a property of the breakpoint, not of a subscription tier.
- Breakpoints of both TTLs can coexist in one request; the 1 h breakpoints must come before the 5 min ones.
- Subagents default to 5 min (`subagentPromptCacheTtl`); a subagent that waits on a long job can opt in
  to 1 h in its own frontmatter (`experimental: { cacheTtl: 1h }`).
- 1 h pays off only when the same prefix is reused after more than 5 min idle. Otherwise the 2x write is
  waste. Decide from measured data (`cache-usage.jsonl`, written by the Stop hook), not by assumption.
- Minimum cacheable prefix depends on the model; below it a breakpoint has no effect. Check the current
  docs for the model in use instead of assuming one number.

## TTL behavior — no decay, refresh on hit

A cache entry's TTL is fixed at write time and refreshed to its full value on every hit that reads it.
It never shrinks with hit count. A hit refreshes only the prefix actually read, not later breakpoints.
If the window elapses with no hit, the next request pays the write cost again
(`usage.cache_creation_input_tokens` nonzero, `cache_read_input_tokens` zero for that block).

## Append-only state updates (never break the prefix)

Once a stable block (tool defs, system prompt, an early turn) has been cached, never rewrite it to inject
a status update — that invalidates everything downstream for no gain. Instead:

- Append new information as a new message/turn at the end (for headless agent-to-agent handoffs: a new
  file/job, never an edit of a previous one).
- Each OpenCode dispatch gets a new `job_id` under `src/.sdd/logs/jobs/<job_id>/`; a retry is a new
  dispatch with a fresh `Context {}` block carrying the retry reason, never an edit of the old
  `dispatch.handoff`. `src/.sdd/logs/metrics.jsonl` is the model: appended lines, never rewritten.
- Editing an agent `.md`, `AGENTS.md` or `CLAUDE.md` mid-session costs a cache write on the next turn
  that loads it. Fine for a real content change; do not churn those files to log status — use a sibling
  file or an appended note.

## Model-gated techniques — do not generalize

Some model tiers allow appending a `{"role": "system"}` entry mid-conversation without invalidating the
cached history. Support varies by model and changes over time: check the current docs for the exact
model before relying on it, and keep the append-a-new-message/file convention as the default.

## Not applicable here

Rolling breakpoints, deterministic tool-definition serialization and a `messages.create()` cache
middleware only matter for code that calls the Messages API directly. This repo has no such call site
(all Claude traffic goes through Claude Code, all OpenCode traffic through the `opencode` CLI). Re-evaluate
only if a component that calls the SDK directly is added.
