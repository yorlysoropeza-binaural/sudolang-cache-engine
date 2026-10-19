# Stigmergic Coordination — SudoLang Constraints

You coordinate multi-agent work through **shared state on disk**, not by passing accumulated
transcripts between agents. This is the "pizarra compartida" pattern: agents read and write files; they
don't hand each other conversation history.

## Core Constraint

An orchestrator delegating to another agent MUST NOT paste the full content of a shared artifact into the
delegate's prompt when a file reference would do. Instead:

```
Context {
  <artifact>_ref: <path>#<section/id>
}
```

...and instruct the delegate to read that path/section itself. The delegate gets a fresh context window;
reading the file costs it the same tokens regardless of who reads it, but pasting the content into the
orchestrator's prompt costs those tokens **twice** (once when the orchestrator read/composed it, again
when the delegate receives it inline) and makes the orchestrator's prompt vary every time the artifact
changes, which defeats template stability (see `cache-architecture.sudo.md`).

## Reference Implementation in This Repo (SDD pipeline)

This repo's SDD flow already is a stigmergic system — treat it as the canonical example, not something to
reinvent per-feature:

| Shared artifact | Written by | Read by |
|---|---|---|
| `spec.md` | `sdd-spec` | `sdd-architect`, `sdd-pm`, `sdd-judge` |
| `plan.md` | `sdd-architect` | `sdd-pm`, `sdd-builder` |
| `tasks.md` | `sdd-pm` | `sdd-builder`, `sdd-qc` |
| `qc-report.md` | `sdd-qc` | `sdd-lead`, `sdd-judge` |
| `src/.sdd/logs/jobs/<job_id>/dispatch.handoff` | `sdd-opencode-runner` (dispatch) | OpenCode `sdd-lead`, later `sdd-judge` |
| `src/.sdd/logs/jobs/<job_id>/result.handoff` | OpenCode pipeline | `sdd-opencode-runner` (status-check), `sdd-judge` |
| `src/.sdd/logs/metrics.jsonl` | `sdd_opencode_run.sh`/`status.sh` (append-only, one JSON line per transition) | `sdd-metrics-reporter` |

(moved 2026-09-05 from `/tmp/sdd-jobs/` — that root didn't survive a host reboot, losing every job's record;
`src/.sdd/logs/` is a persistent, repo-relative root instead, overridable via `SDD_LOG_ROOT`.)

None of these are meant to be pasted whole into another agent's prompt — the consuming agent reads the
file itself. Any **new** delegation added to this pipeline (e.g. `sdd-builder` → `senior-dev`, `sdd-qc` →
`code-reviewer`) should follow the same shape: reference `plan.md#<section>` / `tasks.md#<task_id>` by
path in the `Context {}` block, not paste an "extracto relevante" into the prompt text.

## When Pasting Is Actually Fine

Small, genuinely one-shot values that aren't reused elsewhere (a single EARS requirement ID, a task ID, a
branch name) belong directly in the dynamic block of the `Context {}` schema — they're not "shared state",
they're per-call parameters. The rule is about avoiding duplicated large content (a whole plan section, a
whole diff, a whole prior transcript), not about banning every literal value from a prompt.

## Concurrency Note

If two agents can write to the same artifact concurrently (e.g. two parallel `Task()` delegates both
wanting to update `tasks.md`), that's a real hazard (lost writes) — prefer one writer per artifact per
phase (this repo's SDD pipeline already is single-writer-per-phase) over ad hoc concurrent writes.

## Declaring the Active Phase

Every `Context {}` block dispatched into this pipeline should declare which SDD phase is active, e.g. (the field is `phase:` —
the name `scripts/sdd_opencode_run.sh` reads and records in `metrics.jsonl`; earlier drafts called it `stage:`):

```
Context {
  phase: spec | plan | tasks | build | qc | review-fix   # optional; defaults to "pipeline"
  <artifact>_ref: <path>#<section/id>
}
```

**Exception — full-pipeline dispatch**: this repo's "Modo Delegación" dispatches the entire pipeline in one
`Context {}` block (`agent: sdd-lead`, which internally chains spec→architect→pm→builder→qc itself) rather
than one phase at a time. There, `phase` doesn't apply — omitting it isn't a missing field, it's the correct
shape for "all stages, single dispatch." Only phase-by-phase dispatch (Modo Manual, targeting `@sdd-spec` /
`@sdd-architect` / etc. individually) needs to declare `phase`.

This is a lightweight borrowing of the "stage → allowed actions" idea from an external actor-model/FSM
architecture doc (reviewed 2026-08-31) — without adopting a real finite-state-machine engine: `phase` is
just a stable, explicit field, not a new enforcement mechanism (the actual enforcement of what an agent may
touch in a given stage is still OpenCode's `permission` guardrails, see `sdd-opencode-guardrails`). Two
benefits: it makes which phase produced a given dispatch traceable at a glance, and — since it's a small,
fixed-vocabulary value rather than free prose — it keeps the dynamic block's shape stable across dispatches
of the same phase, which is what actually matters for cache stability (see `cache-architecture.sudo.md`).
