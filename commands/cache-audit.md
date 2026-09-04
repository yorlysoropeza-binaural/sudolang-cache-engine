---
description: Audit agent system prompts, Task()/dispatch templates and shared docs for cache-pollution and drift risks
allowed-tools: Read, Grep, Glob
disable-model-invocation: false
---

# Cache Audit

Audit the **files** that make up this repo's agent/prompt-template surface for cache-pollution and
handoff-drift risks (this reads files, not live API usage metrics — there is no built-in access to real
`cache_creation_input_tokens`/`cache_read_input_tokens`):

1. **Scan for Cache Pollution in Templates**
   - Grep agent `.md` files and dispatch scripts/templates for dynamic content (timestamps, UUIDs,
     job/session IDs, per-run file paths) appearing outside a clearly-labeled trailing dynamic block
   - Report each violation with file + line position

2. **Scan for Handoff-Template Drift**
   - For each place one agent delegates to another via `Task()` or a dispatch script, check whether the
     handoff uses a fixed `Context {}`-style schema (field names/order stable) or free prose that could
     vary call to call
   - Flag any delegation described only in prose where a fixed schema would reduce drift

3. **Scan for Pasted-vs-Referenced State**
   - Check whether a delegate's prompt pastes the content of a shared file (spec.md/plan.md/tasks.md- or
     job-handoff-style state) instead of pointing it at the file/section to read
   - Flag pasted content as a candidate for the stigmergic-coordination pattern
     (`rules/stigmergic-coordination.sudo.md`)

4. **TTL/Mechanics Sanity Check**
   - Confirm no rule/doc in scope claims a hit-based TTL decay or a model-side "cache breakpoint" inside
     its own reply — both are incorrect; see `rules/ttl-management.sudo.md`

5. **Generate Report**
   ```json
   {
     "files_scanned": ["..."],
     "pollution_violations": [{"file": "...", "line": 0, "issue": "..."}],
     "prose_handoffs_without_schema": [{"file": "...", "delegation": "..."}],
     "pasted_state_findings": [{"file": "...", "should_reference": "..."}],
     "recommendations": ["..."]
   }
   ```

Do not report a "cache_hit_rate" or "ttl_compliance" percentage — those require live API telemetry this
command does not have access to; report concrete file/line findings instead.
