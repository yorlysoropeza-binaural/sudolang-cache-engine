# Fork Agent Patterns — SudoLang Constraints

You choose between forking the current agent (same context, same tools, same cached prefix) and spawning
a fresh role-specific subagent (different tools/role, no shared cache) based on what the sub-task
actually needs.

## Core Distinction

- **Fork** (`Agent(subagent_type: "fork")` in Claude Code): the child inherits the parent's full
  conversation context and tools verbatim. Because the prefix is byte-identical to the parent's, the
  fork's request is served almost entirely from cache — cheap, but only sensible when the child genuinely
  wants the *same* context and the *same* tool surface as the parent.
- **Fresh named subagent** (`Task(subagent_type: "<role>")`): the child starts with no memory of the
  parent's conversation and a possibly different, restricted tool set defined by that role. There is no
  cache to inherit — the child pays for its own system prompt from scratch (though that system prompt, if
  reused across many calls to the same role, can itself be cached across those calls — see
  `progressive-disclosure.sudo.md` and `stigmergic-coordination.sudo.md` for how to keep that reusable).

## When to Use Fork

- Independent research/verification questions over the *same* already-loaded context (e.g. "given
  everything discussed so far, check X" run in parallel for several X's)
- Parallel adversarial verification of a finding, where every verifier should see the same accumulated
  state the parent has
- Any case where re-supplying context to a fresh agent would just be re-describing what the parent
  already knows

## When Fork Is the Wrong Choice

- The sub-task needs a **different or more restricted tool set** than the parent has — a fork inherits
  the parent's tools, it cannot narrow them. Example: this repo's `sdd-builder` delegating to
  `binaural-fn-programador:senior-dev`, or `sdd-qc` delegating to
  `binaural-fn-programador:code-reviewer` — these are role-differentiated delegations (different
  responsibilities, different expected tool use, meant to be auditable as a distinct role's output), not
  "the same agent looking at the same thing again." A fresh named subagent is correct here; forking
  `sdd-builder` itself into a "senior-dev" role would blur that distinction and also hand the delegate
  tools/context it doesn't need.
- The sub-task should NOT see the parent's full history (e.g. an independent second opinion that must not
  be anchored by the parent's own reasoning) — forking defeats that independence by construction.
- The orchestrator (`sdd-lead`, `sdd-builder`, `sdd-qc`) is dispatching to a role defined in another
  agent's `.md` file specifically because that role's constraints/checklist should apply — that's what
  `Task(subagent_type: "...")` is for.

## Rule of Thumb

If you find yourself about to write "spawn a copy of myself to go look at X", that's a fork. If you find
yourself about to write "hand this off to the person/role whose job this actually is", that's a fresh
named subagent — which is what every current SDD delegation in this repo does, and should keep doing.

## Cross-reference — concrete instances of this rule in this repo

This file documents native `Agent(subagent_type:"fork")` semantics, not a new mechanism this
plugin implements. For the actual per-role decisions this repo has made (fork adopted for
`sdd-explore`/`sdd-metrics-reporter` in specific in-session cases, explicitly rejected for
`sdd-judge`, with the reasoning for each), see:

- `.claude/agents/explore.md`, section "Fork en vez de Task, cuando el caller ya tiene el
  contexto en sesión"
- `.claude/agents/sdd-metrics-reporter.md`, section "Fork en vez de Task — con una salvedad de
  tools" (a fork only inherits the launching context's tool-allowlist — `Bash` isn't automatically
  available)
- `.claude/agents/sdd-judge.md`, "Qué NO debes hacer" — the explicit "never fork this agent" rule
  and why (independence from the builder's framing is a correctness requirement, not an
  implementation detail)

## Fork availability changed (Claude Code 2.1.302, 2026-10-16)

Per the Claude Code changelog, fork subagents (`subagent_type: "fork"`) are now on by default in `claude -p`,
the Agent SDK, the desktop app and VS Code, as they already were in the terminal; `CLAUDE_CODE_FORK_SUBAGENT=0`
turns them off, and `claude mcp serve` never offers them. Consequences for this repo:

- Headless runs can now fork, so a prompt that says "use a subagent" may get a fork that inherits the whole
  parent context. For SDD delegations that must stay narrow (`sdd-builder` -> `senior-dev`, `sdd-qc` ->
  `code-reviewer`), keep naming the role explicitly; do not rely on the default.
- If a pipeline must never fork (reproducible cost, restricted context), set `CLAUDE_CODE_FORK_SUBAGENT=0`
  in that environment instead of discovering it from a bill.
- Verify the behaviour on the installed version (`claude --version`) before relying on it.

## Two-Phase Fan-Out — Evaluated and Rejected

An external architecture doc (actor-model/TupleSpace multi-agent resilience patterns, reviewed 2026-08-31)
proposes a "two-phase fan-out" for N parallel identical dispatches: fire the first one alone, wait for its
first streaming token (confirming the shared prefix is now warm in cache), then release the other N-1 so
they hit the cache instead of all paying a cold write simultaneously.

This does not carry over to how `Agent`/`Task()` work in Claude Code today: the coordinator gets no
first-token/streaming visibility into a launched agent — only a completion notification once it finishes.
There is no mechanical way to detect "the shared prefix is now cached" from the coordinator's side, and
polling for it would burn more tokens than the pattern is meant to save. Launching all N in one message
(the current guidance) remains correct. Revisit this only if the harness ever exposes per-agent
first-token/streaming state to the coordinator.
