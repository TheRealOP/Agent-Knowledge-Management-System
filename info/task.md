# AKMS — Build Task Tracker

## Phase 1 — Foundation
- [x] Project scaffolding (`pyproject.toml`, package structure, `__init__.py` files)
- [x] Config system (`akms_config.yaml.example` + `config.py`)
- [x] Provider-agnostic message schema (`message.py`)
- [x] Provider abstraction layer (`providers/base.py` + `registry.py`)
- [x] Claude provider adapter (`providers/claude.py`)
- [x] OpenAI provider adapter (`providers/openai_provider.py`)
- [x] Basic CLI entry point (`cli.py`)

## Phase 2 — Knowledge Graph
- [ ] Wiki layer (markdown files + wikilink parsing)
- [ ] SQLite structured layer (nodes, edges, provenance)
- [ ] Hybrid graph interface
- [ ] Graph search
- [ ] Starter templates

## Phase 3 — Checkpoint System
- [ ] Checkpoint store (SQLite)
- [ ] Fork/rollback mechanism
- [ ] Home state management

## Phase 4 — Agent 2: Expert
- [ ] Expert agent with graph section reading
- [ ] Fork-based Q&A with rollback
- [ ] Caveman mode communication
- [ ] Dynamic scaling logic

## Phase 5 — Agent 3: Librarian
- [ ] Conversation log ingestion
- [ ] Paper/document digestion
- [ ] Research queue
- [ ] Consistency checking
- [ ] Mistake archival
- [ ] Expert management

## Phase 6 — Agent 1: Executor
- [ ] Orchestrator
- [ ] Integration wrappers
- [ ] 5-subagent council
- [ ] Conversation logging pipeline

## Phase 7 — Budget & Polish
- [ ] Token tracking + budget limits
- [ ] Remaining providers
- [ ] User overlay system
- [ ] CLI polish + docs

## Phase 8 — Testing & Hardening
- [ ] Unit tests
- [ ] Integration tests
- [ ] Edge cases
- [ ] README + setup guide
