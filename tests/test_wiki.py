from __future__ import annotations

import pytest
from pathlib import Path

from akms.knowledge.wiki import WikiLayer


def test_create_node_creates_file(tmp_dir):
    """create_node creates file at {graph_dir}/{section}/{id}.md."""
    wiki = WikiLayer(str(tmp_dir / "graph"))
    path = wiki.create_node(
        section="ds",
        node_id="cap",
        title="CAP Theorem",
        content="Consistency, Availability, Partition tolerance.",
        tags=["distributed"],
        confidence=0.9,
    )
    expected = tmp_dir / "graph" / "ds" / "cap.md"
    assert path == expected
    assert expected.exists()


def test_read_node_returns_dict(tmp_dir):
    """read_node returns dict with id, section, title, content, tags, confidence, wikilinks."""
    wiki = WikiLayer(str(tmp_dir / "graph"))
    wiki.create_node(
        section="ds",
        node_id="cap",
        title="CAP Theorem",
        content="See [[consistency]] for more.",
        tags=["distributed"],
        confidence=0.85,
    )
    node = wiki.read_node("ds", "cap")
    assert node is not None
    assert node["id"] == "cap"
    assert node["section"] == "ds"
    assert node["title"] == "CAP Theorem"
    assert "consistency" in node["content"] or "consistency" in node["wikilinks"]
    assert node["tags"] == ["distributed"]
    assert abs(node["confidence"] - 0.85) < 1e-9
    assert "wikilinks" in node


def test_read_node_returns_none_for_nonexistent(tmp_dir):
    """read_node returns None for nonexistent node."""
    wiki = WikiLayer(str(tmp_dir / "graph"))
    result = wiki.read_node("nonexistent_section", "nonexistent_id")
    assert result is None


def test_parse_wikilinks(tmp_dir):
    """parse_wikilinks extracts wikilink targets."""
    wiki = WikiLayer(str(tmp_dir / "graph"))
    links = wiki.parse_wikilinks("see [[cap]] and [[consistency]]")
    assert links == ["cap", "consistency"]


def test_list_sections(tmp_dir):
    """list_sections returns sections after creating nodes in multiple sections."""
    wiki = WikiLayer(str(tmp_dir / "graph"))
    wiki.create_node("section_a", "node1", "Node 1", "content")
    wiki.create_node("section_b", "node2", "Node 2", "content")
    sections = wiki.list_sections()
    assert "section_a" in sections
    assert "section_b" in sections


def test_list_nodes_excludes_reserved(tmp_dir):
    """list_nodes returns node ids, excluding _section and _index files."""
    wiki = WikiLayer(str(tmp_dir / "graph"))
    wiki.create_node("ds", "cap", "CAP", "content")
    wiki.create_node("ds", "paxos", "Paxos", "content")
    nodes = wiki.list_nodes("ds")
    assert "cap" in nodes
    assert "paxos" in nodes
    assert "_section" not in nodes
    assert "_index" not in nodes


def test_update_node_confidence(tmp_dir):
    """update_node updates confidence in frontmatter."""
    wiki = WikiLayer(str(tmp_dir / "graph"))
    wiki.create_node("ds", "cap", "CAP", "content", confidence=1.0)
    wiki.update_node("ds", "cap", confidence=0.5)
    node = wiki.read_node("ds", "cap")
    assert node is not None
    assert abs(node["confidence"] - 0.5) < 1e-9


def test_create_node_creates_section_md(tmp_dir):
    """Creating first node in a section creates _section.md."""
    wiki = WikiLayer(str(tmp_dir / "graph"))
    wiki.create_node("ds", "cap", "CAP", "content")
    section_md = tmp_dir / "graph" / "ds" / "_section.md"
    assert section_md.exists()
