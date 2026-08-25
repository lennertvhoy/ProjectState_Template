---
scope: "prompts"
purpose: "CTO/agent startup prompts and handoff templates"
---

# Prompts Agent Instructions

## Scope
This directory contains prompt templates for CTO sessions, coding agent startup, handoffs, and structured reviews. Agents use these as starting prompts — they do not execute them.

## Read Order (after root AGENTS.md)
1. This file
2. Relevant prompt template for the task

## Prompt Catalog
| Template | Use Case |
|----------|----------|
| `CTO_SESSION_PROMPT.md` | Start a CTO architecture/review session |
| `CODING_AGENT_STARTUP_PROMPT.md` | Start a coding agent implementation session |
| `BOOTSTRAP_INTAKE_PROMPT.md` | Initial bootstrap discovery |
| `FINAL_HANDOFF_TEMPLATE.md` | Canonical handoff shape for CTO lane |
| `ACCEPTANCE_FREEZE_TEMPLATE.md` | Record accepted user-facing milestone |
| `RUNTIME_IDENTITY_CHECKLIST.md` | Pre-acceptance runtime verification |
| `EVIDENCE_README_TEMPLATE.md` | Evidence bundle documentation |
| `SLICE_CONTRACT_TEMPLATE.md` | Define scope for implementation slice |
| `CTO_REVIEW_CHECKLIST.md` | CTO review criteria |
| `SUBAGENT_REVIEW_TEMPLATE.md` | Subagent output format |
| `SCHEMA_OWNERSHIP_TEMPLATE.md` | Schema change ownership |
| `TOOL_MODEL_ROUTING_GUIDE.md` | Model/tool selection reasoning |
| `OPENCODE_STARTUP_PROMPT.md` | OpenCode-specific startup |
| `NEW_PROJECT_FROM_URL.md` | Derive a new downstream project prompt from a repository URL |

## Usage Rules
- Prompts are **templates**, not executable code
- Fill placeholders with current repo state before use
- Do not commit filled prompts — they are session artifacts
- When creating a new prompt, add it to this catalog
- Prompts must reference root AGENTS.md invariants

## Human Override
Strong defaults. Override only with explicit human direction, recorded in handoff.