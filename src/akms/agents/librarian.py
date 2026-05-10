"""Librarian agent — knowledge curator for AKMS."""

from __future__ import annotations

import datetime
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from akms.agents.base import BaseAgent

if TYPE_CHECKING:
    from akms.config import AKMSConfig
    from akms.knowledge.graph import HybridGraph
    from akms.logging.conversation_log import ConversationLogger
    from akms.providers.base import LLMProvider


class LibrarianAgent(BaseAgent):
    """Knowledge curator: ingests logs, digests documents, audits consistency."""

    agent_type = "librarian"

    def __init__(
        self,
        provider: LLMProvider,
        model: str,
        config: AKMSConfig,
        logger: ConversationLogger | None = None,
        session_id: str | None = None,
    ) -> None:
        super().__init__(provider, model, config, logger, session_id)

    # ------------------------------------------------------------------
    # Log ingestion
    # ------------------------------------------------------------------

    def ingest_log(
        self, conversation_log_path: str | Path, graph: HybridGraph
    ) -> list[dict[str, Any]]:
        """Read a JSONL conversation log and extract factual insights via LLM."""
        path = Path(conversation_log_path)
        assistant_parts: list[str] = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = entry.get("message", entry)
                if msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    if content:
                        assistant_parts.append(content)
        except OSError:
            return []

        conversation_text = "\n".join(assistant_parts)
        if not conversation_text.strip():
            return []

        prompt = (
            "Extract factual knowledge insights from this conversation log. "
            "Return a JSON array of objects, each with: section (str), node_id (str), "
            "title (str), content (str), tags (list[str]), confidence (float 0-1). "
            "Only extract clear, factual claims worth storing. Max 5 insights.\n\n"
            f"Conversation:\n{conversation_text[:3000]}\n\n"
            "Return ONLY valid JSON array, no other text."
        )
        response = self.ask(prompt)
        raw = response.message.content.strip()

        try:
            insights: list[dict[str, Any]] = json.loads(raw)
            if not isinstance(insights, list):
                return []
            return insights
        except (json.JSONDecodeError, ValueError):
            # Try to extract a JSON array from the response if wrapped in prose
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                try:
                    insights = json.loads(match.group(0))
                    if isinstance(insights, list):
                        return insights
                except (json.JSONDecodeError, ValueError):
                    pass
            return []

    # ------------------------------------------------------------------
    # Graph updates from insights
    # ------------------------------------------------------------------

    def update_graph_from_insights(
        self, insights: list[dict[str, Any]], graph: HybridGraph
    ) -> int:
        """Upsert insight dicts into the graph. Returns count of nodes upserted."""
        count = 0
        for insight in insights:
            try:
                section = insight["section"]
                node_id = insight["node_id"]
                title = insight.get("title", node_id)
                content = insight.get("content", "")
                tags = insight.get("tags", [])
                confidence = float(insight.get("confidence", 1.0))
            except (KeyError, TypeError, ValueError):
                continue

            existing = graph.get_node(section, node_id)
            if existing is not None:
                graph.update_node(section, node_id, content=content)
            else:
                graph.add_node(
                    section=section,
                    node_id=node_id,
                    title=title,
                    content=content,
                    tags=tags,
                    confidence=confidence,
                )
            count += 1
        return count

    # ------------------------------------------------------------------
    # Document digestion
    # ------------------------------------------------------------------

    def digest_document(
        self, file_path: str | Path, graph: HybridGraph
    ) -> int:
        """Parse a markdown document into chunks and store each as a graph node."""
        path = Path(file_path)
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return 0

        # Split on markdown headings (## or #) keeping the heading with its chunk
        chunks: list[str] = re.split(r"(?=^#{1,2} )", raw, flags=re.MULTILINE)

        count = 0
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk or len(chunk) < 50:
                continue

            prompt = (
                "Classify this content chunk for a knowledge graph. "
                "Return JSON with: section (snake_case str), node_id (snake_case str), "
                "title (str), tags (list[str]), confidence (float).\n"
                f"Content: {chunk[:1000]}\n"
                "Return ONLY valid JSON, no other text."
            )
            try:
                response = self.ask(prompt)
                raw_resp = response.message.content.strip()
                meta: dict[str, Any] = json.loads(raw_resp)
            except (json.JSONDecodeError, ValueError):
                # Attempt to extract JSON object from prose
                try:
                    match = re.search(r"\{.*\}", raw_resp, re.DOTALL)
                    if not match:
                        continue
                    meta = json.loads(match.group(0))
                except (json.JSONDecodeError, ValueError, UnboundLocalError):
                    continue

            try:
                section = meta["section"]
                node_id = meta["node_id"]
                title = meta.get("title", node_id)
                tags = meta.get("tags", [])
                confidence = float(meta.get("confidence", 1.0))
            except (KeyError, TypeError, ValueError):
                continue

            try:
                graph.add_node(
                    section=section,
                    node_id=node_id,
                    title=title,
                    content=chunk,
                    tags=tags,
                    confidence=confidence,
                )
                count += 1
            except Exception:
                continue

        return count

    # ------------------------------------------------------------------
    # Consistency checking
    # ------------------------------------------------------------------

    def check_consistency(self, graph: HybridGraph) -> list[dict[str, Any]]:
        """Scan all wikilinks and report broken references."""
        sections = graph.list_sections()

        # Build a flat set of all node_ids across all sections for fast lookup
        all_node_ids: set[str] = set()
        for section in sections:
            for node_id in graph.list_nodes(section):
                all_node_ids.add(node_id)

        issues: list[dict[str, Any]] = []
        for section in sections:
            for node_id in graph.list_nodes(section):
                node = graph.get_node(section, node_id)
                if node is None:
                    continue
                for target in node.get("wikilinks", []):
                    if target not in all_node_ids:
                        issues.append(
                            {
                                "node_id": node_id,
                                "section": section,
                                "broken_link": target,
                                "issue": "broken wikilink",
                            }
                        )
        return issues

    # ------------------------------------------------------------------
    # Research queue
    # ------------------------------------------------------------------

    def add_to_research_queue(
        self, topic: str, reason: str, queue_path: str | Path
    ) -> None:
        """Append a pending research item under the Pending section of the queue file."""
        path = Path(queue_path)
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            content = "## Pending (Awaiting Approval)\n"

        new_item = f'- [ ] "{topic}" — {reason}\n'
        heading = "## Pending (Awaiting Approval)"

        if heading in content:
            # Insert the new item immediately after the heading line
            idx = content.index(heading) + len(heading)
            content = content[:idx] + "\n" + new_item + content[idx + 1:]
        else:
            content = content.rstrip("\n") + f"\n\n{heading}\n{new_item}"

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------
    # Node archival
    # ------------------------------------------------------------------

    def archive_node(
        self, section: str, node_id: str, reason: str, graph: HybridGraph
    ) -> bool:
        """Move a node to the archives directory and remove it from the live graph."""
        node = graph.get_node(section, node_id)
        if node is None:
            return False

        today = datetime.date.today().isoformat()
        archives_dir = Path(self._config.knowledge.archives_dir)
        archive_path = archives_dir / section / f"{node_id}.md"
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        title = node.get("title", node_id)
        content = node.get("content", "")
        tags = node.get("tags", [])
        confidence = node.get("confidence", 1.0)
        created = node.get("created", "")
        sources = node.get("sources", [])

        frontmatter_data: dict[str, Any] = {
            "id": node_id,
            "section": section,
            "created": created,
            "sources": sources,
            "tags": tags,
            "confidence": confidence,
            "archived": today,
            "archive_reason": reason,
            "original_section": section,
        }
        body = f"# {title}\n\n{content}\n"
        archive_text = "---\n" + yaml.safe_dump(frontmatter_data, sort_keys=False) + "---\n\n" + body
        archive_path.write_text(archive_text, encoding="utf-8")

        # Remove from SQLite
        try:
            graph.sqlite.delete_node(node_id)
        except Exception:
            pass

        # Remove the wiki markdown file
        wiki_path = Path(graph.wiki.graph_dir) / section / f"{node_id}.md"
        if wiki_path.exists():
            wiki_path.unlink()

        return True
