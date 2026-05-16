# Agent Operating Rules

You are working inside the outbound_agent repository.

Priorities:

- reliability and crash recovery over flashy architecture
- local-first execution and minimal vendor dependencies
- keep upgrade paths intact

Before making code changes:

1. Understand existing architecture
2. Preserve LangGraph flow
3. Preserve LeadState schema
4. Never rename public interfaces without reason

When adding features:

- prefer adding new nodes
- avoid modifying existing nodes unless necessary
- preserve backward compatibility
- keep dependencies lean and explicit

When debugging:

- identify root cause
- propose minimal patch
- explain tradeoffs

When refactoring:

- keep API stable
- avoid unnecessary abstractions

When writing code:

- code must run immediately
- no placeholders
- no TODO-only implementations

Never:

- delete files without explicit instruction
- replace SQLite with another DB
- introduce new frameworks without justification
- rewrite architecture
- send real outreach emails from tests or examples