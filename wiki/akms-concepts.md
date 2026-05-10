---
title: AKMS Core Concepts
tags: [akms, concepts, knowledge-graph, expert, fork]
category: architecture
created: 2026-05-10
---

# AKMS Core Concepts

## Knowledge Graph

The graph lives in `knowledge/graph/`. It has two layers that stay in sync:

- **Markdown files** — human-readable, you can edit them by hand
- **SQLite database** — powers fast keyword search

Nodes are organized by **section** (a directory):

```
knowledge/graph/
├── distributed-systems/
│   ├── cap-theorem.md
│   └── consensus.md
└── machine-learning/
    └── transformers.md
```

Each node is a markdown file with YAML frontmatter:

```markdown
---
id: cap-theorem
section: distributed-systems
tags: [consistency, availability]
confidence: 0.92
---

# CAP Theorem

The CAP theorem states that a distributed system can guarantee at most two of:
Consistency, Availability, Partition tolerance.

## Connections
- [[consensus]] — CAP defines the tradeoff space
```

`[[wikilinks]]` create graph edges. Run `graph.sync_links()` to push them into SQLite.

## How Expert Agents Work (Fork/Rollback)

Expert agents have a "home state" — a set of priming messages teaching them their section. When you ask an Expert a question:

1. The home state is **forked** (copied)
2. Your question is added to the fork
3. The Expert answers
4. The fork is **discarded**

The Expert's home state is never polluted by any single query. Each Q&A is clean and isolated.

This means Expert agents are cheap to run: no accumulated conversation bloat, no context drift.

## How the Librarian Updates the Graph

The Librarian reads conversation log files (JSONL) and document files, then:

1. Splits content by headings
2. Classifies each chunk (what section does this belong to?)
3. Creates or updates knowledge nodes
4. Flags knowledge gaps for the research queue

You can run this manually: `akms ingest <file>`

## Budget & Cost Control

Every API call is logged to `knowledge/logs/token_usage.json`. Set a daily cap in config:

```yaml
budget:
  daily_limit_usd: 5.00   # hard stop at $5/day
  per_query_warn_usd: 0.50  # warn on expensive single calls
```

Check usage: `akms budget`

## See also

- [[akms-overview]] — what AKMS is
- [[akms-quickstart]] — get running in 3 steps
