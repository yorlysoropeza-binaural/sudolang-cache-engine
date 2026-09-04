---
description: Test whether two authored variants of a prompt/template (e.g. a dispatch vs. its retry) keep the stable block byte-for-byte identical
allowed-tools: Read, Bash
disable-model-invocation: false
---

# Cache Test

Verify that a prompt/template keeps its stable block byte-for-byte identical across the calls meant to
reuse it — e.g. an initial dispatch and its retry, or two `Task()` calls to the same delegate role. This
is a lint on **authored templates you provide**, not a live measurement against the Anthropic API (no
`cache_creation_input_tokens`/`cache_read_input_tokens` data is available here).

## Input
The user provides two variants of a prompt/template (paths or inline text) — e.g. "first dispatch" and
"retry dispatch" — that are expected to share a stable block.

## Process

1. **Split Each Variant**
   - Identify the stable block and the trailing dynamic block in each variant (per the labeled boundary,
     or infer it from where dynamic-looking content starts)

2. **Byte-Compare the Stable Blocks**
   - Report: identical / different
   - If different: show the exact diff and which authoring rule it violates (e.g. a reworded constraint,
     a reordered `Context {}` field, a leaked timestamp)

3. **Check for Pollution in Either Variant**
   - Scan each stable block for dates, UUIDs, job/session IDs, per-run paths
   - Report any found, regardless of whether the blocks otherwise matched

4. **Output Report**
   ```json
   {
     "stable_block_identical": true,
     "diff": null,
     "pollution_found": [],
     "verdict": "PASS"
   }
   ```

## Verdicts

- **PASS**: stable blocks identical, no pollution found
- **WARN**: stable blocks identical but pollution found in them
- **FAIL**: stable blocks differ

This tests the templates as authored — it does not confirm an actual cache hit occurred on Anthropic's
servers, which would require reading `usage.cache_read_input_tokens` from a real API response.
