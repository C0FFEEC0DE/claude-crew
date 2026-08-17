# Architecture Decision Records

Decisions for the `agnthive` hook runtime. Each ADR records context, decision,
and a pinned interface contract so implementations can be executed independently.

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-scope-subagent-stop-footer-to-agnthive-specialists.md) | Scope SubagentStop footer contract to AgntHive specialist agents | Proposed |
| [0002](0002-per-agent-loop-block-counter.md) | Per-agent loop-block counter for SubagentStop | Proposed |
| [0003](0003-honor-stop-hook-active.md) | Honor `stop_hook_active` in the Stop hook | Proposed |
| [0004](0004-strip-plugin-namespace-in-agent-label-canonicalization.md) | Strip plugin-namespace prefix when canonicalizing agent labels | Proposed |
| [0005](0005-carry-per-key-loop-block-entry-explicitly.md) | Carry the per-key loop-block entry explicitly to the dispatcher | Proposed |
| [0006](0006-centralize-per-agent-loop-block-key.md) | Centralize the per-agent loop-block key | Proposed |
| [0007](0007-namespace-prefix-is-plugin-identity.md) | The `agnthive:` namespace prefix is plugin identity, not config | Proposed |

## Origin

These ADRs address the defects described in an untracked Russian bug report that
was supplied at the repo root and removed after the ADRs were recorded. Of the
five claims in that report, four are actionable defects (claims 1, 2, 4, 5) and
one was **refuted** (claim 3: `agent_transcript_path` is not a documented Claude
Code SubagentStop field; `last_assistant_message` is the primary path and is
already preferred by `resolvedLastAssistantMessage`). No ADR is recorded for the
refuted claim.