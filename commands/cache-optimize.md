---
description: Optimize a prompt for cache stability using Frente Estable/Fondo Volátil pattern
allowed-tools: Read, Write, Edit
disable-model-invocation: false
---

# Cache Optimize

Transform a prompt into a cache-optimized structure:

## Input
The user provides a raw prompt to optimize.

## Process

1. **Parse Prompt**
   - Identify static instructions vs dynamic content
   - Extract constraints, schemas, rules
   - Identify user-specific variables

2. **Apply Frente Estable / Fondo Volátil**
   - Move ALL static content to prefix (first 80%)
   - Move ALL dynamic content to suffix (last 20%)
   - Insert implicit cache breakpoint

3. **Convert to SudoLang**
   - Transform verbose instructions → concise constraints
   - Replace "you should always" → "All X MUST be Y"
   - Replace "it's important that you never" → "NEVER do X"
   - Replace step-by-step → pipe operator `|>`

4. **Validate Cache Stability**
   - Check: no timestamps in prefix
   - Check: no UUIDs in prefix
   - Check: no file paths in prefix
   - Check: no user input in prefix

5. **Output Optimized Prompt**
   ```markdown
   [CACHE-STABLE PREFIX — Frente Estable]
   (2000-4000 tokens of static instructions)

   ---
   [DYNAMIC SUFFIX — Fondo Volátil]
   (500-2000 tokens of dynamic content)
   ```

## Example

**Input:**
```
Please help me review this code. Today is 2026-08-09. 
The file is /home/user/project/main.py. 
Make sure to check for security issues.
```

**Output:**
```markdown
## Constraints (Frente Estable — CACHE STABLE)
- All code reviews MUST check for: SQL injection, XSS, path traversal
- All responses MUST include severity rating (CRITICAL/HIGH/MEDIUM/LOW)
- NEVER approve code with CRITICAL issues
- All file references use relative paths only

---
## Current Review (Fondo Volátil — DYNAMIC)
- File: main.py
- Date: 2026-08-09
- Review type: security

## Findings
(content goes here)
```
