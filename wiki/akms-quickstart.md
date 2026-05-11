---
title: AKMS Quick Start
tags: [akms, quickstart, setup]
category: environment
created: 2026-05-10
---

# AKMS Quick Start

Get running in 3 steps. You only need **one** API key — Claude is the simplest choice.

## Step 1 — Install

```bash
git clone https://github.com/your-org/akms && cd akms
pip install -e .
```

## Step 2 — Minimal config

Create `akms_config.yaml` with just Claude:

```yaml
providers:
  claude:
    api_key: "${CLAUDE_API_KEY}"
    models:
      - claude-sonnet-4-6

agent_assignments:
  expert:
    provider: claude
    model: claude-sonnet-4-6
  librarian:
    provider: claude
    model: claude-sonnet-4-6

knowledge:
  graph_dir: "knowledge/graph"
  archives_dir: "knowledge/archives"
  logs_dir: "knowledge/logs"
  db_path: "knowledge/akms.db"
```

Set your API key:
```bash
export CLAUDE_API_KEY="sk-ant-..."
```

## Step 3 — Init and query

```bash
akms init                          # creates the knowledge/ directory
akms ingest my-notes.md            # feed documents to the Librarian
akms search "consensus algorithms" # search the graph
akms ask "distributed-systems" "How does Raft work?"
```

## What happens next

Run `akms ingest` on documents or notes. The Librarian agent extracts knowledge nodes and adds them to the graph. Future queries get smarter as the graph grows.

## See also

- [[akms-overview]] — what AKMS is
- [[akms-concepts]] — how the knowledge graph works
