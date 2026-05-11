# AKMS — Agent Instructions

> **Read this file first.** It tells you how to work with this project's knowledge graph.

---

## What is this project?

AKMS (Agent Knowledge Management System) gives AI agents **persistent memory** via a knowledge graph. Knowledge is stored as markdown files backed by SQLite — human-readable, git-friendly, and searchable.

You are operating inside a project that uses AKMS. There is a `knowledge/` directory containing structured knowledge you can query, and a set of CLI commands you should use before answering domain-specific questions.

---

## Your #1 Rule

**Before answering a question about a domain topic, check the knowledge graph first.**

Do not guess. Do not hallucinate. If the knowledge graph has relevant nodes, use them. If it doesn't, say so — and optionally flag the gap via `akms research`.

---

## How to Use AKMS — CLI Skills

AKMS exposes all operations as CLI commands. **You don't need any Python integration, wrappers, or plugins.** If you can run a shell command, you can use AKMS.

### Core Commands

| Command | What it does | When to use it |
|---|---|---|
| `akms search "query"` | Search the knowledge graph for relevant nodes | Before answering any domain question |
| `akms ask "section" "question"` | Query the Expert agent for a specific section | When you need a detailed, contextual answer from stored knowledge |
| `akms get section/node-id` | Get the full content of a specific node | When you need the exact content of a known node |
| `akms sections` | List all available knowledge sections | To discover what knowledge exists |
| `akms ingest file.md` | Feed a document into the graph via the Librarian | When the user provides new material to learn from |
| `akms archive "section" "node-id" "reason"` | Archive a node (move to archives, never delete) | When a node is wrong or outdated |
| `akms check` | Find broken wikilinks in the graph | Maintenance |
| `akms init` | Set up the `knowledge/` directory structure | First-time setup only |
| `akms status` | Show providers and agent assignments | Diagnostics |
| `akms research` | Show the research queue (knowledge gaps) | To see what's missing |

### Decision Table: When to Query vs. Answer Directly

| Situation | Action |
|---|---|
| Question about a domain topic (e.g., "How does Raft work?") | **Run `akms search "Raft consensus"`** or **`akms ask "distributed-systems" "How does Raft work?"`** |
| General coding task (e.g., "Add a unit test") | **Answer directly** — no graph lookup needed |
| Question about this project's architecture | **Check `how-this-works.md`** and the `wiki/` directory |
| Question you're not sure about | **Run `akms search` first**, then supplement with your own knowledge if the graph has gaps |

### Referencing Nodes

When referencing knowledge from the graph in your responses, use this format:

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

### Option 2: Drop a markdown file manually

Create a file at `knowledge/graph/<section>/<node-id>.md` with this format:

```markdown
---
id: node-id
section: section-name
created: 2026-05-11
tags: [tag1, tag2]
confidence: 0.9
sources: []
---

# Title

Content goes here.

## Connections
- [[other-node-id]]
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

Never delete a node directly. Use:

```bash
akms archive "section" "node-id" "Reason for archival"
```

This moves the node to `knowledge/archives/` with proper frontmatter (`archived`, `archive_reason`, `original_section`). History is preserved.

---

## Knowledge Graph Structure

```
knowledge/
├── graph/                          ← Live knowledge nodes (source of truth)
│   ├── distributed-systems/
│   │   ├── _section.md             ← Section overview (auto-created)
│   │   ├── cap-theorem.md
│   │   └── consensus.md
│   └── machine-learning/
│       └── transformers.md
├── archives/                       ← Retired nodes (with archive reason + timestamp)
├── logs/                           ← JSONL conversation logs (Librarian reads these)
└── research_queue.md               ← Knowledge gaps to investigate
```

---

## Flagging Knowledge Gaps

If you encounter a question the graph can't answer, tell the user:

*"This isn't in the knowledge graph yet. I'd recommend adding it via `akms ingest` or flagging it in `knowledge/research_queue.md`."*

---

## What NOT to Do

1. **Don't skip the graph for domain questions** — even if you "know" the answer, run `akms search` first. The stored knowledge may have project-specific context, confidence scores, or connections you'd miss.

2. **Don't hardcode provider assumptions** — AKMS is provider-agnostic. Don't assume Claude, GPT, or any specific model. The user configures this in `akms_config.yaml`.

3. **Don't delete nodes** — archive them instead (see above).

4. **Don't ignore low-confidence nodes** — mention them but flag the uncertainty.

5. **Don't read graph files directly when an expert query would be better** — `akms ask` gives you a synthesized answer from the Expert agent; raw file reading gives you unprocessed markdown.

---

## Quick Reference

```bash
# Discovery
akms sections                          # What sections exist?
akms search "consensus algorithms"     # Find relevant nodes

# Retrieval
akms ask "distributed-systems" "How does Raft handle leader election?"
akms get distributed-systems/raft      # Full node content

# Knowledge management
akms ingest paper.md                   # Feed a document to the Librarian
akms archive "section" "node" "reason" # Retire a node
akms check                             # Find broken wikilinks

# Diagnostics
akms status                            # Providers, assignments
akms research                          # Knowledge gaps queue
```
