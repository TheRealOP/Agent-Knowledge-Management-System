---
title: AKMS Overview
tags: [akms, overview, what-is]
category: architecture
created: 2026-05-10
updated: 2026-05-11
---

# AKMS Overview

AKMS gives AI agents a persistent memory — a knowledge graph that grows over sessions.

## The core idea in one sentence

Knowledge is stored as markdown nodes in a graph. Expert agents pre-load sections of that graph and answer questions from your IDE agent via CLI commands — no wrappers, no per-IDE integration code.

## Three things AKMS does

1. **Stores knowledge** — markdown files + SQLite index, human-readable, git-friendly
2. **Retrieves knowledge** — Expert agents pre-load sections and answer queries via `akms ask`
3. **Grows knowledge** — the Librarian agent reads documents and conversation logs, adds new nodes, uses the Council internally to reason about graph structure

## The three roles

| Role | Who | What it does |
|---|---|---|
| **Agent 1 (Main)** | Your IDE agent (Claude Code, Codex, ...) | Talks to you, does work, queries Experts via `akms` CLI commands |
| **Agent 2 (Expert)** | `ExpertAgent` — one per section | Pre-loads a knowledge section, answers queries via fork/rollback (no context drift) |
| **Agent 3 (Manager)** | `LibrarianAgent` | Ingests documents, manages the expert pool, uses Council internally to organize the graph |

## The fork/rollback pattern

Each Expert pre-loads its section into a home state checkpoint (think `--resume`). Every query from Agent 1 creates a throwaway fork, gets answered, and is discarded. The Expert's home state is never mutated — no context drift across queries.

## Why not just use a plain chatbot?

A plain chatbot forgets everything between sessions. AKMS keeps a graph that compounds — every session leaves behind structured knowledge for the next one, and any agent can query it with a shell command.

## Storage: markdown + SQLite

- **Markdown** is the source of truth — human-readable, git-friendly, LLM-traversable, wikilink syntax maps directly to graph edges
- **SQLite** is a derived index — fast search and edge queries when the graph grows large. Always reconstructable from the markdown.

## See also

- [[akms-quickstart]] — get running in 3 steps
- [[akms-concepts]] — how the knowledge graph works
