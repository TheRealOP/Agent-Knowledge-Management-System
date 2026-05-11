# How This Works — AKMS Architecture Guide

> A visual, diagram-heavy walkthrough of every layer in the Agent Knowledge Management System.

---

## 1. High-Level System Overview

```mermaid
graph TB
    User["👤 User"]
    AnyAgent["Any Agent / IDE\n(Claude Code, Antigravity, Codex, Ollama, ...)"]
    AKMSCLI["akms CLI\nsearch · ask · get · ingest · sections · ..."]

    subgraph AKMSCore["AKMS Core"]
        Orchestrator["⚙️ Orchestrator\n(routing only)"]
        Expert["🤖 Expert Agent(s)"]
        Librarian["🤖 Librarian Agent"]
        Council["🤖 Council Agent"]
    end

    KG["Knowledge Graph\n(Markdown + SQLite)"]
    CP["Checkpoint Store"]
    Providers["LLM Providers"]

    User --> AnyAgent
    AnyAgent -->|"reads agents.md\nruns shell commands"| AKMSCLI
    AKMSCLI --> AKMSCore
    Orchestrator -->|"creates & caches"| Expert
    Expert -->|"reads nodes"| KG
    Librarian -->|"writes nodes"| KG
    Expert -->|"chat()"| Providers
    Librarian -->|"chat()"| Providers
    Council -->|"chat()"| Providers
    Expert -->|"fork/rollback"| CP

    style User fill:#6366f1,color:#fff
    style AnyAgent fill:#1e293b,color:#fff
    style AKMSCLI fill:#0ea5e9,color:#fff
    style AKMSCore fill:#0f172a,color:#fff
    style Orchestrator fill:#f59e0b,color:#000
    style KG fill:#10b981,color:#fff
    style CP fill:#8b5cf6,color:#fff
    style Providers fill:#ef4444,color:#fff
    style Expert fill:#10b981,color:#fff
    style Librarian fill:#f59e0b,color:#000
    style Council fill:#ef4444,color:#fff
```

> [!IMPORTANT]
> **The CLI is the universal interface.** Any agent that can run a shell command can use AKMS — no wrapper code, no Python integration, no per-IDE maintenance. The agent reads `agents.md` to learn the available commands, then calls them like skills.

> [!IMPORTANT]
> **The Orchestrator is NOT an agent.** It's a plain Python coordinator class in `core/orchestrator.py` that never calls an LLM. It manages the Expert pool (caching, splitting large sections, routing queries). Think of it as the **switchboard**, not a participant.

**One sentence:** Any agent, from any provider, reads `agents.md` and uses `akms` CLI commands as skills to query, update, and grow a persistent knowledge graph.

---

## 2. Repository File Tree

```mermaid
graph LR
    Root["📁 akms/"]
    Root --> Config["akms_config.yaml.example"]
    Root --> Pyproject["pyproject.toml"]
    Root --> Readme["README.md"]
    Root --> SrcDir["📁 src/akms/"]
    Root --> KnowDir["📁 knowledge/"]
    Root --> TestDir["📁 tests/"]
    Root --> WikiDir["📁 wiki/"]
    Root --> InfoDir["📁 info/"]

    SrcDir --> CliPy["cli.py"]
    SrcDir --> ConfigPy["config.py"]
    SrcDir --> Agents["📁 agents/"]
    SrcDir --> Core["📁 core/"]
    SrcDir --> Knowledge["📁 knowledge/"]
    SrcDir --> Checkpoints["📁 checkpoints/"]
    SrcDir --> ProvidersDir["📁 providers/"]
    SrcDir --> Integrations["📁 integrations/"]
    SrcDir --> Logging["📁 logging/"]

    style Root fill:#1e293b,color:#fff
    style SrcDir fill:#334155,color:#fff
    style KnowDir fill:#10b981,color:#fff
    style TestDir fill:#f59e0b,color:#000
```

---

## 3. What Every File Does

### Root Files

| File | Purpose |
|---|---|
| `pyproject.toml` | Package metadata, deps (`pyyaml`, `click`, `anthropic`, `openai`, `aiosqlite`), CLI entry point `akms = akms.cli:main` |
| `akms_config.yaml.example` | Reference config — providers, agent assignments, budget, knowledge paths, expert thresholds |
| `README.md` | Full user-facing docs, CLI reference, Python API examples |

### `src/akms/` — The Main Package

| File | Purpose |
|---|---|
| `__init__.py` | Exports `__version__` |
| `cli.py` | Click CLI — `init`, `chat`, `ingest`, `status`, `budget`, `research`, `overlay` commands |
| `config.py` | Dataclasses (`ProviderConfig`, `AgentAssignment`, `BudgetConfig`, `KnowledgeConfig`, `ExpertConfig`, `AKMSConfig`) + YAML loader with `${ENV_VAR}` resolution |

### `src/akms/agents/`

| File | Class | Purpose |
|---|---|---|
| `base.py` | `BaseAgent` | Abstract base — `send()`, `ask()`, `reset()`, token tracking, JSONL logging, session management |
| `executor.py` | `ExecutorAgent` | Primary chat agent — detects `query_knowledge` JSON tool calls in LLM output, routes them through orchestrator, loops up to 5 rounds |
| `expert.py` | `ExpertAgent` | Owns one knowledge section — `load_section()` builds system prompt from nodes, `answer()` uses fork/rollback (throwaway conversation branch) |
| `librarian.py` | `LibrarianAgent` | Knowledge curator — `ingest_log()` extracts insights from JSONL, `digest_document()` chunks markdown by heading, `check_consistency()` finds broken wikilinks, `archive_node()` moves nodes to archives |
| `council.py` | `CouncilAgent` | 5-role deliberation (Advocate, Critic, Historian, Innovator, Synthesizer) — does NOT extend BaseAgent |

### `src/akms/core/`

| File | Class | Purpose |
|---|---|---|
| `message.py` | `Role`, `Message`, `Response`, `Conversation` | Provider-agnostic message schema — serializable to/from dict, `Conversation.fork_at()` for branching |
| `budget.py` | `BudgetTracker`, `UsageRecord` | In-memory cost tracking — `record_usage()`, `daily_total_usd()`, `is_over_limit()`, `summary()` |
| `orchestrator.py` | `Orchestrator` | Central coordinator — expert pool cache, dynamic expert scaling (splits large sections into chunk experts), `query_expert()` with keyword-overlap routing for split sections |

### `src/akms/knowledge/`

| File | Class | Purpose |
|---|---|---|
| `wiki.py` | `WikiLayer` | Markdown filesystem layer — YAML frontmatter + `# Title` + content, `[[wikilink]]` parsing, CRUD for nodes organized in section directories |
| `db.py` | `SQLiteLayer` | Structured SQLite store — `nodes`, `edges`, `provenance`, `search_index` tables, keyword search via `LIKE` |
| `graph.py` | `HybridGraph` | Unified facade — writes to both wiki + SQLite, `sync_links()` parses wikilinks into DB edges, delegates search to `GraphSearch` |
| `search.py` | `GraphSearch` | Tokenized keyword search — splits query into tokens, scores nodes by token-hit count, returns ranked results |
| `user_overlay.py` | `UserOverlay` | JSON file storing per-concept understanding scores (0.0–1.0) with notes and review dates |
| `schema.sql` | — | SQLite DDL for `nodes`, `edges`, `provenance`, `search_index` |

### `src/akms/checkpoints/`

| File | Class/Function | Purpose |
|---|---|---|
| `store.py` | `CheckpointStore` | SQLite-backed checkpoint persistence — `save()`, `load()`, `get_home_state_id()`, `list_checkpoints()` |
| `fork.py` | `fork_from_checkpoint()`, `discard_fork()`, `restore_home_state()` | Fork/rollback helpers — create throwaway conversation branches from checkpoints, discard after use |
| `schema.sql` | — | SQLite DDL for `checkpoints` and `forks` tables |

### `src/akms/providers/`

| File | Class | Purpose |
|---|---|---|
| `base.py` | `LLMProvider` (ABC) | Abstract interface — `chat()`, `stream()`, `count_tokens()`, `_to_provider_format()`, `_from_provider_response()` |
| `registry.py` | `ProviderRegistry` | Factory pattern — `register()`, `create()`, `create_from_config()`. `build_default_registry()` lazy-loads all built-in providers |
| `claude.py` | `ClaudeProvider` | Anthropic adapter — handles system prompt separation, token counting via API |
| `openai_provider.py` | `OpenAIProvider` | OpenAI/GPT adapter |
| `gemini.py` | `GeminiProvider` | Google Gemini adapter |
| `deepseek.py` | `DeepSeekProvider` | DeepSeek adapter (OpenAI-compatible) |
| `ollama.py` | `OllamaProvider` | Local Ollama adapter |

### `src/akms/integrations/`

| File | Class | Purpose |
|---|---|---|
| `generic.py` | `GenericWrapper` | Base wrapper — injects AKMS system prompt listing available sections + tool protocol, handles multi-round tool call loops |
| `claude_code.py` | `ClaudeCodeWrapper` | Tuned for Claude Code — `graph:section/node-id` references |
| `codex.py` | `CodexWrapper` | Tuned for OpenAI Codex |
| `opencode.py` | `OpenCodeWrapper` | Tuned for OpenCode — checks architectural decisions first |

### `src/akms/logging/`

| File | Class | Purpose |
|---|---|---|
| `conversation_log.py` | `ConversationLogger` | JSONL conversation logger — one file per `{date}_{conversation_id}.jsonl`, organized by agent type |
| `token_tracker.py` | `TokenTracker` | JSONL token usage logger — `log()`, `load_today()`, `load_all()` |

### `knowledge/` — Runtime Data

| Path | Purpose |
|---|---|
| `knowledge/graph/` | Markdown node files organized by section subdirectories |
| `knowledge/archives/` | Archived (retired) nodes with archive reason |
| `knowledge/logs/` | JSONL conversation logs and token usage |
| `knowledge/user_overlay/` | `understanding.json` — user concept scores |
| `knowledge/research_queue.md` | Knowledge gaps flagged by the Librarian |

### `tests/` — Test Suite

| File | What it tests |
|---|---|
| `conftest.py` | Shared fixtures (tmp dirs, mock providers, sample configs) |
| `test_config.py` | Config loading, env var resolution, defaults |
| `test_db.py` | SQLite layer CRUD, search index, edges |
| `test_wiki.py` | Wiki layer file I/O, frontmatter parsing, wikilinks |
| `test_message.py` | Message/Response serialization, Conversation forking |
| `test_budget.py` | BudgetTracker daily totals, limits, warnings |
| `test_checkpoints.py` | Checkpoint save/load, home state, forks |
| `test_expert.py` | Expert section loading, fork-based answering |
| `test_executor.py` | Tool call detection and routing |
| `test_librarian.py` | Log ingestion, document digestion, consistency checks, archival |
| `test_orchestrator.py` | Expert pool caching, dynamic splitting, query routing |
| `test_council.py` | Council deliberation flow |
| `test_registry.py` | Provider registration and creation |
| `test_search.py` | Keyword search ranking |
| `test_user_overlay.py` | Overlay CRUD, score clamping |
| `test_integration.py` | End-to-end flows |
| `test_edge_cases.py` | Error handling, missing files, empty states |

---

## 4. The Chat Flow — Step by Step

```mermaid
sequenceDiagram
    participant U as 👤 User
    participant CLI as CLI
    participant E as Executor
    participant O as Orchestrator
    participant X as Expert
    participant P as LLM Provider
    participant KG as Knowledge Graph
    participant CP as Checkpoint Store

    U->>CLI: akms chat
    CLI->>O: _build_orchestrator()
    CLI->>E: create ExecutorAgent
    U->>E: "What is CAP theorem?"
    E->>P: chat(system + user msg)
    P-->>E: response with tool call JSON
    E->>E: detect query_knowledge JSON
    E->>O: query_expert("distributed-systems", "CAP?")
    O->>O: check expert pool cache
    O->>X: create ExpertAgent if not cached
    X->>KG: load_section() → read all nodes
    X->>CP: set_home_state() → persist checkpoint
    O->>X: answer(question)
    X->>CP: fork_from_checkpoint()
    X->>P: chat(fork messages)
    P-->>X: expert answer
    X->>CP: discard_fork()
    X-->>O: compressed answer
    O-->>E: "[distributed-systems] answer..."
    E->>P: chat("Tool result: ... Continue.")
    P-->>E: final response
    E-->>U: "Based on the knowledge graph..."
```

---

## 5. The Ingestion Flow

```mermaid
sequenceDiagram
    participant U as 👤 User
    participant CLI as CLI
    participant L as Librarian
    participant P as LLM Provider
    participant KG as Knowledge Graph

    U->>CLI: akms ingest paper.md
    CLI->>L: create LibrarianAgent
    CLI->>L: digest_document("paper.md", graph)
    L->>L: read file, split on # headings
    loop For each chunk > 50 chars
        L->>P: "Classify this chunk → JSON"
        P-->>L: {section, node_id, title, tags, confidence}
        L->>KG: add_node(section, node_id, ...)
        KG->>KG: write .md file (WikiLayer)
        KG->>KG: upsert SQLite row (SQLiteLayer)
        KG->>KG: update search index
    end
    L-->>CLI: "Done. N node(s) added."
    CLI-->>U: output
```

---

## 6. Knowledge Graph — Dual Storage

```mermaid
graph TB
    subgraph HybridGraph["HybridGraph (graph.py)"]
        direction TB
        API["add_node / get_node / update_node / search / sync_links"]
    end

    subgraph Wiki["WikiLayer (wiki.py)"]
        direction TB
        FS["📁 knowledge/graph/"]
        S1["📁 distributed-systems/"]
        S2["📁 machine-learning/"]
        N1["📄 cap-theorem.md"]
        N2["📄 consensus.md"]
        N3["📄 transformers.md"]
        FS --> S1 & S2
        S1 --> N1 & N2
        S2 --> N3
    end

    subgraph SQLite["SQLiteLayer (db.py)"]
        direction TB
        NT["nodes table"]
        ET["edges table"]
        PT["provenance table"]
        SI["search_index table"]
    end

    API -->|"write .md file"| Wiki
    API -->|"upsert row + index"| SQLite

    style HybridGraph fill:#1e293b,color:#fff
    style Wiki fill:#10b981,color:#fff
    style SQLite fill:#3b82f6,color:#fff
```

### Node Markdown Format

```
---
id: cap-theorem
section: distributed-systems
created: 2026-05-10
tags: [consistency, availability]
confidence: 0.92
sources: []
---

# CAP Theorem

Content here...

## Connections
- [[consensus]]       ← creates a graph edge
```

### SQLite Schema

```mermaid
erDiagram
    nodes {
        TEXT id PK
        TEXT section
        TEXT file_path
        TEXT title
        TEXT created
        TEXT updated
        REAL confidence
    }
    edges {
        INTEGER id PK
        TEXT source_id FK
        TEXT target_id FK
        TEXT relationship_type
        REAL weight
        INTEGER auto_discovered
    }
    provenance {
        INTEGER id PK
        TEXT node_id FK
        TEXT source_type
        TEXT source_ref
        TEXT date
        TEXT verified_by
    }
    search_index {
        TEXT node_id PK
        TEXT keywords
    }

    nodes ||--o{ edges : "source_id"
    nodes ||--o{ edges : "target_id"
    nodes ||--o{ provenance : "node_id"
    nodes ||--|| search_index : "node_id"
```

---

## 7. The Four Agent Types

```mermaid
graph TB
    subgraph Agents
        direction LR
        Base["BaseAgent (ABC)"]
        Exec["ExecutorAgent"]
        Exp["ExpertAgent"]
        Lib["LibrarianAgent"]
        Coun["CouncilAgent ⚠️"]

        Base --> Exec
        Base --> Exp
        Base --> Lib
    end

    Exec ---|"You talk to this one"| UserFacing["User-facing chat"]
    Exp ---|"One per section"| SectionKnow["Section knowledge"]
    Lib ---|"Runs after sessions"| Curation["Knowledge curation"]
    Coun ---|"5-role deliberation"| Deliberation["Complex decisions"]

    style Base fill:#6366f1,color:#fff
    style Exec fill:#0ea5e9,color:#fff
    style Exp fill:#10b981,color:#fff
    style Lib fill:#f59e0b,color:#000
    style Coun fill:#ef4444,color:#fff
```

> ⚠️ `CouncilAgent` does **not** extend `BaseAgent` — it calls `provider.chat()` directly.

### BaseAgent Responsibilities

```mermaid
flowchart LR
    A["send(messages)"] --> B["provider.chat()"]
    B --> C["append to _history"]
    C --> D["log via ConversationLogger"]
    D --> E["track via TokenTracker"]
    E --> F["return Response"]
```

---

## 8. Expert Fork/Rollback Pattern

```mermaid
stateDiagram-v2
    [*] --> HomeState: load_section() + set_home_state()
    HomeState --> Fork: question arrives → fork_from_checkpoint()
    Fork --> Answer: provider.chat(fork_messages)
    Answer --> Discard: discard_fork()
    Discard --> HomeState: home state unchanged

    note right of HomeState: System prompt + all section nodes
    note right of Fork: Throwaway branch — never mutates history
    note right of Discard: Fork marked 'discarded' in SQLite
```

**Why?** Each Expert Q&A is a throwaway branch. The Expert's home state stays clean — no accumulated context drift across queries.

---

## 9. Dynamic Expert Scaling

```mermaid
flowchart TD
    Q["query_expert(section, question)"]
    Q --> Check{"Section tokens > threshold?"}
    Check -->|"No"| Single["Single ExpertAgent"]
    Single --> Load["load_section() → all nodes"]
    Load --> Ans1["answer(question)"]

    Check -->|"Yes"| Split["Split into chunk experts"]
    Split --> C0["Expert :0 (nodes 1-50)"]
    Split --> C1["Expert :1 (nodes 51-100)"]
    Split --> CN["Expert :N (...)"]

    Q2["Question arrives"] --> Score["Score chunks by keyword overlap"]
    Score --> Top2["Query top-2 chunks"]
    Top2 --> Concat["Concatenate answers"]

    style Check fill:#f59e0b,color:#000
    style Split fill:#ef4444,color:#fff
```

**Pool keying:**
- Single sections: `"distributed-systems"`
- Split sections: `"distributed-systems:0"`, `"distributed-systems:1"`, ...
- Sentinel: `"distributed-systems:__split__"` stores the chunk key list

---

## 10. Provider Abstraction

```mermaid
graph TB
    subgraph Abstract["LLMProvider (ABC)"]
        chat["chat(messages) → Response"]
        stream["stream(messages) → Iterator"]
        count["count_tokens(messages) → int"]
    end

    subgraph Implementations
        Claude["ClaudeProvider"]
        OpenAI["OpenAIProvider"]
        Gemini["GeminiProvider"]
        DeepSeek["DeepSeekProvider"]
        Ollama["OllamaProvider"]
    end

    subgraph Registry["ProviderRegistry"]
        register["register(name, class)"]
        create["create(name) → instance"]
        build["build_default_registry()"]
    end

    Abstract --> Claude & OpenAI & Gemini & DeepSeek & Ollama
    Registry -->|"lazy import + register"| Implementations
    Registry -->|"create_from_config()"| Abstract

    style Abstract fill:#6366f1,color:#fff
    style Registry fill:#f59e0b,color:#000
```

All providers normalize to the same `Message` / `Response` types. Swap providers by changing `agent_assignments` in config — zero code changes.

---

## 11. Configuration Loading

```mermaid
flowchart TD
    Start["load_config(path?)"]
    Start --> S1{"Explicit path?"}
    S1 -->|Yes| F1["Use it"]
    S1 -->|No| S2{"./akms_config.yaml?"}
    S2 -->|Yes| F2["Use it"]
    S2 -->|No| S3{"~/.akms/config.yaml?"}
    S3 -->|Yes| F3["Use it"]
    S3 -->|No| Defaults["Return AKMSConfig() defaults"]

    F1 & F2 & F3 --> Parse["yaml.safe_load()"]
    Parse --> Resolve["Resolve ${ENV_VAR} in API keys"]
    Resolve --> Build["Build dataclasses"]
    Build --> Result["AKMSConfig"]

    subgraph Dataclasses
        PC["ProviderConfig"]
        AA["AgentAssignment"]
        BC["BudgetConfig"]
        KC["KnowledgeConfig"]
        EC["ExpertConfig"]
    end

    Result --> Dataclasses

    style Start fill:#0ea5e9,color:#fff
    style Result fill:#10b981,color:#fff
```

---

## 12. CLI Command Map

```mermaid
flowchart LR
    CLI["akms"]
    CLI --> init["init"]
    CLI --> chat["chat"]
    CLI --> ingest["ingest FILE"]
    CLI --> status["status"]
    CLI --> budget["budget"]
    CLI --> research["research"]
    CLI --> overlay["overlay"]

    overlay --> olist["list"]
    overlay --> oset["set CONCEPT --score"]
    overlay --> oget["get CONCEPT"]
    overlay --> orem["remove CONCEPT"]

    init -->|"Creates"| Dirs["knowledge/ dirs + _index.md + research_queue.md"]
    chat -->|"Starts"| Executor
    ingest -->|"Runs"| Librarian
    status -->|"Shows"| Config["Providers, assignments, budget"]
    budget -->|"Reads"| TokenLog["token_usage.json"]
    research -->|"Shows"| RQ["research_queue.md"]

    style CLI fill:#1e293b,color:#fff
```

---

## 13. Integration Wrappers

```mermaid
classDiagram
    class GenericWrapper {
        +orchestrator
        +extra_system
        +wrap_messages()
        +handle_tool_call()
        +run(user_input, provider, model)
    }
    class ClaudeCodeWrapper {
        +graph:section/node-id refs
    }
    class CodexWrapper {
        +brief structured answers
    }
    class OpenCodeWrapper {
        +architectural decisions first
    }

    GenericWrapper <|-- ClaudeCodeWrapper
    GenericWrapper <|-- CodexWrapper
    GenericWrapper <|-- OpenCodeWrapper
```

These inject an AKMS system prompt into any existing tool session, enabling knowledge graph queries from within Claude Code, Codex, or OpenCode.

---

## 14. Logging & Token Tracking

```mermaid
flowchart LR
    subgraph ConversationLogger
        CL["log_message()"]
        CL --> JSONL["knowledge/logs/{agent_type}/{date}_{id}.jsonl"]
    end

    subgraph TokenTracker
        TT["log()"]
        TT --> TL["knowledge/logs/token_usage.json"]
    end

    subgraph BudgetTracker
        BT["record_usage()"]
        BT --> Mem["In-memory records"]
        Mem --> Daily["daily_total_usd()"]
        Mem --> Limit["is_over_limit()"]
    end

    style ConversationLogger fill:#6366f1,color:#fff
    style TokenTracker fill:#0ea5e9,color:#fff
    style BudgetTracker fill:#f59e0b,color:#000
```

---

## 15. Checkpoint & Fork Database

```mermaid
erDiagram
    checkpoints {
        INTEGER id PK
        TEXT agent_type
        TEXT agent_id
        TEXT name
        TEXT messages_json
        TEXT created_at
        INTEGER is_home_state
    }
    forks {
        INTEGER id PK
        INTEGER checkpoint_id FK
        TEXT fork_messages_json
        TEXT created_at
        TEXT status
    }

    checkpoints ||--o{ forks : "checkpoint_id"
```

- **Home state checkpoints** (`is_home_state=1`): Expert's system prompt + loaded section knowledge
- **Forks**: Throwaway Q&A branches — created from checkpoints, discarded after answering

---

## 16. Council Deliberation Flow

```mermaid
flowchart TD
    Task["Task + Context"]
    Task --> A["🟢 Advocate: Argue FOR"]
    Task --> C["🔴 Critic: Find flaws"]
    Task --> H["🟡 Historian: Past evidence"]
    Task --> I["🔵 Innovator: Alternatives"]

    A & C & H & I --> S["🟣 Synthesizer: Merge all views"]
    S --> Result["Final Recommendation"]

    style A fill:#22c55e,color:#fff
    style C fill:#ef4444,color:#fff
    style H fill:#eab308,color:#000
    style I fill:#3b82f6,color:#fff
    style S fill:#a855f7,color:#fff
```

Each role is a separate LLM call with a role-specific system prompt. The Synthesizer sees all four perspectives and produces the final recommendation.

---

## 17. Data Flow Summary

```mermaid
flowchart TB
    subgraph Input
        Chat["akms chat"]
        Ingest["akms ingest"]
        Manual["Manual .md files"]
    end

    subgraph Processing
        Exec["Executor (chat)"]
        Lib["Librarian (ingest)"]
        Sync["sync_links()"]
    end

    subgraph Storage
        Wiki["📁 Markdown files"]
        DB["🗄️ SQLite (akms.db)"]
        Logs["📋 JSONL logs"]
        Checkpoints["💾 checkpoints.db"]
    end

    subgraph Output
        Answers["Chat responses"]
        Status["Status/budget info"]
        Research["Research queue"]
    end

    Chat --> Exec --> Answers
    Exec -->|"logs"| Logs
    Ingest --> Lib --> Wiki & DB
    Manual --> Sync --> DB
    Logs -->|"Librarian reads"| Lib
    Wiki & DB -->|"Expert reads"| Exec

    style Input fill:#0ea5e9,color:#fff
    style Processing fill:#f59e0b,color:#000
    style Storage fill:#10b981,color:#fff
    style Output fill:#6366f1,color:#fff
```

---

## 18. Known Architectural Decisions

| Decision | Rationale |
|---|---|
| **Dual storage (Wiki + SQLite)** | Markdown is human-readable and git-friendly; SQLite enables fast search and relational queries |
| **Fork/rollback for Experts** | Prevents context drift — each Q&A is isolated, home state never mutated |
| **Text-based tool protocol** | LLM outputs JSON tool calls as text, parsed by string matching — simple, provider-agnostic |
| **Lazy provider imports** | Only loads provider dependencies that are installed — avoids requiring all SDKs |
| **Chunk expert splitting** | Large sections auto-split at `token_threshold` with keyword-overlap routing to top-2 chunks |
| **CouncilAgent standalone** | Does not extend BaseAgent — 5 separate LLM calls don't need shared history |
