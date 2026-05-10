# Agent Knowledge Management System (AKMS)

A Python library that gives AI agents **persistent memory**. Every conversation is logged, summarized, and stored in a knowledge graph. The next session starts smarter.

Works with Claude, GPT-4, Gemini, DeepSeek, or local Ollama models — swap providers without changing code.

---

## Quick Start (3 steps)

### 1. Install

```bash
pip install -e .
```

### 2. Create `akms_config.yaml`

You only need **one** API key to get started. Here's the minimal config with Claude:

```yaml
providers:
  claude:
    api_key: "${CLAUDE_API_KEY}"
    models:
      - claude-sonnet-4-6

agent_assignments:
  executor:   { provider: claude, model: claude-sonnet-4-6 }
  expert:     { provider: claude, model: claude-sonnet-4-6 }
  librarian:  { provider: claude, model: claude-sonnet-4-6 }
  council:    { provider: claude, model: claude-sonnet-4-6 }

budget:
  daily_limit_usd: 5.00
  track_tokens: true
  token_log_path: "knowledge/logs/token_usage.json"

knowledge:
  graph_dir: "knowledge/graph"
  archives_dir: "knowledge/archives"
  user_overlay_dir: "knowledge/user_overlay"
  logs_dir: "knowledge/logs"
  db_path: "knowledge/akms.db"
  checkpoints_db_path: "knowledge/checkpoints.db"
```

Set your API key in the shell:

```bash
export CLAUDE_API_KEY="sk-ant-..."
```

### 3. Initialize and chat

```bash
akms init    # creates the knowledge/ directory
akms chat    # start talking
```

The knowledge graph is empty at first. Feed it by ingesting documents:

```bash
akms ingest my-notes.md
akms ingest research-paper.pdf.txt
```

---

## Table of Contents

- [How It Works](#how-it-works)
- [CLI Reference](#cli-reference)
- [Knowledge Graph](#knowledge-graph)
- [The Three Agents](#the-three-agents)
- [Configuration Reference](#configuration-reference)
- [Provider Support](#provider-support)
- [Python API](#python-api)
- [Budget & Token Tracking](#budget--token-tracking)
- [Project Structure](#project-structure)

---

## How It Works

```
You ──► akms chat ──► Executor
                         │
              calls query_knowledge
                         │
                      Expert Agent
                  (reads one section,
                   answers, discards
                   conversation fork)
                         │
                    answer back
                         │
                      Executor
                  (continues response)

After session:
  Librarian reads logs ──► updates knowledge graph
```

1. You chat with the **Executor** agent
2. When the Executor needs stored knowledge, it calls `query_knowledge(section, question)` automatically
3. An **Expert** agent wakes up, reads its section, answers in compressed form, then discards the conversation (fork/rollback — no context bloat)
4. After sessions, the **Librarian** reads logs and adds new nodes to the graph
5. Every session leaves the graph richer

---

## CLI Reference

### `akms init`

Set up the knowledge directory. Run once before anything else.

```bash
akms init
```

Creates `knowledge/graph/`, `knowledge/logs/`, `knowledge/archives/`, `knowledge/research_queue.md`.

---

### `akms chat`

Start an interactive chat session. The Executor agent has access to your full knowledge graph.

```bash
akms chat
```

```
AKMS Chat (executor/claude-sonnet-4-6) — type 'quit' to exit

You> What does CAP theorem say about our database design?
Assistant> Based on the knowledge graph, your system is an AP design...

You> quit
Goodbye.
```

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

Supports markdown and plain text files.

---

### `akms status`

Show configured providers, agent assignments, and budget settings.

```bash
akms status
```

```
AKMS v0.1.0

Configured providers:
  claude: key=✓  models=['claude-sonnet-4-6']  (loaded)

Agent assignments:
  executor: claude/claude-sonnet-4-6
  expert:   claude/claude-sonnet-4-6

Budget:
  Daily limit: $5.00
  Token tracking: True
```

---

### `akms budget`

Show today's token usage and cost.

```bash
akms budget
```

```
Today's usage: 12,450 tokens  $0.0312

  claude: $0.0312
```

---

### `akms research`

Show the research queue — knowledge gaps the Librarian flagged.

```bash
akms research
```

```
## Pending (Awaiting Approval)
- [ ] "Raft consensus" — gap in distributed-systems section

## Completed
- [x] "Paxos algorithm" — integrated 2026-05-08, 3 nodes created
```

To approve a topic, edit `knowledge/research_queue.md` and change `- [ ]` to `- [x]`.

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
created: 2026-05-10
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

`[[wikilinks]]` create graph edges between nodes.

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

### Searching

```python
from akms.config import load_config
from akms.knowledge import HybridGraph

graph = HybridGraph(load_config().knowledge)
for node, score in graph.search("consensus algorithms", top_k=5):
    print(f"[{score:.1f}] {node['title']} ({node['section']})")
```

---

## The Three Agents

### Executor — the agent you talk to

Receives your questions, decides when to query experts, builds the final response.

Uses this tool call internally (you don't need to write it):
```json
{"tool": "query_knowledge", "section": "distributed-systems", "question": "how does Raft handle leader election?"}
```

### Expert — domain knowledge retrieval

One Expert per knowledge section. Each Expert answers from its section in compressed form:

```
Raft: leader-based. One leader elected per term. Handles failures via heartbeat timeout.
See: graph:distributed-systems/raft, graph:distributed-systems/consensus
Confidence: 0.9
```

Experts use **fork/rollback**: each Q&A is a throwaway conversation branch. The Expert's home state stays clean — no accumulated context drift across queries.

### Librarian — knowledge curation

Runs after sessions or when you call `akms ingest`. Reads logs and documents, extracts structured knowledge, adds nodes to the graph, and flags gaps for the research queue.

---

## Configuration Reference

### Minimal (Claude only)

```yaml
providers:
  claude:
    api_key: "${CLAUDE_API_KEY}"
    models:
      - claude-sonnet-4-6

agent_assignments:
  executor:   { provider: claude, model: claude-sonnet-4-6 }
  expert:     { provider: claude, model: claude-sonnet-4-6 }
  librarian:  { provider: claude, model: claude-sonnet-4-6 }
  council:    { provider: claude, model: claude-sonnet-4-6 }

budget:
  daily_limit_usd: 5.00
  track_tokens: true
  token_log_path: "knowledge/logs/token_usage.json"

knowledge:
  graph_dir: "knowledge/graph"
  archives_dir: "knowledge/archives"
  user_overlay_dir: "knowledge/user_overlay"
  logs_dir: "knowledge/logs"
  db_path: "knowledge/akms.db"
  checkpoints_db_path: "knowledge/checkpoints.db"
```

### Full (multiple providers, different agents)

Use different providers for different agent roles — e.g., cheap/fast for Experts, powerful for Executor:

```yaml
providers:
  claude:
    api_key: "${CLAUDE_API_KEY}"
    models: [claude-sonnet-4-6, claude-opus-4-7]

  openai:
    api_key: "${OPENAI_API_KEY}"
    models: [gpt-4o]

  gemini:
    api_key: "${GEMINI_API_KEY}"
    models: [gemini-2.5-pro]

  deepseek:
    api_key: "${DEEPSEEK_API_KEY}"
    models: [deepseek-chat]

  ollama:
    base_url: "http://localhost:11434"   # no API key
    models: [llama3, mistral]

agent_assignments:
  executor:   { provider: claude, model: claude-opus-4-7 }
  expert:     { provider: openai, model: gpt-4o }
  librarian:  { provider: claude, model: claude-sonnet-4-6 }
  council:    { provider: openai, model: gpt-4o }

budget:
  daily_limit_usd: 10.00
  per_query_warn_usd: 0.50
  track_tokens: true
  token_log_path: "knowledge/logs/token_usage.json"

knowledge:
  graph_dir: "knowledge/graph"
  archives_dir: "knowledge/archives"
  user_overlay_dir: "knowledge/user_overlay"
  logs_dir: "knowledge/logs"
  db_path: "knowledge/akms.db"
  checkpoints_db_path: "knowledge/checkpoints.db"
```

API keys are never stored in the file — always use environment variables:

```bash
export CLAUDE_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
```

---

## Provider Support

| Provider | Needs | Notes |
|---|---|---|
| Claude | `pip install -e .` | Default, included |
| OpenAI / Azure | `pip install -e .` | Default, included |
| DeepSeek | `pip install -e .` | OpenAI-compatible |
| Google Gemini | `pip install -e ".[gemini]"` | |
| Ollama (local) | `pip install -e ".[ollama]"` + run Ollama | No API key |

Switching providers: change `agent_assignments` in the config, no code changes needed.

---

## Python API

### Minimal setup

```python
from akms.config import load_config
from akms.providers.registry import build_default_registry
from akms.knowledge import HybridGraph
from akms.checkpoints import CheckpointStore
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

### Run the Executor

```python
from akms.agents.executor import ExecutorAgent

provider = registry.create_from_config("claude", config.providers["claude"])
executor = ExecutorAgent(
    provider=provider,
    model=config.agent_assignments["executor"].model,
    config=config,
)
response = executor.run("Explain CAP theorem's impact on our DB choice", orchestrator=orchestrator)
print(response)
```

### Use the Librarian

```python
from akms.agents.librarian import LibrarianAgent

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

# Get a synthesized recommendation
result = council.convene(
    task="Should we use eventual or strong consistency for user profiles?",
    context="10M users, rare writes, very frequent reads"
)
print(result)

# Get all 5 perspectives (Advocate, Critic, Historian, Innovator, Synthesizer)
detailed = council.convene_detailed(task="...", context="...")
for role, perspective in detailed.items():
    print(f"\n## {role}\n{perspective}")
```

---

## Budget & Token Tracking

```python
from akms.core.budget import BudgetTracker

tracker = BudgetTracker()
tracker.record_usage("claude", "sonnet", tokens_in=500, tokens_out=200, cost_usd=0.012)

print(tracker.daily_total_usd())     # e.g. 0.012
print(tracker.is_over_limit(5.0))    # True if >= $5
print(tracker.summary())             # breakdown by provider
```

```python
from akms.logging import TokenTracker

tt = TokenTracker("knowledge/logs/token_usage.json")
tt.log("claude", "sonnet", tokens=700, cost_usd=0.014)

today = tt.load_today()
```

CLI shortcut: `akms budget`

---

## Project Structure

```
akms/
├── akms_config.yaml.example     ← reference config (copy to akms_config.yaml)
├── src/akms/
│   ├── cli.py                   ← akms command
│   ├── config.py                ← config loading
│   ├── agents/
│   │   ├── base.py              ← BaseAgent
│   │   ├── executor.py          ← main chat agent
│   │   ├── expert.py            ← knowledge retrieval (fork/rollback)
│   │   ├── librarian.py         ← knowledge curation
│   │   └── council.py           ← 5-role deliberation
│   ├── core/
│   │   ├── message.py           ← provider-agnostic message type
│   │   ├── budget.py            ← cost tracking
│   │   └── orchestrator.py      ← agent coordination
│   ├── knowledge/
│   │   ├── wiki.py              ← markdown layer
│   │   ├── db.py                ← SQLite layer
│   │   ├── graph.py             ← unified interface
│   │   └── search.py            ← keyword search
│   ├── checkpoints/
│   │   ├── store.py             ← save/load conversations
│   │   └── fork.py              ← fork/rollback for Expert agents
│   ├── providers/               ← claude, openai, gemini, deepseek, ollama
│   ├── integrations/
│   │   ├── generic.py           ← inject AKMS into any provider session
│   │   └── claude_code.py       ← Claude Code specific
│   └── logging/
│       ├── conversation_log.py
│       └── token_tracker.py
├── knowledge/                   ← created by akms init
└── tests/                       ← 43 tests (pytest)
```

---

## Tips

**You only need one API key.** Start with Claude or OpenAI alone — use the minimal config above and expand later.

**Start small.** Run `akms init`, ingest one document, then `akms chat`. Don't try to build a large graph before testing the flow.

**Sections are directories — pick a naming convention.** `distributed-systems` and `distributed_systems` are different sections. Stick with `kebab-case`.

**Archive, don't delete.** Use `librarian.archive_node()` to mark something wrong — it moves to `knowledge/archives/` with a reason. The history is preserved.

**Keep the daily limit low while experimenting.** Set `daily_limit_usd: 1.00` until you know your usage patterns.
