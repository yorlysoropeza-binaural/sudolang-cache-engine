---
description: Restructure an agent prompt/Task() template for cache stability using the Frente Estable/Fondo Volátil authoring pattern
allowed-tools: Read, Write, Edit
disable-model-invocation: false
---

# Cache Optimize

Transform a prompt/template — an agent system prompt, a `Task()` call, a dispatch script's prompt
contract — into a cache-friendly structure. This restructures a **template you will reuse**, not a
one-off reply.

## Input
The user provides a raw prompt/template to optimize (or a file path to one).

## Process

1. **Parse the Template**
   - Identify static instructions/schema vs. per-call values
   - Identify any pasted file content that could instead be a path reference

2. **Apply Frente Estable / Fondo Volátil**
   - Move ALL static content to the stable block (goes first)
   - Move ALL per-call values to the trailing dynamic block (goes last)
   - Label the boundary explicitly (a real `cache_control` breakpoint, if any, is set by the caller —
     Claude Code/the Agent SDK do this automatically on system prompts and tool defs)

3. **Convert to SudoLang where it shortens without losing meaning**
   - "you should always" → "All X MUST be Y"
   - "it's important that you never" → "NEVER do X"
   - step-by-step prose → pipe operator `|>` where genuinely sequential

4. **Validate Cache Stability**
   - No timestamps/UUIDs/session paths in the stable block
   - No pasted file content in the stable OR dynamic block where a path reference would do
   - Field names/order in any `Context {}` schema are fixed, not reworded per call

5. **Output**
   ```markdown
   [STABLE — Frente Estable]
   (static instructions/schema)

   ---
   [DYNAMIC — Fondo Volátil]
   (per-call values, referenced file paths, not pasted content)
   ```

## Example

**Input:**
```
Please review this code. Today is 2026-08-09.
The file is /home/user/project/main.py.
Make sure to check for security issues.
```

**Output:**
```markdown
## Constraints (STABLE)
- All code reviews MUST check for: SQL injection, XSS, path traversal
- All responses MUST include a severity rating (CRITICAL/HIGH/MEDIUM/LOW)
- NEVER approve code with CRITICAL issues open

---
## Current Review (DYNAMIC)
- File: main.py
- Date: 2026-08-09
- Review type: security

## Findings
(content goes here)
```

Do not claim a specific measured token-savings percentage in the output — report the structural change
made (what moved where), not an unverified metric.
