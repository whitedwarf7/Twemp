# Research notes

Research completed on 2026-08-25 before implementation.

## Selected use case: production incident response

Incident response is a strong fit for hierarchical multi-agent orchestration because it combines:

- a single accountable command role;
- recursively delegated, specialized work;
- parallel evidence gathering;
- a shared event and decision record;
- time-sensitive but risky actions; and
- an explicit transition from investigation to remediation.

It also produces an observable workflow that can be evaluated in deterministic demo mode without granting an AI system access to production infrastructure.

## Sources and findings

### OpenAI Agents SDK — orchestration

Sources:

- https://openai.github.io/openai-agents-js/guides/agents/
- https://openai.github.io/openai-agents-js/guides/multi-agent/
- https://openai.github.io/openai-agents-js/guides/running-agents/
- https://openai.github.io/openai-agents-js/guides/guardrails/
- https://openai.github.io/openai-agents-js/guides/tracing/

Relevant findings:

1. The SDK supports two LLM-led composition patterns: managers invoking agents as tools, and handoffs transferring control to a specialist.
2. Code-driven orchestration is recommended when predictability, cost control, latency, and explicit sequencing matter.
3. Independent agent tasks can run concurrently with `Promise.all`.
4. Structured outputs provide a validation boundary between model reasoning and application control flow.
5. Agent-level guardrails do not automatically wrap every nested agent or tool boundary. Checks must be placed at the actual application boundary.
6. Traces may contain sensitive model and tool data. Sensitive trace capture should be disabled unless intentionally enabled.

Decision for Twemp: deterministic code owns phase transitions, concurrency, and the approval gate. A provider owns bounded reasoning only. Every provider result is parsed through a Zod schema before entering workflow state.

### Google SRE — managing incidents

Source:

- https://sre.google/sre-book/managing-incidents/

Relevant findings:

1. An Incident Commander should hold global state and assign responsibilities.
2. Operational work, communications, and planning should be separated.
3. Responsibility can be recursively delegated into sub-incidents or component teams.
4. A live incident state document and clear event log reduce duplicated or conflicting work.
5. Uncoordinated remediation ("freelancing") can make an incident worse.
6. Response should first stop customer impact, restore service, and preserve evidence.

Decision for Twemp: the main orchestrator is the Incident Commander. Four sub-orchestrators own triage, investigation, response, and communications. Only the Response team can propose remediation, and the engine does not cross that boundary without a human decision.

### PagerDuty incident response

Source:

- https://response.pagerduty.com/

Relevant findings:

1. Mature response processes define severity, command, scribe, liaison, and subject-matter expert roles before an incident occurs.
2. The lifecycle spans preparation, active response, resolution, and post-incident learning.
3. Customer and internal communications should be explicit responsibilities rather than side work performed by technical responders.

Decision for Twemp: specialist roles include an Incident Scribe, Stakeholder Liaison, Recovery Verifier, and Postmortem Analyst. The workflow cannot resolve until independent verification passes.

## Architecture choice

Twemp uses a hybrid design, implemented as a FastAPI backend plus a Next.js client:

- **Code orchestrates:** phases, parallel fan-out, event order, schema checks, fail-closed behavior, and approval.
- **Agents reason:** evidence analysis, team synthesis, mitigation planning, verification assessment, and postmortem drafting.
- **Humans authorize:** remediation is always blocked until an explicit approval decision is recorded.
- **Providers are replaceable:** deterministic demo and OpenAI implementations share one `AgentProvider` protocol.

This avoids a single unconstrained model recursively deciding what to execute while preserving the useful specialization and synthesis properties of a multi-agent system.

## Backend platform

The workflow runs on FastAPI with Pydantic v2 because:

1. the orchestration is I/O-bound, so `asyncio.gather` maps cleanly onto the parallel specialist fan-out;
2. Pydantic provides the same declarative validation guarantees the original Zod contract relied on, at every boundary;
3. the OpenAI Agents SDK for Python offers equivalent `Agent`/`Runner` primitives, including `output_type` structured outputs and `RunConfig` tracing controls;
4. a standalone API separates the reasoning system from the presentation layer and keeps model credentials out of any rendering process; and
5. OpenAPI documentation is generated directly from the domain contract.

The Python SDK's structured outputs prefer permissive schemas, so the provider requests relaxed draft models and then normalizes them into the strict domain contract. This keeps provider compatibility without weakening the guarantees the engine depends on.
