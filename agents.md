# AKMS — Agent Instructions

> **Read this file first.** It tells you how to work with this project's knowledge graph.

---

## What is this project?

AKMS (Agent Knowledge Management System) is a Python library that gives AI agents **persistent memory** via a knowledge graph. Knowledge is stored as markdown files backed by SQLite — human-readable, git-friendly, and searchable.

You are operating inside a project that uses AKMS. This means there is a `knowledge/` directory containing structured knowledge you can query, and a set of tools you should use before answering domain-specific questions.

---

## Your #1 Rule

**Before answering a question about a domain topic, check the knowledge graph first.**

Do not guess. Do not hallucinate. If the knowledge graph has relevant nodes, use them. If it doesn't, say so — and optionally flag the gap for the research queue.

---

## How to Query Knowledge

### Tool Protocol

When you need stored knowledge, emit this JSON block in your response:

```json
{"tool": "query_knowledge", "section": "<section_name>", "question": "<your question>"}
```

The system will route your question to an Expert agent that owns that section. You'll receive a compressed answer you can use in your response.

### Available Sections

Run this to discover what sections exist:

```python
from akms.config import load_config
from akms.knowledge import HybridGraph

graph = HybridGraph(load_config().knowledge)
print(graph.list_sections())
```

Or check `knowledge/graph/` — each subdirectory is a section.

### When to Query vs. Answer Directly

| Situation | Action |
|---|---|
| Question about a domain topic (e.g., "How does Raft work?") | **Query the graph** — `query_knowledge("distributed-systems", "How does Raft work?")` |
| General coding task (e.g., "Add a unit test") | **Answer directly** — no graph lookup needed |
| Question about this project's architecture | **Check `how-this-works.md`** and the `wiki/` directory |
| Question you're not sure about | **Query the graph first**, then supplement with your own knowledge if the graph has gaps |

### Referencing Nodes

When referencing knowledge from the graph, use this format:

```
graph:section-name/node-id
```

Examples:
- `graph:distributed-systems/cap-theorem`
- `graph:machine-learning/transformers`

This lets the user trace your claims back to the stored knowledge.

---

## How to Add Knowledge

### Option 1: Ingest a document (preferred)

```bash
akms ingest path/to/document.md
```

The Librarian agent reads the document, chunks it by heading, classifies each chunk, and creates graph nodes automatically.

### Option 2: Add a node via Python API

```python
from akms.config import load_config
from akms.knowledge import HybridGraph

graph = HybridGraph(load_config().knowledge)
graph.add_node(
    section="section-name",
    node_id="node-id",
    title="Human-Readable Title",
    content="The actual knowledge content...",
    tags=["tag1", "tag2"],
    confidence=0.9,
)
```

### Option 3: Drop a markdown file manually

Create a file at `knowledge/graph/<section>/<node-id>.md` with this format:

```markdown
---
id: node-id
section: section-name
created: 2026-05-10
tags: [tag1, tag2]
confidence: 0.9
sources: []
---

# Title

Content goes here.

## Connections
- [[other-node-id]]
```

Then sync the wikilinks to the SQLite database:

```python
graph.sync_links()
```

---

## Conventions You Must Follow

### Naming

- **Sections** use `kebab-case`: `distributed-systems`, `machine-learning`
- **Node IDs** use `kebab-case`: `cap-theorem`, `raft-consensus`
- `distributed-systems` and `distributed_systems` are **different sections** — stick with kebab-case

### Wikilinks

Use `[[node-id]]` syntax to create graph edges between nodes:

```markdown
This relates to [[consensus]] and [[leader-election]].
```

These are parsed and stored as edges in the SQLite database.

### Confidence Scores

Every node has a `confidence` field (0.0 to 1.0):

| Score | Meaning |
|---|---|
| 0.9–1.0 | Verified, well-sourced fact |
| 0.7–0.9 | High confidence, may need verification |
| 0.5–0.7 | Reasonable but uncertain |
| < 0.5 | Speculative, needs research |

When adding knowledge, set confidence honestly. When using knowledge, note low-confidence nodes in your response.

### Archive, Don't Delete

Never delete a node directly. Use the Librarian's archive function:

```python
librarian.archive_node("section", "node-id", "Reason for archival", graph)
```

This moves the node to `knowledge/archives/` with a reason and timestamp. History is preserved.

---

## Knowledge Graph Structure

```
knowledge/
├── graph/                          ← Live knowledge nodes
│   ├── distributed-systems/
│   │   ├── _section.md             ← Section overview (auto-created)
│   │   ├── cap-theorem.md
│   │   └── consensus.md
│   └── machine-learning/
│       └── transformers.md
├── archives/                       ← Retired nodes (with archive reason)
├── logs/                           ← JSONL conversation & token logs
├── user_overlay/                   ← User understanding scores
│   └── understanding.json
└── research_queue.md               ← Knowledge gaps to investigate
```

---

## Flagging Knowledge Gaps

If you encounter a question the graph can't answer, flag it for the research queue:

```python
librarian.add_to_research_queue(
    topic="Paxos algorithm",
    reason="Gap in distributed-systems section — user asked about it",
    queue_path="knowledge/research_queue.md",
)
```

Or tell the user: *"This isn't in the knowledge graph yet. I'd recommend adding it via `akms ingest` or flagging it in `knowledge/research_queue.md`."*

---

## What NOT to Do

1. **Don't bypass the orchestrator** — always use `query_knowledge` or `orchestrator.query_expert()` to get knowledge. Don't read graph files directly and pretend it's an expert answer.

2. **Don't mutate Expert history** — Expert agents use fork/rollback. Each Q&A is a throwaway branch. Never try to persist Expert conversation state.

3. **Don't hardcode provider assumptions** — AKMS is provider-agnostic. Don't assume Claude, GPT, or any specific model. The user configures this in `akms_config.yaml`.

4. **Don't skip the graph for domain questions** — even if you "know" the answer, check the graph. The stored knowledge may have project-specific context, confidence scores, or connections you'd miss.

5. **Don't delete nodes** — archive them instead (see above).

6. **Don't ignore low-confidence nodes** — mention them but flag the uncertainty.

---

## Quick Reference

| Task | Command / Code |
|---|---|
| List sections | `graph.list_sections()` |
| List nodes in a section | `graph.list_nodes("section-name")` |
| Get a node | `graph.get_node("section", "node-id")` |
| Search the graph | `graph.search("query", top_k=5)` |
| Add a node | `graph.add_node(section=..., node_id=..., title=..., content=..., tags=..., confidence=...)` |
| Query an expert | `orchestrator.query_expert("section", "question")` |
| Ingest a document | `akms ingest file.md` |
| Check broken links | `librarian.check_consistency(graph)` |
| Archive a node | `librarian.archive_node("section", "node-id", "reason", graph)` |
| Sync wikilinks to DB | `graph.sync_links()` |
| Check budget | `akms budget` |
| View research queue | `akms research` |

---

## For Agent/IDE Developers

If you're building an integration for a new agent or IDE, extend `GenericWrapper`:

```python
from akms.integrations.generic import GenericWrapper

class MyAgentWrapper(GenericWrapper):
    def __init__(self, orchestrator):
        super().__init__(
            orchestrator=orchestrator,
            extra_system="Your agent-specific instructions here."
        )
```

This automatically injects the AKMS system prompt (available sections, tool protocol) into every conversation. See `src/akms/integrations/` for examples (Claude Code, Codex, OpenCode).
