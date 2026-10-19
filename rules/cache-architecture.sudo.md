# Cache Architecture — SudoLang Constraints

You are a context engineering engine helping **author** system prompts, agent definitions, and
`Task()`/dispatch prompt templates for Anthropic prompt caching. This governs how you write those
templates — not how you shape a live reply to a user.

## Core Constraints

Every authored prompt/template MUST follow the Frente Estable / Fondo Volátil layout:

- **Frente Estable** (cache-stable block, goes first): static instructions, schemas, rules, constraints,
  `Context {}` field definitions — content that stays byte-identical across every call reusing this
  template.
- **Fondo Volátil** (dynamic block, goes last): timestamps, UUIDs, user input, file hashes, per-call
  field values — content that differs on every call.

The actual cache breakpoint is placed by whoever sends the request (Claude Code / the Agent SDK do this
automatically on the system prompt and tool definitions; direct Messages API callers set it explicitly
with `cache_control: {"type": "ephemeral"}`) — authoring the template this way is what makes that
breakpoint effective, it does not create the breakpoint by itself.

## Layout Rule

```
[STABLE BLOCK — Frente Estable]
  1. System role & identity
  2. Constraints & rules
  3. Schema / Context {} field definitions
  4. Example patterns
  5. Anti-patterns to avoid
  ---
  (this is where a real cache_control breakpoint would go, set by the caller)
  ---
[DYNAMIC BLOCK — Fondo Volátil]
  6. Current timestamp (if needed)
  7. User input / query
  8. File-specific context (paths, not pasted content — see stigmergic-coordination.sudo.md)
  9. Execution results
```

## Sizing Guidance

There's no fixed "optimal" token budget — a stable block only pays off if it's (a) large enough that
caching it is worth the write cost (the minimum is per model: 512 tokens on the Claude 5.5 models, 1,024 on
Sonnet 5 / 4.x, up to 4,096 on Opus 4.5/4.6 and Haiku 4.5 per the docs checked 2026-10-19; below it the
breakpoint silently has no effect, no error) and (b) genuinely reused byte-for-byte across multiple calls. A 200-token
system prompt reused twice isn't worth engineering around; a multi-KB agent definition or `Task()`
template reused across dozens of dispatches is.

## Authoring Checklist

Before treating a template as "cache-friendly", verify:
1. The stable block is byte-for-byte identical across every call meant to reuse it — no field reordering,
   no rewording, no conditionally-included examples.
2. Only the trailing dynamic block contains per-call values.
3. No dynamic value (date, UUID, path, pasted file content) leaked into the stable block.
