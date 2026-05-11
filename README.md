# Agent Knowledge Management System (AKMS)

A Python library that gives AI agents **persistent memory**. Knowledge is stored in a graph that grows across sessions. Any agent that can run a shell command can query it — no wrappers, no per-IDE integration code.

Works with Claude, GPT-4, Gemini, DeepSeek, or local Ollama models — swap providers without changing code.

---

## Quick Start (3 steps)

### 1. Install

```bash
pip install -e .
```

### 2. Create `akms_config.yaml`

You only need **one** API key to get started:

```yaml
providers:
  claude:
    api_key: "${CLAUDE_API_KEY}"
    models:
      - claude-sonnet-4-6

agent_assignments:
  expert:     { provider: claude, model: claude-sonnet-4-6 }
  librarian:  { provider: claude, model: claude-sonnet-4-6 }

knowledge:
  graph_dir: "knowledge/graph"
  archives_dir: "knowledge/archives"
  logs_dir: "knowledge/logs"
  db_path: "knowledge/akms.db"
  checkpoints_db_path: "knowledge/checkpoints.db"
```

```bash
export CLAUDE_API_KEY="sk-ant-..."
```

### 3. Initialize and start querying

```bash
akms init                          # create the knowledge/ directory
akms ingest my-notes.md            # feed documents to the Librarian
akms search "consensus algorithms" # search the graph
akms ask "distributed-systems" "How does Raft work?"
```

---

## Table of Contents

- [How It Works](#how-it-works)
- [CLI Reference](#cli-reference)
- [Knowledge Graph](#knowledge-graph)
- [The Three Roles](#the-three-roles)
- [Configuration Reference](#configuration-reference)
- [Provider Support](#provider-support)
- [Python API](#python-api)
- [Dynamic Expert Scaling](#dynamic-expert-scaling)
- [Project Structure](#project-structure)

---

## How It Works

```
Your IDE agent (Agent 1)
   │
   ├── akms search "query"      ──► knowledge graph (SQLite index)
   ├── akms ask "section" "q"   ──► Expert agent (pre-loaded section)
   │                                   │
   │                           fork/rollback per query
   │                           (home state never mutated)
   │
   └── akms ingest doc.md       ──► Librarian agent ──► knowledge graph
```

1. **Agent 1** (your IDE agent) reads `agents.md` and calls `akms` commands as shell skills
2. **Expert agents** pre-load knowledge sections into memory. Each query from Agent 1 creates a throwaway fork — answered and discarded. No context drift.
3. **The Librarian** (Agent 3) reads documents and conversation logs, adds nodes to the graph, uses the Council internally to reason about graph structure
4. Every session leaves the graph richer for the next

---

## CLI Reference

### `akms init`

Set up the knowledge directory. Run once before anything else.

```bash
akms init
```

Creates `knowledge/graph/`, `knowledge/logs/`, `knowledge/archives/`, `knowledge/research_queue.md`.

---

### `akms ingest <file>`

Feed a document into the knowledge graph. The Librarian reads it, chunks by heading, and creates nodes.

```bash
akms ingest papers/distributed-systems-primer.md
```

```
Ingesting: papers/distributed-systems-primer.md
Done. 7 node(s) added to knowledge graph.
```

---

### `akms search <query>`

Search the knowledge graph and return ranked results.

```bash
akms search "consensus algorithms"
akms search "leader election" --top-k 5
akms search "Raft" --json
```

---

### `akms ask <section> <question>`

Route a question to the Expert agent for a section. The Expert pre-loads its section, answers via fork/rollback, and returns a compressed answer.

```bash
akms ask "distributed-systems" "How does Raft handle leader election?"
```

---

### `akms get <section/node-id>`

Get the full content of a specific node.

```bash
akms get distributed-systems/raft
akms get distributed-systems/raft --json
```

---

### `akms sections`

List all available knowledge sections and node counts.

```bash
akms sections
akms sections --json
```

---

### `akms archive <section> <node-id> <reason>`

Archive a node — moves it to `knowledge/archives/` with proper metadata. Never delete nodes directly.

```bash
akms archive "distributed-systems" "old-raft-notes" "Superseded by raft-consensus node"
```

---

### `akms check`

Find broken wikilinks across the knowledge graph.

```bash
akms check
akms check --json
```

---

### `akms council <task> [context]`

Run a 5-role Council deliberation (Advocate, Critic, Historian, Innovator, Synthesizer) and return a recommendation.

```bash
akms council "Should we use eventual or strong consistency?" "10M users, rare writes"
akms council "task" "context" --detailed   # show all 5 perspectives
akms council "task" "context" --json
```

---

### `akms status`

Show configured providers and agent assignments.

```bash
akms status
```

---

### `akms research`

Show the research queue — knowledge gaps flagged by the Librarian.

```bash
akms research
```

---

## Knowledge Graph

The graph lives in `knowledge/graph/` — a directory tree of markdown files, backed by SQLite for search.

### Structure

```
knowledge/graph/
├── distributed-systems/
│   ├── _section.md          ← section overview
│   ├── cap-theorem.md
│   └── consensus.md
└── machine-learning/
    └── transformers.md
```

### Node format

```markdown
---
id: cap-theorem
section: distributed-systems
created: 2026-05-11
tags: [consistency, availability, partition-tolerance]
confidence: 0.92
sources: []
---

# CAP Theorem

The CAP theorem states that a distributed system can guarantee at most two of:
Consistency, Availability, Partition tolerance.

## Connections
- [[consensus]] — CAP defines the tradeoff space
```

`[[wikilinks]]` create graph edges between nodes. Markdown is the source of truth — SQLite is a derived index for fast search and routing.

### Adding nodes manually

Drop a markdown file into `knowledge/graph/<section>/<node-id>.md` following the format above. Then sync the links:

```bash
python3 -c "
import sys; sys.path.insert(0,'src')
from akms.config import load_config
from akms.knowledge import HybridGraph
g = HybridGraph(load_config().knowledge)
print(f'Synced {g.sync_links()} wikilinks')
"
```

---

## The Three Roles

### Agent 1 — your IDE agent

Your Claude Code session, Codex, or any agent that can run shell commands. It reads `agents.md` to learn the available `akms` commands and calls them as skills. AKMS provides no dedicated "chat" agent — your IDE is already Agent 1.

### Agent 2 — Expert (knowledge retrieval)

One Expert per knowledge section. Experts pre-load their section into a home state checkpoint. Each query from Agent 1 creates a throwaway conversation fork — answered and discarded. The home state is never mutated.

```
Expert home state:  [system prompt + all section nodes]  ← checkpoint
                              │
         query arrives ──► fork ──► answer ──► discard fork
                              │
                    home state unchanged
```

This is the fork/rollback pattern — think of the home state as a `--resume` point. No context drift across queries.

### Agent 3 — Librarian (knowledge curation)

Runs when you call `akms ingest` or after sessions via `ingest_log()`. Reads documents, extracts structured knowledge, and adds nodes. Uses the Council internally to reason about graph structure before writing — the Council is not exposed as a top-level CLI command.

---

## Configuration Reference

### Minimal (one provider)

```yaml
providers:
  claude:
    api_key: "${CLAUDE_API_KEY}"
    models:
      - claude-sonnet-4-6

agent_assignments:
  expert:     { provider: claude, model: claude-sonnet-4-6 }
  librarian:  { provider: claude, model: claude-sonnet-4-6 }

knowledge:
  graph_dir: "knowledge/graph"
  archives_dir: "knowledge/archives"
  logs_dir: "knowledge/logs"
  db_path: "knowledge/akms.db"
  checkpoints_db_path: "knowledge/checkpoints.db"
```

### Multi-provider (different agents on different models)

```yaml
providers:
  claude:
    api_key: "${CLAUDE_API_KEY}"
    models: [claude-sonnet-4-6, claude-opus-4-7]

  openai:
    api_key: "${OPENAI_API_KEY}"
    models: [gpt-4o]

  ollama:
    base_url: "http://localhost:11434"
    models: [llama3, mistral]

agent_assignments:
  expert:     { provider: openai, model: gpt-4o }
  librarian:  { provider: claude, model: claude-sonnet-4-6 }

expert:
  token_threshold: 50000   # sections larger than this are split into chunk experts

knowledge:
  graph_dir: "knowledge/graph"
  archives_dir: "knowledge/archives"
  logs_dir: "knowledge/logs"
  db_path: "knowledge/akms.db"
  checkpoints_db_path: "knowledge/checkpoints.db"
```

API keys are never stored in the file — always use environment variables.

---

## Provider Support

| Provider | Needs | Notes |
|---|---|---|
| Claude | `pip install -e .` | Default, included |
| OpenAI / Azure | `pip install -e .` | Default, included |
| DeepSeek | `pip install -e .` | OpenAI-compatible |
| Google Gemini | `pip install -e ".[gemini]"` | |
| Ollama (local) | `pip install -e ".[ollama]"` + run Ollama | No API key |

Switching providers: change `agent_assignments` in the config. No code changes needed.

---

## Python API

### Minimal setup

```python
from akms.config import load_config
from akms.providers.registry import build_default_registry
from akms.knowledge import HybridGraph
from akms.checkpoints.store import CheckpointStore
from akms.core.orchestrator import Orchestrator

config = load_config()
registry = build_default_registry()
graph = HybridGraph(config.knowledge)
graph.init_graph_dirs()
store = CheckpointStore(config.knowledge.checkpoints_db_path)
store.init_db()

orchestrator = Orchestrator(config=config, registry=registry, graph=graph, checkpoint_store=store)
```

### Add a knowledge node

```python
graph.add_node(
    section="distributed-systems",
    node_id="raft",
    title="Raft Consensus",
    content="Raft is a consensus algorithm designed for understandability...",
    tags=["consensus", "leader-election"],
    confidence=0.95,
)
```

### Search the graph

```python
results = graph.search("leader election", top_k=5)
for node, score in results:
    print(f"[{score:.1f}] {node['title']}")
```

### Query an Expert

```python
answer = orchestrator.query_expert(
    section="distributed-systems",
    question="What are the differences between Raft and Paxos?"
)
print(answer)
```

### Use the Librarian

```python
from akms.agents.librarian import LibrarianAgent

provider = registry.create_from_config("claude", config.providers["claude"])
librarian = LibrarianAgent(provider=provider, model="claude-sonnet-4-6", config=config)

# Ingest a document
librarian.digest_document("papers/raft.md", graph)

# Find broken wikilinks
for issue in librarian.check_consistency(graph):
    print(f"Broken: [[{issue['broken_link']}]] in {issue['node_id']}")

# Archive a wrong node
librarian.archive_node("distributed-systems", "old-explanation", "Incorrect claim", graph)
```

### Use the Council (5-role deliberation)

```python
from akms.agents.council import CouncilAgent

council = CouncilAgent(provider=provider, model="claude-sonnet-4-6", config=config)

result = council.convene(
    task="Should we use eventual or strong consistency for user profiles?",
    context="10M users, rare writes, very frequent reads"
)
print(result)

# All 5 perspectives (Advocate, Critic, Historian, Innovator, Synthesizer)
detailed = council.convene_detailed(task="...", context="...")
for role, perspective in detailed.items():
    print(f"\n## {role}\n{perspective}")
```

---

## Dynamic Expert Scaling

For sections exceeding `expert.token_threshold` tokens, AKMS automatically splits the section into chunk experts:

```yaml
expert:
  token_threshold: 50000
```

- Single sections: pooled under `"section-name"`
- Split sections: `"section-name:0"`, `"section-name:1"`, ...
- Sentinel key `"section-name:__split__"` stores the chunk list
- Query routing: question is tokenized, scored against each chunk by keyword overlap, top-2 chunks are queried and answers concatenated

```python
# Force-recreate an expert (evicts cached instance)
orc.spawn_expert("distributed-systems")

# Reload only if already cached
orc.refresh_expert("distributed-systems")
```

---

## Project Structure

```
akms/
├── akms_config.yaml.example     ← reference config
├── agents.md                    ← agent instructions (read this to use AKMS)
├── how-this-works.md            ← architecture deep-dive with diagrams
├── src/akms/
│   ├── cli.py                   ← akms command entry point
│   ├── config.py                ← AKMSConfig, KnowledgeConfig, ExpertConfig
│   ├── agents/
│   │   ├── base.py              ← BaseAgent (send, ask, logging)
│   │   ├── expert.py            ← Expert agent (fork/rollback, load_section)
│   │   ├── librarian.py         ← Librarian agent (ingest, check, archive)
│   │   └── council.py           ← 5-role deliberation (Librarian's internal tool)
│   ├── core/
│   │   ├── message.py           ← provider-agnostic message types
│   │   └── orchestrator.py      ← expert pool, dynamic splitting, query routing
│   ├── knowledge/
│   │   ├── wiki.py              ← markdown layer (source of truth)
│   │   ├── db.py                ← SQLite layer (derived index)
│   │   ├── graph.py             ← unified HybridGraph facade
│   │   └── search.py            ← keyword search
│   ├── checkpoints/
│   │   ├── store.py             ← checkpoint persistence (SQLite)
│   │   └── fork.py              ← fork/rollback helpers
│   ├── providers/               ← claude, openai, gemini, deepseek, ollama
│   └── logging/
│       └── conversation_log.py  ← JSONL conversation logger
├── knowledge/                   ← created by akms init
└── tests/                       ← pytest suite
```

---

## Tips

**You only need one API key.** Start with Claude or OpenAI alone and expand later.

**Start small.** Run `akms init`, ingest one document, then `akms search` or `akms ask`. Don't build a large graph before testing the flow.

**Sections are directories — pick a naming convention.** `distributed-systems` and `distributed_systems` are different sections. Stick with `kebab-case`.

**Archive, don't delete.** Use `akms archive` or `librarian.archive_node()` — the node moves to `knowledge/archives/` with a reason and timestamp. History is preserved.

**Markdown is the source of truth.** The SQLite database is a derived index — always reconstructable from the markdown files. Commit the `knowledge/graph/` directory to git.
