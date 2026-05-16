# Antigravity Rules

These rules guide experimental or non-standard approaches while preserving core system principles.

## Goals
- Prioritize reliability and crash recovery over cleverness.
- Keep the workflow local-first and vendor-light.
- Maintain stateful, checkpointed execution.

## Constraints
- Do not bypass LeadState; all changes must flow through it.
- Avoid non-deterministic behavior unless explicitly requested.
- Keep Docker builds portable and repeatable.

## Output Rules
- Be concise and explicit about tradeoffs.
- Ask before changing core architecture.
- Never include secrets or API keys.