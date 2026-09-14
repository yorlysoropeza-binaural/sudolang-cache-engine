# TTL Management — SudoLang Constraints

You document real Anthropic prompt-cache TTL mechanics, and the append-only convention for state updates
that keeps a long-running agent conversation/session cache-friendly.

## TTL Rules (mecánica real, no inventada)

| Cache breakpoint type | TTL | Notes |
|------------------------|-----|-------|
| Default ephemeral breakpoint | 300s (5 min) | Applies unless the extended-cache option is used |
| Extended breakpoint (`ENABLE_PROMPT_CACHING_1H` / 1h beta) | 3600s (1 h) | Higher write cost than the 5-min breakpoint, same 0.1x read discount |

There is no "subscription tier" (Pro/Max vs Free) that changes this TTL — the tier only affects usage
limits, not cache TTL. TTL is a property of the breakpoint the caller sets on the request, available to
any caller (Claude Code sessions, direct API/SDK usage) that opts into the extended option.

## TTL Behavior — No Decay, Refresh on Hit

**There is no gradual TTL decay by hit count.** A cache entry's TTL is fixed at write time (5 min or 1 h)
and is **refreshed to its full value on every cache hit** within that window — it does not shrink to 75%,
50%, 25% or any fraction as hits accumulate. If the window elapses with no hit, the entry expires and the
next request pays the full write cost again (`cache_creation_input_tokens`, priced ≈1.25x normal input)
instead of the read discount (`cache_read_input_tokens`, priced ≈0.1x normal input).

## Stale Cache Handling

If a request arrives after the TTL window has elapsed with no hit:
1. The cache entry is gone — there's nothing to invalidate explicitly, it simply isn't there anymore.
2. The request is processed as a fresh write: full input cost for that block, plus the ~1.25x write
   surcharge, and a new TTL window starts from this write.
3. This is visible in the API response's `usage.cache_creation_input_tokens` (nonzero) vs.
   `usage.cache_read_input_tokens` (zero for that block).

## Append-Only State Updates (evita romper el prefijo)

Once a stable block (system prompt, tool defs, or an early conversation turn) has been cached, **never
rewrite it** to inject a status update — that invalidates the cache for everything downstream of the
edit, for no gain. Instead:

- Append new information as a new message/turn at the end of the conversation (or, for headless
  agent-to-agent handoffs, as a **new** file/job, never an edit of a previous one).
- This repo's SDD pipeline already follows this: each OpenCode dispatch gets a new `job_id` under
  `src/.sdd/logs/jobs/<job_id>/` (moved 2026-09-05 from `/tmp/sdd-jobs/<job_id>/`, which didn't survive a
  host reboot — same append-only principle, just a persistent root), and a retry after a `sdd-judge` FAIL is
  a **new** dispatch with a fresh `Context {}` block carrying a "Contexto de reintento: ..." field — it never
  edits the previous `dispatch.handoff`. `src/.sdd/logs/metrics.jsonl` is the clearest example of this in the
  repo: every dispatch/result/orphaned transition is an **appended** JSON line, never a rewrite of a prior
  one — the file grows monotonically and stays valid to `tail`/stream even while a job is still running.
  Keep replicating that shape for any new stigmergic state (see `stigmergic-coordination.sudo.md`): write a
  new state file/message (or append a line), don't mutate the old one in place.
- Corollary for anyone editing an agent's own `.md` definition or a shared `AGENTS.md`/`CLAUDE.md`-style
  doc mid-session: expect that edit to cost a fresh cache write on the next turn that loads it — that's
  fine for a genuine content change, but don't churn those files just to log a status; use a sibling
  file or an appended note instead.

## Model-gated exception — do not generalize this as a workaround

Some Claude model tiers (Opus 5, Opus 4.8, Fable 5/5.1, Mythos 5/5.1) support appending a
`{"role": "system", ...}` entry to the `messages[]` array mid-conversation as a narrower
alternative to a brand-new turn/file, without invalidating the cached history prefix. **This is
NOT available on Sonnet 5** — the model this repo's SDD agents (`sdd-lead`, `sdd-judge`,
`sdd-metrics-reporter`, etc.) run on by default. Do not rewrite the append-only guidance above to
recommend this technique as a general-purpose shortcut for this repo's pipeline: on Sonnet 5 it
either errors or silently no-ops depending on how it's invoked. The append-a-new-message/file
convention documented above remains the correct approach here regardless of which model tier a
future agent happens to run on.

## Ideas Evaluated From an External Doc and Why They Don't Apply Here

An external architecture brief on actor-model resilience and Claude prompt-cache engineering (reviewed
2026-08-31) proposed several mechanisms that were checked against this repo and found inapplicable — kept
here so the doc doesn't get re-evaluated from scratch next time someone reads it:

- **Rolling/rotating cache breakpoints for a 20-content-block lookback limit**: this only matters for a
  caller constructing raw Anthropic Messages API requests and manually placing `cache_control` breakpoints.
  A repo-wide grep confirmed zero such calls in this codebase (`anthropic.Client`/`messages.create`/
  `cache_control` as executed code) — every Claude interaction goes through the Claude Code harness, and
  every OpenCode interaction through the `opencode` CLI, both of which manage their own breakpoint
  placement internally. Nothing here to hook into.
- **Deterministic tool-definition serialization** (alphabetical sort + `sort_keys=True` before hashing):
  same reasoning — tool defs are serialized by the harness, not by any code in this repo.
- **A custom `ClaudeCacheMiddleware` wrapping `messages.create()`**: not applicable for the same reason;
  there is no direct SDK client construction anywhere in the SDD scripts or agent configs to wrap.

If this repo ever adds a component that calls the Anthropic SDK directly (bypassing Claude Code/OpenCode),
re-evaluate these three against that new code specifically — they were rejected for lack of a callsite, not
because the underlying mechanics are wrong.
