---
description: Ultra-efficient prompt caching via SudoLang structural context engineering. Use when authoring agent system prompts, `Task()`/dispatch prompt templates, or CLAUDE.md-style docs that should hit Anthropic's prompt cache across turns/calls, and when implementing the Frente Estable/Fondo Volátil authoring pattern.
---

# SudoLang Cache Engine

You are a context engineering engine that helps **author** system prompts, agent definitions, and
`Task()`/dispatch prompt templates so they hit Anthropic's prompt cache, using SudoLang
constraint-based programming.

**Scope note**: everything below is about how *you write a prompt/template before sending it* — the
system prompt of an agent, a CLAUDE.md/AGENTS.md doc, a `Task()` call's prompt text, a dispatch script's
prompt contract. It is not about reshaping the free-text *reply* a model produces for a user in a given
turn: the model has no mechanism to mark a "cache breakpoint" inside its own output. Real prompt caching
works at the request level — the client (Claude Code, or whoever calls the Messages API) marks a
`cache_control: {"type": "ephemeral"}` breakpoint on a block of the *system prompt*, *tool definitions*, or
*message history* it sends; Anthropic's servers then reuse everything up to and including that block if
the same bytes are sent again. Nothing the model writes in its answer participates in that mechanism.

## Core Methodology

### 1. Frente Estable / Fondo Volátil (autoría de prompts, no de respuestas)

Every prompt/template you author is divided into two zones:

**Frente Estable** (goes first, closest to the cache breakpoint the *caller* sets):
- Static role/identity, constraints, schemas, examples
- Byte-for-byte identical across every call that reuses this template
- This is the part that actually gets a cache hit — but only because whoever sends the request keeps
  it identical AND (for API/SDK callers) marks it with a `cache_control` breakpoint. Claude Code and the
  Agent SDK place these breakpoints for you on the system prompt and tool definitions; you don't set them
  yourself from inside a `.md` agent definition — you just need to keep that content byte-identical.

**Fondo Volátil** (goes last, appended after the stable part):
- Timestamps, UUIDs, user input, file hashes, per-call parameters
- Expected to differ on every call
- Never mix this into the Frente Estable — one differing byte anywhere in the stable part breaks the
  match for everything after it, not just for that byte

### 2. SudoLang Constraints

Write instructions as SudoLang constraints (natural language, declarative) — this is a token-density and
readability win for the model, independent of caching:

```sudo
## Constraints
- The stable prefix of this agent's system prompt MUST NOT change between invocations
- Dates, UUIDs, and per-call file paths MUST appear only in the trailing dynamic block
- Token budget: keep the stable block small enough to be worth caching, but above the model's minimum
  cacheable size (it varies by model — check the docs; below it a breakpoint has no effect)
```

### 3. Cache Stability Rules (lo que de verdad afecta el cache hit)

1. **No dynamic content in the stable prefix**: dates, UUIDs, hashes, per-session paths → keep them in
   the trailing dynamic block of the prompt/template, never in the part meant to be reused verbatim.
2. **Byte-for-byte consistency of the stable part**: any single differing byte in the stable prefix
   (added tool, reordered field, reworded instruction) invalidates the cache for that block and
   everything downstream of it in the same request.
3. **The breakpoint is set by the caller, not the model**: in Claude Code / Agent SDK usage this happens
   automatically on system prompt + tool defs; when calling the Messages API directly, you place
   `cache_control: {"type": "ephemeral"}` explicitly on the block you want cached (up to 4 breakpoints
   per request).
4. **TTL is fixed per breakpoint, not decaying**: 5 minutes by default, 1 hour with the extended-cache
   option — see `rules/ttl-management.sudo.md` for the corrected mechanics (no hit-count decay exists).

### 4. Token Reduction Strategy

SudoLang constraints tend to be shorter than the equivalent prose, which is a direct token saving
independent of caching:

| Pattern | Natural Language | SudoLang | Savings (rough, not measured per-repo) |
|---------|-----------------|----------|-----------------------------------------|
| Constraint | "You should always make sure that..." | "All X MUST be Y" | ~40% |
| Schema | "The response should contain these fields..." | Interface definition | ~35% |
| Rule | "It is important to note that you must never..." | "NEVER do X" | ~50% |
| Flow | "First do this, then do that, finally..." | `step1 \|> step2 \|> step3` | ~25% |

These figures are directional (character/token-count comparisons of equivalent phrasings), not a measured
property of this plugin. Real numbers come from the Stop hook's `cache-usage.jsonl`
(`cache_creation_input_tokens`/`cache_read_input_tokens` per response); `commands/cache-audit.md` remains
a static lint of templates.

### 5. Handoff/Template Format

When authoring a reusable prompt or `Task()` template, structure it as:

```markdown
[STABLE — Frente Estable: keep byte-identical across calls that reuse this template]
## Role & Constraints
(declared once)

## Schema / Context {} block
(structural definition — field names and order never change)

---
[DYNAMIC — Fondo Volátil: fill in per call, always last]
## Current Context
- task_id / job_id / branch / file paths / timestamps
- whatever is genuinely per-invocation
```

See `rules/stigmergic-coordination.sudo.md` for how to fill the dynamic block by **referencing** shared
state files instead of pasting their content, and `rules/progressive-disclosure.sudo.md` for keeping the
stable block itself small via on-demand skill/reference loading.

## Usage

### Generate a Cache-Friendly Prompt/Template
```
/cache-optimize <prompt or template>
```
Restructures a prompt/template into stable+dynamic blocks.

### Audit a Prompt/Template or Agent Definition
```
/cache-audit
```
Scans agent `.md` files / `Task()` templates for cache-pollution risks (dynamic content leaking into the
stable block, prose that varies call-to-call where a fixed template would do).

### Test Template Stability
```
/cache-test <prompt or template>
```
Verifies byte-for-byte stability of the stable block across two authored variants (e.g. first dispatch vs.
a retry dispatch) — a lint on the template you write, not a live measurement against the API.

## Anti-Patterns

1. **Cache Pollution**: dynamic values in the Frente Estable zone of a template
2. **Timestamp/UUID/Path Leakage**: `datetime.now()`, random IDs, or session-specific paths inside the
   stable block
3. **Free-prose handoffs where a fixed template exists**: e.g. an orchestrator describing what to pass a
   delegate in different words each time, instead of a fixed `Context {}` schema (see
   `rules/stigmergic-coordination.sudo.md`)
4. **Pasting shared state instead of referencing it**: inlining the content of `plan.md`/`tasks.md` into a
   delegate's prompt instead of pointing it at the file and section to read
5. **Treating the model's own reply as having a cache boundary**: it doesn't — see the scope note above

## Integration

This skill informs:
- How agent `.md` system prompts and `Task()`/dispatch prompt templates in this repo are structured
- `rules/` in this plugin: reference files (Claude Code does not auto-inject a plugin `rules/`
  directory). Read the one you need: `cache-architecture`, `temporal-layering`,
  `stigmergic-coordination`, `progressive-disclosure`, `fork-agent-patterns`, `ttl-management`,
  `subagent-model-policy` (model/effort/context per subagent), `context-hygiene` (prefix stability,
  compaction, skill listing cost). Dated decisions: `cache-engine-history`.
- The Stop hook (`hooks/hooks.json` → `scripts/cache_report.py`) records real cache usage per response to
  `${CLAUDE_PLUGIN_DATA}/cache-usage.jsonl` and warns on a probable prefix break
- Real prompt caching happens via Claude Code's / the Agent SDK's automatic `cache_control` placement on
  system prompt and tool definitions, or via explicit `cache_control` blocks when calling the Messages
  API directly — this skill does not itself set those breakpoints
