# Agent Knowledge Management System (AKMS)

A **provider-agnostic** Python library that gives AI agents a persistent, searchable knowledge graph. AKMS acts as middleware — wrap your existing AI tool (Claude, GPT-4, Gemini, local models) and it automatically logs conversations, builds a knowledge base, and lets specialized "Expert" agents answer questions from stored knowledge.

---

## Table of Contents

- [What AKMS Does](#what-akms-does)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [CLI Reference](#cli-reference)
- [How It Works](#how-it-works)
- [Knowledge Graph](#knowledge-graph)
- [The Three Agents](#the-three-agents)
- [Provider Support](#provider-support)
- [Python API](#python-api)
- [Budget & Token Tracking](#budget--token-tracking)
- [Project Structure](#project-structure)

---

## What AKMS Does

| Without AKMS | With AKMS |
|---|---|
| Each conversation starts from scratch | Knowledge accumulates across sessions |
| You re-explain context every time | Expert agents answer from a persistent graph |
| No record of what the AI learned | Full conversation logs + provenance tracking |
| Locked to one provider | Swap Claude ↔ GPT-4 ↔ Gemini ↔ Ollama freely |

---

## Quick Start

```bash
# 1. Install
pip install -e .

# 2. Copy and fill in the config
cp akms_config.yaml.example akms_config.yaml
# Edit akms_config.yaml — add your API keys

# 3. Initialize the knowledge graph directory
akms init

# 4. Start chatting
akms chat
```

That's it. Every conversation is logged and fed into the knowledge graph automatically.

---

## Installation

**Requirements:** Python 3.11+

```bash
# From source (recommended)
git clone https://github.com/your-org/akms
cd akms
pip install -e .

# With optional provider extras
pip install -e ".[gemini]"     # Google Gemini support
pip install -e ".[ollama]"     # Local Ollama models
```

Core dependencies (`anthropic`, `openai`, `pyyaml`, `click`) are installed automatically.

---

## Configuration

Copy the example config and edit it:

```bash
cp akms_config.yaml.example akms_config.yaml
```

### Full Config Reference

```yaml
providers:
  claude:
    api_key: "${CLAUDE_API_KEY}"    # reads from environment variable
    models:
      - claude-sonnet-4-6
      - claude-opus-4-7

  openai:
    api_key: "${OPENAI_API_KEY}"
    models:
      - gpt-4o

  gemini:
    api_key: "${GEMINI_API_KEY}"
    models:
      - gemini-2.5-pro

  deepseek:
    api_key: "${DEEPSEEK_API_KEY}"
    models:
      - deepseek-chat

  ollama:
    base_url: "http://localhost:11434"   # no API key needed
    models:
      - llama3
      - mistral

# Which provider+model each agent role uses
agent_assignments:
  executor:               # the main chat agent
    provider: claude
    model: claude-sonnet-4-6
  expert:                 # knowledge-retrieval agents
    provider: openai
    model: gpt-4o
  librarian:              # knowledge-curation agent
    provider: claude
    model: claude-sonnet-4-6
  council:                # 5-role deliberation council
    provider: openai
    model: gpt-4o

budget:
  daily_limit_usd: 5.00        # hard daily cap
  per_query_warn_usd: 0.50     # warn when a single call exceeds this
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

### Using Environment Variables

API keys are never stored in the file. Set them in your shell:

```bash
export CLAUDE_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="..."
```

Or put them in a `.env` file and source it: `source .env`

---

## CLI Reference

All commands accept `--config PATH` to point at a non-default config file.

### `akms init`

Set up the knowledge graph directory structure. Run this once before anything else.

```bash
akms init
```

Creates:
```
knowledge/
├── graph/          ← knowledge nodes go here
│   └── _index.md
├── archives/       ← archived/deprecated nodes
├── user_overlay/   ← personal learning layer
├── logs/           ← conversation + token logs
└── research_queue.md
```

---

### `akms status`

Show system status: configured providers, agent assignments, budget settings.

```bash
akms status
```

```
AKMS v0.1.0

Configured providers:
  claude: key=✓  models=['claude-sonnet-4-6']  (loaded)
  openai: key=✓  models=['gpt-4o']  (loaded)

Agent assignments:
  executor: claude/claude-sonnet-4-6
  expert: openai/gpt-4o

Budget:
  Daily limit: $5.00
  Per-query warn: $0.50
  Token tracking: True
```

---

### `akms chat`

Start an interactive chat session with the Executor agent. The agent has access to your entire knowledge graph via the `query_knowledge` tool.

```bash
akms chat
```

```
AKMS Chat (executor/claude-sonnet-4-6) — type 'quit' to exit

You> What does CAP theorem say about our database design?
Assistant: Based on the knowledge graph, your system is an AP design...

You> quit
Goodbye.
```

The agent will automatically query the knowledge graph when it needs stored facts — you don't need to prompt it to do so.

---

### `akms ingest <file>`

Feed a document (markdown, text) into the knowledge graph via the Librarian agent. The Librarian reads the document, chunks it by heading, classifies each chunk, and creates knowledge nodes.

```bash
akms ingest papers/distributed-systems-primer.md
akms ingest notes/cap-theorem-notes.txt
```

```
Ingesting: papers/distributed-systems-primer.md
Done. 7 node(s) added to knowledge graph.
```

After ingesting, those nodes are immediately available to Expert agents during chat.

---

### `akms research`

Show the current research queue — topics the Librarian has flagged as knowledge gaps awaiting your approval.

```bash
akms research
```

```
# Research Queue

## Pending (Awaiting Approval)
- [ ] "Raft consensus algorithm" — gap detected in distributed-systems section
- [ ] "CRDT data structures" — referenced in 3 nodes but no dedicated section

## Approved
- [x] "Vector clock implementations" — approved 2026-05-09

## Completed
- [x] "Paxos algorithm" — integrated 2026-05-08, 3 new nodes created
```

To approve a topic, edit `knowledge/research_queue.md` and change `- [ ]` to `- [x]` under **Approved**.

---

### `akms budget`

Show today's token usage and cost across all providers.

```bash
akms budget
```

```
Today's usage: 12,450 tokens  $0.0312

  claude: $0.0198
  openai: $0.0114
```

If you've hit the daily limit, a warning is shown.

---

## How It Works

```
You ──► akms chat ──► Executor Agent
                           │
                    ┌──────┴──────┐
                    │   needs     │
                    │  knowledge  │
                    ▼             │
              Expert Agent        │
              (reads section      │
               from graph)        │
                    │             │
                    └──────►──────┘
                           │
                    Librarian Agent
                    (runs async,
                     updates graph
                     from logs)
```

1. **You chat** with the Executor agent
2. When the Executor needs domain knowledge, it calls `query_knowledge(section, question)`
3. An **Expert agent** wakes up, reads its assigned knowledge section, answers in compressed format, then returns to sleep — conversation history discarded (fork/rollback mechanism)
4. After the session, the **Librarian** reads conversation logs, extracts insights, and updates the graph
5. Next session, the graph is richer

---

## Knowledge Graph

The graph is **dual-layer**: human-readable markdown files + a SQLite database for queries.

### Structure

```
knowledge/graph/
├── _index.md                    ← root map
├── distributed-systems/
│   ├── _section.md              ← section overview
│   ├── cap-theorem.md
│   └── consensus.md
└── machine-learning/
    ├── _section.md
    └── transformers.md
```

### Node Format

Every node is a markdown file with YAML frontmatter:

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
- [[consistency-models]] — CAP defines the tradeoff space
- [[distributed-databases]] — practical implementations
```

### Adding Knowledge Manually

You can write nodes by hand — just follow the format above and place the file in `knowledge/graph/<section>/<node-id>.md`. Then run:

```bash
python3 -c "
import sys; sys.path.insert(0,'src')
from akms.config import load_config
from akms.knowledge import HybridGraph
g = HybridGraph(load_config().knowledge)
synced = g.sync_links()
print(f'Synced {synced} wikilinks to SQLite')
"
```

### Searching the Graph

```python
from akms.config import load_config
from akms.knowledge import HybridGraph

graph = HybridGraph(load_config().knowledge)
results = graph.search("consensus algorithms", top_k=5)
for node, score in results:
    print(f"[{score:.1f}] {node['title']} ({node['section']})")
```

---

## The Three Agents

### Executor (Agent 1) — `akms chat`

The main reasoning agent. Receives user tasks, decides when to query experts, optionally convenes the 5-role council for complex decisions.

**Tool it uses:**
```json
{"tool": "query_knowledge", "section": "distributed-systems", "question": "how does Raft handle leader election?"}
```

### Expert (Agent 2) — automatic

Spawned per knowledge section. Each Expert "owns" one section and answers questions from it in compressed "caveman mode":

```
CAP applies. System = AP. Sacrifice strong consistency.
Use eventual consistency. See: graph:distributed-systems/cap,
graph:consistency-models/eventual. Confidence: 0.9
```

Experts use a **fork/rollback** mechanism — each Q&A is a throwaway conversation branch. The expert's home state is never polluted by queries.

### Librarian (Agent 3) — automatic / `akms ingest`

Runs after sessions to integrate new knowledge. Responsibilities:

| Task | How to trigger |
|---|---|
| Ingest conversation log | Automatic after chat sessions |
| Digest a document | `akms ingest <file>` |
| Check for broken wikilinks | Python API (see below) |
| Add research queue item | Python API |
| Archive incorrect node | Python API |

---

## Provider Support

| Provider | Package | Notes |
|---|---|---|
| Claude (Anthropic) | `anthropic` | Included by default |
| OpenAI / Azure | `openai` | Included by default |
| DeepSeek | `openai` | OpenAI-compatible, uses DeepSeek base URL |
| Google Gemini | `google-genai` | Install with `pip install -e ".[gemini]"` |
| Ollama (local) | `ollama` | Install with `pip install -e ".[ollama]"`, run Ollama locally |

### Switching Providers Mid-Project

Change `agent_assignments` in `akms_config.yaml` — no code changes needed:

```yaml
agent_assignments:
  executor:
    provider: ollama        # switch to local
    model: llama3
```

---

## Python API

For programmatic use beyond the CLI:

### Build the core objects

```python
from akms.config import load_config
from akms.providers.registry import build_default_registry
from akms.knowledge import HybridGraph
from akms.checkpoints import CheckpointStore
from akms.core.orchestrator import Orchestrator

config = load_config()           # reads akms_config.yaml
registry = build_default_registry()
graph = HybridGraph(config.knowledge)
graph.init_graph_dirs()
store = CheckpointStore(config.knowledge.checkpoints_db_path)
store.init_db()

orchestrator = Orchestrator(config=config, registry=registry, graph=graph, checkpoint_store=store)
```

### Add knowledge nodes directly

```python
graph.add_node(
    section="distributed-systems",
    node_id="raft",
    title="Raft Consensus",
    content="Raft is a consensus algorithm designed to be understandable...",
    tags=["consensus", "leader-election"],
    confidence=0.95,
)
```

### Search the graph

```python
results = graph.search("leader election", top_k=5)
for node, score in results:
    print(node["title"], score)
```

### Query an Expert directly

```python
answer = orchestrator.query_expert(
    section="distributed-systems",
    question="What are the main differences between Raft and Paxos?"
)
print(answer)
```

### Run the Executor programmatically

```python
from akms.agents.executor import ExecutorAgent

provider_cfg = config.providers["claude"]
provider = registry.create_from_config("claude", provider_cfg)
executor = ExecutorAgent(
    provider=provider,
    model=config.agent_assignments["executor"].model,
    config=config,
)

response = executor.run("Explain how CAP theorem affects our database choice", orchestrator=orchestrator)
print(response)
```

### Use the Librarian

```python
from akms.agents.librarian import LibrarianAgent
from pathlib import Path

librarian = LibrarianAgent(provider=provider, model="claude-sonnet-4-6", config=config)

# Digest a document
nodes_added = librarian.digest_document("papers/raft.md", graph)

# Check for broken wikilinks
issues = librarian.check_consistency(graph)
for issue in issues:
    print(f"Broken link in {issue['node_id']}: [[{issue['broken_link']}]]")

# Archive a wrong node
librarian.archive_node("distributed-systems", "old-cap-explanation", "Incorrect claim", graph)
```

### Use the Council for complex decisions

```python
from akms.agents.council import CouncilAgent

council = CouncilAgent(provider=provider, model="gpt-4o", config=config)

synthesis = council.convene(
    task="Should we use eventual consistency or strong consistency for our user profile service?",
    context="We have 10M users, writes are rare (profile updates), reads are very frequent."
)
print(synthesis)

# Get all 5 perspectives
detailed = council.convene_detailed(task="...", context="...")
for role, perspective in detailed.items():
    print(f"\n## {role}\n{perspective}")
```

---

## Budget & Token Tracking

### In-session tracking

```python
from akms.core.budget import BudgetTracker

tracker = BudgetTracker()
tracker.record_usage("claude", "sonnet", tokens_in=500, tokens_out=200, cost_usd=0.012)

print(tracker.daily_total_usd())     # today's total
print(tracker.is_over_limit(5.0))    # True if >= $5
print(tracker.summary())             # full breakdown by provider
```

### Persistent token log

The `TokenTracker` appends every API call to a JSONL file:

```python
from akms.logging import TokenTracker

tt = TokenTracker("knowledge/logs/token_usage.json")
tt.log("claude", "sonnet", tokens=700, cost_usd=0.014)

today = tt.load_today()   # list of records for today
all_records = tt.load_all()
```

View today's usage from the CLI: `akms budget`

---

## Project Structure

```
akms/
├── akms_config.yaml.example     ← copy this to akms_config.yaml
├── pyproject.toml
├── src/
│   └── akms/
│       ├── cli.py               ← CLI entry point (akms command)
│       ├── config.py            ← config loading
│       ├── agents/
│       │   ├── base.py          ← BaseAgent
│       │   ├── executor.py      ← Executor (main chat agent)
│       │   ├── expert.py        ← Expert (knowledge retrieval)
│       │   ├── librarian.py     ← Librarian (knowledge curation)
│       │   └── council.py       ← 5-role deliberation council
│       ├── core/
│       │   ├── message.py       ← provider-agnostic message schema
│       │   ├── budget.py        ← budget tracking
│       │   └── orchestrator.py  ← agent coordination
│       ├── knowledge/
│       │   ├── wiki.py          ← markdown wiki layer
│       │   ├── db.py            ← SQLite structured layer
│       │   ├── graph.py         ← hybrid graph interface
│       │   └── search.py        ← keyword search
│       ├── checkpoints/
│       │   ├── store.py         ← checkpoint persistence
│       │   └── fork.py          ← fork/rollback for Expert agents
│       ├── providers/
│       │   ├── base.py          ← LLMProvider protocol
│       │   ├── claude.py
│       │   ├── openai_provider.py
│       │   ├── gemini.py
│       │   ├── deepseek.py
│       │   └── ollama.py
│       ├── integrations/
│       │   ├── generic.py       ← GenericWrapper (inject AKMS into any provider)
│       │   └── claude_code.py   ← Claude Code specific wrapper
│       └── logging/
│           ├── conversation_log.py
│           └── token_tracker.py
├── knowledge/                   ← created by `akms init`
│   ├── graph/
│   ├── archives/
│   ├── logs/
│   └── research_queue.md
└── tests/                       ← pytest test suite (43 tests)
```

---

## Tips

**Start small.** Run `akms init`, then `akms ingest` one or two documents you care about, then `akms chat`. The knowledge graph builds incrementally.

**Check consistency regularly.** After adding many nodes manually, broken wikilinks accumulate. Run the consistency check via the Python API to find them.

**Use section names consistently.** Sections are directories — `distributed-systems` and `distributed_systems` are different sections. Pick a convention (`kebab-case` recommended) and stick to it.

**Archive, never delete.** The system is designed around never deleting knowledge. If something is wrong, use `librarian.archive_node()` — it moves the node to `knowledge/archives/` with metadata about why it was archived.

**Budget control.** Set a low `daily_limit_usd` in the config while experimenting. The CLI will warn you when you approach the limit.
