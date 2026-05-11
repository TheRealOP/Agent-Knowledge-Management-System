# AKMS — Internal Agent Reference

This document describes the two agents that run **inside** AKMS.

**This is NOT instructions for Agent 1** (the external agent that queries AKMS).
Agent 1 reads its own project's `AGENTS.md` or `CLAUDE.md` and calls `akms` CLI commands as tools.
See `meta-learning-system/AGENTS.md` for the Agent 1 guide.

---

## Expert Agent — `src/akms/agents/expert.py`

**Role:** Answers questions about a specific knowledge section.

**Lifecycle:**
1. Created by the Orchestrator when `akms ask <section>` is called
2. Reads all markdown nodes in `knowledge/graph/<section>/`
3. Builds `_home_messages` — a system prompt containing all section knowledge
4. Cached in the Orchestrator's expert pool across queries in the same session

**Fork/rollback pattern:**
Each `answer(question)` call builds `_home_messages + [question]` — a new Python list.
`_home_messages` is never modified. No context drift across queries.

**Constraints:**
- Read-only — never writes to the knowledge graph
- One Expert per section; large sections auto-split into chunk experts
- Model: configured in `akms_config.yaml` → `agent_assignments.expert`

---

## Librarian Agent — `src/akms/agents/librarian.py`

**Role:** Curates and grows the knowledge graph.

**Operations:**
- `digest_document(file)` — splits a markdown file on headings, asks the LLM to classify each chunk (section, node_id, tags, confidence), writes graph nodes
- `ingest_log(jsonl)` — reads JSONL conversation logs, extracts factual insights, writes graph nodes
- `check_consistency(graph)` — scans all wikilinks, reports broken references
- `archive_node(section, node_id, reason)` — moves a node to `knowledge/archives/`, removes from live graph

**Constraints:**
- Write access to `knowledge/graph/` and `knowledge/archives/`
- **Never deletes nodes** — archives with reason + timestamp
- Model: configured in `akms_config.yaml` → `agent_assignments.librarian`

---

## Orchestrator — `src/akms/core/orchestrator.py`

Not an agent. A plain Python coordinator that:
- Holds the in-memory Expert pool
- Decides whether to split a large section into chunk experts (based on `expert.token_threshold`)
- Routes queries to the right chunk expert using keyword overlap scoring

---

## Agent 1 (external — not in this repo)

The user-facing agent: Claude Code, Gemma, or any other LLM. It:
- Reads `meta-learning-system/AGENTS.md` to learn its role and workflow
- Calls `akms` CLI commands as shell tools
- Is never instantiated by AKMS — it is the consumer

```
Agent 1 (Gemma / Claude Code)
  └─▶  akms ask "section" "question"   ← shell command
         └─▶  Orchestrator
                └─▶  ExpertAgent  →  claude -p (claude_cli provider)
                                      or Ollama (runpod provider)
```
