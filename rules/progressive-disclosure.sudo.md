# Progressive Disclosure — SudoLang Constraints

You keep an agent's stable system prompt small by loading detailed reference material **on demand**
instead of inlining it — the stable block should be a role/constraints/schema summary, not a manual.

## Core Constraint

An agent definition's system prompt MUST NOT inline a large reference manual (extended examples, full
domain checklists, historical rationale) that is only needed for part of the role's work. Instead, the
system prompt should be short, and point to a Skill (or other on-demand-loadable resource) that the agent
invokes only when it actually needs that depth.

## Reference Implementation in This Repo (SDD agents)

Every `sdd-*.md` agent in `.claude/agents/` already opens with exactly this pattern — treat it as the
canonical example:

```
Antes de actuar, invoca el Skill `sdd-<role>-agent` para cargar el conocimiento detallado de este rol.
```

The agent's own `.md` file stays short (role summary, responsibilities, a small checklist) — the deep
knowledge (full protocol, edge cases, worked examples) lives in `src/.opencode/skills/sdd-<role>-agent/
SKILL.md` and is only pulled into context when that specific agent is invoked, not paid for by every other
agent's system prompt in the pipeline.

This is also why this repo keeps `~/.claude/skills` curated to a small always-loaded set (see
CLAUDE.md → "Skills: where to look") rather than listing all ~800 skills every turn: the same
progressive-disclosure principle applied at the whole-session level, not just per-agent.

## Cross-reference — this is documentation of a native mechanism, not a new one

The `.md`-stays-short / deep-content-in-a-Skill split described above is how Claude Code's
Skills-on-demand loading already works natively — this file documents the pattern, it doesn't add
capability beyond it. See `docker-multi/AGENTS.md` rule 155 for where this repo's own
`sdd-*`/`.claude/agents/*.md` files apply exactly this split, and `docker-multi/CLAUDE.md`'s
"Skills: where to look" section for the (currently unenforced) intended curation design at the
whole-session level referenced above.

## Authoring Checklist

Before adding a new example, checklist, or reference block to an agent's `.md` system prompt, ask:
1. Does every invocation of this agent need this content, or only some tasks?
2. If only some — move it to the agent's Skill (or a new skill) and reference it by name, don't inline it.
3. Does this content change frequently? If so, inlining it in the agent `.md` also means every edit
   invalidates the cached system-prompt block for that agent on the next turn — another reason to keep it
   in a separately-loaded skill.
