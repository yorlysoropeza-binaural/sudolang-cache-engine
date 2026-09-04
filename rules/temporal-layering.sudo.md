# Temporal Layering — SudoLang Constraints

You enforce strict temporal separation when **authoring** agent system prompts, `Task()`/dispatch prompt
templates, and docs meant to be reused byte-for-byte across calls.

## Forbidden in the Stable Block (Frente Estable)

NEVER include these in a template's cache-stable part:
- Current date/time (`2026-08-09`, `now()`)
- UUIDs or random identifiers
- File hashes or checksums
- User-specific or session-specific paths (`/home/user/...`, `/tmp/sdd-jobs/<job_id>/...`)
- Session IDs, job IDs, or request IDs
- Any value from `datetime.now()`, `uuid4()`, `os.urandom()`

## Required in the Dynamic Block (Fondo Volátil)

ALWAYS push these to the trailing dynamic part of the template:
- Timestamps and dates
- Hashes, checksums, job/session IDs
- User input verbatim
- File paths and names specific to this call
- Execution results, error messages

## Pattern: Stable Schema + Dynamic Data

```markdown
## Context {} Schema (STABLE — field names/order never change)
Context {
  <field_1>: <type/description>
  <field_2>: <type/description>
}

---
## Current Call (DYNAMIC — values change every call)
Context {
  <field_1>: 2026-08-24T12:00:00Z
  <field_2>: job-abc123
}
```

## Authoring-Time Anti-Pattern Check

When writing or reviewing an agent `.md` / `Task()` template, scan for:
- A date/time literal outside the trailing dynamic section → move it
- A UUID/job-id literal outside the trailing dynamic section → move it
- A file path specific to one run outside the trailing dynamic section → move it
- Pasted user input or file content outside the trailing dynamic section → move it, or better, replace it
  with a reference (see `stigmergic-coordination.sudo.md`)

This is a lint on the **template you write**, applied before you send/reuse it — not something the model
does to its own free-text reply after the fact (a reply has no cache boundary of its own to police).
