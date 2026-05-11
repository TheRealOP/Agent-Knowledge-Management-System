"""Markdown-based wiki layer for knowledge nodes."""

from __future__ import annotations

import datetime
import re
from pathlib import Path
from typing import Any

import yaml


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_RESERVED_FILES = {"_index", "_section"}


class WikiLayer:
    """Filesystem-backed markdown nodes organized by section."""

    def __init__(self, graph_dir: str) -> None:
        self.graph_dir = Path(graph_dir)

    def _node_path(self, section: str, node_id: str) -> Path:
        return self.graph_dir / section / f"{node_id}.md"

    def _section_path(self, section: str) -> Path:
        return self.graph_dir / section

    def _parse_file(self, path: Path) -> tuple[dict[str, Any], str, str]:
        """Return (frontmatter, title, content) from a node markdown file."""
        raw = path.read_text(encoding="utf-8")
        match = _FRONTMATTER_RE.match(raw)
        if match:
            frontmatter = yaml.safe_load(match.group(1)) or {}
            body = match.group(2)
        else:
            frontmatter = {}
            body = raw

        title = ""
        content = body
        body_stripped = body.lstrip("\n")
        if body_stripped.startswith("# "):
            first_newline = body_stripped.find("\n")
            if first_newline == -1:
                title = body_stripped[2:].strip()
                content = ""
            else:
                title = body_stripped[2:first_newline].strip()
                content = body_stripped[first_newline + 1:].lstrip("\n")
        return frontmatter, title, content

    def create_node(
        self,
        section: str,
        node_id: str,
        title: str,
        content: str,
        tags: list[str] | None = None,
        confidence: float = 1.0,
        sources: list[Any] | None = None,
    ) -> Path:
        """Write a node markdown file, creating the section dir if needed."""
        section_dir = self._section_path(section)
        section_dir.mkdir(parents=True, exist_ok=True)

        section_md = section_dir / "_section.md"
        if not section_md.exists():
            section_md.write_text(f"# {section}\n", encoding="utf-8")

        frontmatter = {
            "id": node_id,
            "section": section,
            "created": datetime.date.today().isoformat(),
            "sources": sources if sources is not None else [],
            "tags": tags if tags is not None else [],
            "confidence": confidence,
        }
        body = f"# {title}\n\n{content}\n"
        text = "---\n" + yaml.safe_dump(frontmatter, sort_keys=False) + "---\n\n" + body

        path = self._node_path(section, node_id)
        path.write_text(text, encoding="utf-8")
        return path

    def read_node(self, section: str, node_id: str) -> dict[str, Any] | None:
        path = self._node_path(section, node_id)
        if not path.exists():
            return None
        frontmatter, title, content = self._parse_file(path)
        return {
            "id": frontmatter.get("id", node_id),
            "section": frontmatter.get("section", section),
            "title": title,
            "content": content,
            "tags": frontmatter.get("tags", []) or [],
            "confidence": frontmatter.get("confidence", 1.0),
            "wikilinks": self.parse_wikilinks(content),
            "created": frontmatter.get("created", ""),
            "sources": frontmatter.get("sources", []) or [],
        }

    def update_node(self, section: str, node_id: str, **fields: Any) -> bool:
        path = self._node_path(section, node_id)
        if not path.exists():
            return False
        frontmatter, title, content = self._parse_file(path)
        frontmatter_keys = {"id", "section", "created", "sources", "tags", "confidence"}
        for key, value in fields.items():
            if key == "title":
                title = value
            elif key == "content":
                content = value
            elif key in frontmatter_keys:
                frontmatter[key] = value
            else:
                frontmatter[key] = value

        new_body = f"# {title}\n\n{content}".rstrip() + "\n"
        text = "---\n" + yaml.safe_dump(frontmatter, sort_keys=False) + "---\n\n" + new_body
        path.write_text(text, encoding="utf-8")
        return True

    def list_sections(self) -> list[str]:
        if not self.graph_dir.exists():
            return []
        return sorted(p.name for p in self.graph_dir.iterdir() if p.is_dir())

    def list_nodes(self, section: str) -> list[str]:
        section_dir = self._section_path(section)
        if not section_dir.exists():
            return []
        return sorted(
            p.stem
            for p in section_dir.iterdir()
            if p.is_file() and p.suffix == ".md" and p.stem not in _RESERVED_FILES
        )

    def parse_wikilinks(self, content: str) -> list[str]:
        return [m.group(1).split("|")[0].strip() for m in _WIKILINK_RE.finditer(content)]
