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
  executor:
    provider: claude
    model: claude-sonnet-4-6
  expert:
    provider: claude
    model: claude-sonnet-4-6
  librarian:
    provider: claude
    model: claude-sonnet-4-6
  council:
    provider: claude
    model: claude-sonnet-4-6

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

Set your API key:
```bash
export CLAUDE_API_KEY="sk-ant-..."
```

## Step 3 — Init and chat

```bash
akms init    # creates the knowledge/ directory
akms chat    # start talking
```

That's it. The knowledge graph is empty at first — start by ingesting some documents:

```bash
akms ingest my-notes.md
```

## What happens next

After each chat session, run `akms ingest` on any new notes or documents. The Librarian agent will extract knowledge nodes and add them to the graph. Future chat sessions get smarter.

## See also

- [[akms-overview]] — what AKMS is
- [[akms-concepts]] — how the knowledge graph works
