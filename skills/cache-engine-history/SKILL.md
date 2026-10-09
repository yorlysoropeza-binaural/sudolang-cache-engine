---
description: Dated decisions and incidents behind the sudolang-cache-engine rules (why an idea was rejected, what was found in audits). Load only when re-evaluating a past decision; the rules themselves stay date-free.
disable-model-invocation: true
---

# SudoLang Cache Engine — decision history

Kept out of `rules/` because `temporal-layering` forbids dates in guidance that should stay stable.

- **2026-08-31 — external actor-model/cache-middleware brief reviewed.** Rejected for lack of a call
  site: rolling breakpoints for the 20-block lookback, deterministic tool-def serialization, and a
  `ClaudeCacheMiddleware` around `messages.create()`. A repo-wide grep found no direct SDK call
  (`anthropic.Client`/`messages.create`/`cache_control` as executed code). Rejected because there was
  nothing to hook into, not because the mechanics are wrong.
- **2026-09-05 — job root moved** from `/tmp/sdd-jobs/<job_id>/` (lost on reboot) to
  `src/.sdd/logs/jobs/<job_id>/`. Same append-only principle, persistent root. A relay that retyped
  prompts also showed a fidelity failure (see `temporal-layering` rule).
- **2026-09-14 — audit:** nothing in the plugin read `settings.json` at runtime.
- **2026-10-09 — review against Claude Code docs:**
  - A plugin has no `rules/` component: `rules/*.sudo.md` are not auto-injected, they are reference
    files read through the umbrella skill. A plugin `settings.json` only honors `agent` and
    `subagentStatusLine`, so the old TTL/prefix keys were dropped and the file was removed.
  - The earlier claim that mid-conversation system entries are unavailable on a specific model tier was
    removed from `ttl-management`: it was never verified against docs and ages badly.
  - Added the Stop hook that records real cache usage; the plugin is no longer purely static analysis.
