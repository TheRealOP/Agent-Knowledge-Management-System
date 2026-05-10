---
title: AKMS Overview
tags: [akms, overview, what-is]
category: architecture
created: 2026-05-10
---

# AKMS Overview

AKMS gives AI agents a persistent memory — a knowledge graph that grows over sessions.

## The core idea in one sentence

Every conversation you have with an AI agent gets logged, summarized, and stored. The next conversation starts smarter because the agent can look things up from what it learned before.

## Three things AKMS does

1. **Stores knowledge** — markdown files + SQLite database, human-readable, git-friendly
2. **Retrieves knowledge** — Expert agents answer domain questions from stored nodes
3. **Grows knowledge** — the Librarian agent reads your conversation logs and adds new nodes automatically

## The three agents

| Agent | Role | When it runs |
|---|---|---|
| **Executor** | Talks to you, decides when to query experts | Every `akms chat` session |
| **Expert** | Answers questions from one knowledge section | When Executor calls `query_knowledge` |
| **Librarian** | Reads logs, updates the graph | After sessions / `akms ingest` |

## Why not just use a plain chatbot?

A plain chatbot forgets everything between sessions. AKMS keeps a graph that compounds — every session leaves behind structured knowledge for the next one.

## See also

- [[akms-quickstart]] — get running in 3 steps
- [[akms-concepts]] — how the knowledge graph works
