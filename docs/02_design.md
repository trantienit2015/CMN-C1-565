# Template Design Specification

## Position in AgentCore Architecture

- **Agent Class**: `Graph` (`src/graph/graph.py`)
- **L1 Base**: AgentBaseGraph
- **Three-Layer Separation**:
  - State: flat TypedDict composition (`src/schemas/state.py`, no Pydantic — msgpack incompatible)
  - Node: L1 inheritance (Template Method: `execute(self, state: dict) -> dict` override only)
  - Graph: composition (`register_nodes()` for node substitution)

## Architecture Overview

Canonical 5-step workflow, mapped onto the fixed 3-slot `AgentBaseGraph` backbone
(Cat 1: more than three business steps are grouped into the three slots).

**Scope:** In — OpenMemory local-store query patterns + FISC/APPI compliance Q&A (single
capability). Deferred — APPI erasure workflow execution (separate template), exact-match
store ops. OpenMemory is a live local store queried via Tool call (not a static KB); a
small curated snapshot KB supplements FISC/APPI compliance notes.

### Node Configuration

| Node | Responsibility | Input State | Output State | Inherits/Overrides |
|------|---------------|-------------|--------------|-------------------|
| initialize | framework default | — | — | InitializeNode (default) |
| pre_process | **QueryNormalize** — S-2 credential-shaped-token reject on raw `user_input`, then normalize + classify compliance topic (fisc / appi / general) | `user_input` | `sanitized_query`, `compliance_topic`, `validated_input` | `PreProcessNode(FunctionNode)` |
| main | **MemoryContextRetrieve + ComplianceContextEnrich + GuidanceGenerate** — Tool call to the live local-first OpenMemory API (no cloud), overlay FISC/APPI compliance notes from a curated snapshot KB, then LLM-synthesize implementation/compliance guidance (business steps live in `src/services/*`) | `sanitized_query`, `compliance_topic` | `memory_context`, `compliance_notes`, `draft_answer` | `MainNode(FunctionNode)` |
| post_process | **OutputValidate (S-3)** — deterministic PII-leak-rejection gate: raw PII-shaped memory-context content must not be echoed verbatim into the answer, else FAIL + audit log (never an LLM self-check) | `draft_answer`, `memory_context`, `compliance_notes` | `validated_answer`, `formatted_output`, `pii_leak_detected` | `PostProcessNode(FunctionNode)` |
| finalize | framework default | — | — | FinalizeNode (default) |

### Data Flow

```
START → initialize → pre_process → main → {route} → post_process → finalize → END
                                            ↓ (retry)
                                          pre_process
```

### State Definition

| Field | Type | Purpose | Required |
|-------|------|---------|----------|
| `sanitized_query` | `NotRequired[str]` | Query after normalization | No |
| `compliance_topic` | `NotRequired[str]` | fisc / appi / general | No |
| `memory_context` | `NotRequired[list[dict]]` | OpenMemory local-API retrieval results | No |
| `compliance_notes` | `NotRequired[list[dict]]` | FISC/APPI snapshot-KB overlay notes | No |
| `draft_answer` | `NotRequired[str]` | Pre-validation assembled answer | No |
| `pii_leak_detected` | `NotRequired[bool]` | S-3 gate result flag | No |
| `validated_answer` | `NotRequired[dict]` | Final validated answer payload | No |

**State Constraints (mandatory):**
- Flat TypedDict only (primitives + JSON-serializable types)
- No JWT, API keys, credentials in State (checkpoint DB leakage)
- InvocationContext via `config["configurable"]` only (not in State)
- No Pydantic models, dataclass, arbitrary Python objects (msgpack incompatible)

## Framework Utilization

### Shared Components Used
- [x] InvocationContext (correlation_id, session_id, permissions, credential handle)
- [ ] ConnectionPolicy (retry/timeout strategy) — not needed (no external write ops)
- [x] SecurityViolationError (framework-raised on S-1/S-2/S-3 violations)
- [x] S-2: `_extra_security_gate_input()` (`PreProcessNode`) — rejects credential-shaped
      tokens (`Bearer `, `sk-`) in `user_input` before normalization/classification
- [x] S-3: `_extra_security_gate_output()` (`PostProcessNode`) — preservation variant:
      rejects output missing `compliance_notes` when compliance notes were enriched upstream
      (FISC/APPI overlay must survive to the final answer)
- [x] S-4: `emit_trace_event()` — domain events in every node's `execute()`:
      `query_normalized`, `main_short_circuited_on_upstream_error`,
      `memory_context_retrieved`, `compliance_context_enriched`, `guidance_generated`,
      `output_validation_failed`, `output_validated`

> **S-2/S-3 gate behaviour by node type (ADR-017):** all three nodes are `FunctionNode`
> subclasses → the framework `@final` gate always runs automatically; domain checks are
> added exclusively via the `_extra_security_gate_input()` / `_extra_security_gate_output()`
> hooks above.

### Composition Pattern

- **Pattern**: Standalone (Cat 1, flat 3-slot backbone — no `GraphNode`/`RemoteAgentNode`
  composition; this template does not wrap another agent)
- **Composition target**: N/A
- **Error propagation strategy**: N/A (no composed sub-agent)

## Import Isolation Confirmation
- [x] Template does not import agenticstar-platform SDK (Level 0)
- [x] Import targets: framework/ and shared/ only (no agents/base/ required)

## Persistent-write bundle applicability

This template is **read-only** — it queries the OpenMemory local API and a compliance
snapshot KB, and never writes to either. The persistent-write SEC bundle (namespaced write
keys, anti-poisoning sanitization on the write path, `memory_write` audit events) is
**N/A** for this template; no write path exists in `src/`.

## Design Decision Record

| Decision | Option A | Option B | Chosen | Rationale |
|----------|----------|----------|--------|-----------|
| L1 base type | AgentBaseGraph | AutonomousBaseGraph | **AgentBaseGraph** | Cat 1 single-shot retrieval Q&A, no autonomous think-act loop |
| Composition pattern | Standalone | GraphNode subgraph | **Standalone** | 5 workflow steps fit the fixed 3-slot backbone directly (pre_process=step 1, main=steps 2-4, post_process=step 5); no inner subgraph needed |
| Trust level | ANONYMOUS | VERIFIED_EXTERNAL | **ANONYMOUS** (agent + all nodes) | Read-only Q&A, no privileged operation, no write side-effect |
| Memory source handling | Ingest into KB | Live Tool call, local-first | **Live Tool call, local-first** | Scope boundary (§4 proposal): OpenMemory is queried live via a local API, never a cloud-hosted store, to satisfy FISC FY2026 data-residency + APPI cross-border-transfer avoidance |
