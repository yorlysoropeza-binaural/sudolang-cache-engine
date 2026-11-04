# Memory Injection — SudoLang Constraints

You expose a persistent memory (Engram, local) to agents. Two kinds of content reach a prompt, and they
obey different cache rules: a fixed protocol (stable front) and a per-job snapshot (volatile). Mixing them
breaks the prefix of every agent that receives them.

## Constraints

- The protocol (`scripts/memory-protocol.md`) is STABLE: byte-identical on every turn and dispatch, read from
  a file, never built from dates, ids, paths or counters. It goes into the system prompt only for editors.
- The per-job snapshot is VOLATILE: it never goes into the system prompt. It is passed by reference
  (`memory_ref:` in the dispatch context) and the agent reads it with its file tool, so it arrives as a
  message appended to the conversation.
- Pin the mode per job (`SDD_MEMORY_MODE` / `memory:`) and record it, with the snapshot sha256, in the dispatch
  handoff and the metrics. Switching it mid-job rewrites the cached prefix and makes runs incomparable.
- Inject only into editors. Never into orchestrators, judges, QC or relays that return structured output.
- Add the protocol to the compaction context of the same agents, or the compaction request loses the prefix.
- Long-term search results are on-demand tool results (`mem_search`, `mem_get_observation`): they arrive at the
  end of the context and are cache-safe. Do not preload them into a prompt.
- Tool schemas count as prefix too: grant the memory tools per agent (permission or `tools:`), not globally.
- Every persisted item is redacted before writing (secrets, `<private>` blocks, client names, tickets). Session
  ids are explicit on every write.
- Claims of savings need a pre-registered A/B (tokens, rounds to PASS, repeated errors). Byte counts are not
  evidence.

## Verify

Diff the injected protocol between two dispatches of the same stage (must be identical). Confirm the snapshot
never appears in `experimental.chat.system.transform` output. Check the plugin source for network, child
processes and global state. Re-check the `experimental.*` hooks after an OpenCode upgrade.
