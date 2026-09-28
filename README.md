# CMN-C1-565 — Enterprise AI Agent Local Memory & Context Persistence Q&A (OpenMemory pattern)

> **Category**: Cat 1 (delivers a single technical capability, generic and use-case-agnostic)
> **Industry**: CMN

## Overview

Answers a question about running AI-agent memory on a local-first store (the OpenMemory
pattern), using entries retrieved from that store plus a small built-in compliance overlay. The
input is the question as plain text. An empty question is rejected, and so is a question that
contains a bearer-token or `sk-` style credential marker.

The agent normalises whitespace in the question and tags it with a compliance topic by keyword:
`fisc` (for example "FISC", "data residency", "financial sector"), `appi` (for example "APPI",
"cross-border", "erasure") or `general`. It then retrieves up to `top_k` entries from an injected
local memory client, attaches one fixed note for the `fisc` or `appi` topic (none for `general`),
and asks an injected language model to write the guidance. The answer is withheld with an error if
it contains e-mail-, phone- or 12-digit-number-shaped text, or repeats a PII-shaped memory entry
verbatim. The result carries `answer` and `compliance_notes`.

Both dependencies are optional and are passed in through the graph configuration. Without a
memory client no entries are retrieved; without a language model the `answer` is an empty string
and only the compliance notes are returned. A configured model that fails or returns an empty
reply ends the run with an error. The bundled HTTP entry point supplies an Anthropic client only
when `ANTHROPIC_API_KEY` is available and never supplies a memory client, so a call through it
returns the compliance notes with an empty answer unless a model key is set. The `snapshot_kb`
setting is reserved and currently unused.

This is an agent template built with the **AGENTIC STAR** development platform and the
**AgentCore Framework**. It is intended to be taken as a starting point: fork it, adapt it to
your own data and policies, and run it inside your own AGENTIC STAR deployment.

## Requirements

**This template does not run standalone.** It requires:

| Requirement | Notes |
|---|---|
| **AGENTIC STAR platform** | The agent connects to the platform at start-up. Without it, start-up fails immediately (see *Behaviour without the platform* below). Deployment guides and API documentation: [AGENTIC STAR Developers](https://developers.fd.agenticstar.tm.softbank.jp/) |
| **AgentCore Framework** (`agenticstar-agentcore`) | Installed from PyPI as a dependency. |
| Python | 3.11 or later |

```bash
pip install -e .
```

### Behaviour without the platform

The framework is designed to run **only** on AGENTIC STAR. There is no fallback or degraded
mode. If the platform is unreachable or the SDK version does not match, the agent raises
`PlatformRequired` during graph compile / start-up preflight rather than starting in a partially
working state. This is intentional — a half-running agent is worse than one that refuses to start.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests/ -v
```

Tests run without a platform connection. Running the agent itself does not.

## Project Structure

```
src/          agent implementation (nodes, services, schemas)
tests/        unit, integration and boundary tests
config/       agent configuration
docs/         design and test specification
```

See `docs/02_design.md` for the design and `docs/03_test_spec.md` for the test specification.

## Customising

1. Adjust `config/` for your own environment and policies.
2. Replace the knowledge sources and sample data with your own.
3. Review the node implementations under `src/nodes/` for domain-specific logic.
4. Re-run the test suite.

## License

MIT — see [LICENSE](LICENSE).

## Status of this repository

This template is published **as is**, by its individual author, under the MIT license. It carries
**no warranty and no support commitment**, and no organisation stands behind its behaviour or
fitness for any purpose. Issues and pull requests may or may not receive a response; that is at
the sole discretion of the repository owner.
