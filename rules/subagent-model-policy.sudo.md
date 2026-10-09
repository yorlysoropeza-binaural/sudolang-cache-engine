# Subagent Model Policy — SudoLang Constraints

You choose model, effort and context for each subagent by the work it does, because every spawn pays
for its own system prompt, tool list and (unless omitted) CLAUDE.md.

## Constraints

- Relay or polling agents (run a script, return its output) MUST use `model: haiku`, `effort: low`, a
  small `maxTurns`, and `tools` limited to what the script needs.
- Read-only scanners (search, metrics aggregation, inventory) SHOULD use `model: haiku` or the cheapest
  model that returns correct structured output; give them `disallowedTools` for anything that writes.
- Editors, reviewers and orchestrators that make judgment calls keep the stronger model; do not
  downgrade them to save tokens without measuring failure rate.
- A subagent that does not need project rules SHOULD set `omitClaudeMd: true`; a subagent that does MUST
  receive them through a skill it loads on demand rather than a large CLAUDE.md.
- Preloading skills with `skills:` in frontmatter is incompatible with `disable-model-invocation: true`
  on those skills; never set that flag on a skill a subagent preloads.
- A subagent that waits on long external work (OpenCode job) MAY set `experimental: { cacheTtl: 1h }`
  only if measured idle gaps exceed 5 min; otherwise keep the 5 min default.
- Prefer one fork/subagent per independent question; never fan out the same context to several agents.

## Verify

Check frontmatter against the current Claude Code docs (`sub-agents`) before relying on a field; some
fields are version-gated. Measure per-agent spend with `/usage` before and after a change.
