#!/usr/bin/env python3
"""
GraphMap deterministic builder (dev-only).

RU: Генерирует `docs/graph/graph.json` строго по SoT `docs/graph/GRAPHMAP_SPEC.md`.
EN: Deterministically builds `docs/graph/graph.json` per `docs/graph/GRAPHMAP_SPEC.md`.

Non-goals:
- No inferred/semantic edges
- No placeholder/UNKNOWN nodes
- No absolute paths, secrets, tokens, UUIDs, timestamps in output
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Optional

RE_MD_LINK = re.compile(r"\]\((?P<target>[^)]+)\)")
RE_PATH_LINE = re.compile(r"(?P<path>[A-Za-z0-9_\-./]+\.[A-Za-z0-9]+):(?P<line>\d{1,6})")

INPUT_GLOBS: tuple[str, ...] = (
    "AGENTS.md",
    "docs/graph/GRAPHMAP_SPEC.md",
    "docs/agents/index.md",
    "docs/orchestration/**/*.md",
    "docs/audit/**/*.md",
    ".cursor/agents/*.md",
)

MODULE_ROOTS: tuple[str, ...] = ("core", "app", "providers", "tests", "frontend", "ios", "deploy")

NODE_TYPES: frozenset[str] = frozenset(
    {"topic", "module", "document", "agent", "invariant", "test", "risk"}
)
EDGE_TYPES: frozenset[str] = frozenset(
    {"defines", "constrains", "implements", "validates", "references", "risks"}
)

LEVEL_TAGS: frozenset[str] = frozenset(
    {"theme", "project", "architecture", "module", "safety", "execution"}
)


@dataclass(frozen=True)
class Node:
    id: str
    type: str
    label: str
    path: Optional[str] = None
    tags: Optional[tuple[str, ...]] = None


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    type: str
    evidence: Optional[tuple[str, ...]] = None


def _repo_root() -> Path:
    """
    RU: Определяем корень репозитория детерминированно и независимо от cwd.
    EN: Resolve repository root deterministically and independent of cwd.

    Priority:
    1) `git rev-parse --show-toplevel`
    2) Walk up from this script to find `.git` or `AGENTS.md`
    """
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if out:
            return Path(out)
    except Exception:
        pass

    here = Path(__file__).resolve()
    for parent in [here.parent] + list(here.parents):
        if (parent / ".git").exists() or (parent / "AGENTS.md").exists():
            return parent

    return Path.cwd()


def _posix(p: Path) -> str:
    return p.as_posix()


def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="utf-8", errors="replace")


def _iter_input_files(repo: Path) -> list[Path]:
    files: set[Path] = set()
    for pattern in INPUT_GLOBS:
        for p in repo.glob(pattern):
            if p.is_file():
                files.add(p)
    return sorted(files, key=lambda p: _posix(p.relative_to(repo)))


def _strip_fragment_and_query(raw: str) -> str:
    return raw.split("#", 1)[0].split("?", 1)[0].strip()


def _normalize_rel_path(repo: Path, src_file: Path, raw: str) -> Optional[str]:
    raw = raw.strip()
    if not raw or raw.startswith("#"):
        return None
    if re.match(r"^(https?:|mailto:)", raw, flags=re.IGNORECASE):
        return None

    cleaned = _strip_fragment_and_query(raw)
    if not cleaned:
        return None

    resolved = (src_file.parent / cleaned).resolve()
    try:
        rel = resolved.relative_to(repo.resolve())
    except Exception:
        return None

    return _posix(rel)


def _node_id_for_path(node_type: str, rel_path: str) -> str:
    # Only strip a literal leading "./" (do NOT strip leading ".cursor/").
    if rel_path.startswith("./"):
        rel_path = rel_path[2:]
    if node_type == "agent":
        # Use file stem for agent IDs (frontmatter name parsing not implemented here).
        name = Path(rel_path).stem
        return f"agent:{name}"
    if node_type == "module":
        return f"module:{rel_path.rstrip('/')}"
    return f"doc:{rel_path}"


def _guess_node_type(rel_path: str) -> str:
    if rel_path.startswith("./"):
        rel_path = rel_path[2:]
    if rel_path.startswith(".cursor/agents/") and rel_path.endswith(".md"):
        return "agent"
    if rel_path.startswith("tests/") or (
        rel_path.startswith("ios/") and rel_path.endswith("Tests.swift")
    ):
        return "test"
    if rel_path.startswith("docs/"):
        return "document"
    if rel_path in MODULE_ROOTS or rel_path.rstrip("/") in MODULE_ROOTS:
        return "module"
    if rel_path.endswith("/"):
        root = rel_path.rstrip("/").split("/", 1)[0]
        if root in MODULE_ROOTS:
            return "module"
    return "document"


def _default_tags_for_path(rel_path: str, node_type: str) -> tuple[str, ...]:
    if rel_path.startswith("./"):
        rel_path = rel_path[2:]
    tags: list[str] = []

    if node_type == "module":
        tags.append("module")
    if node_type == "test":
        tags.append("execution")

    if rel_path == "AGENTS.md":
        tags.extend(["project", "safety"])
    elif rel_path.startswith("docs/orchestration/") or rel_path.startswith("docs/architecture/"):
        tags.append("architecture")
    elif rel_path.startswith("docs/safety/") or rel_path.startswith("docs/security/"):
        tags.append("safety")
    elif rel_path.startswith("docs/roadmap/"):
        tags.append("project")
    elif rel_path.startswith("docs/audit/"):
        tags.append("architecture")
    elif rel_path.startswith(".cursor/agents/"):
        tags.append("project")

    # Dedup while preserving deterministic order.
    seen: set[str] = set()
    out: list[str] = []
    for t in tags:
        if t in LEVEL_TAGS and t not in seen:
            seen.add(t)
            out.append(t)
    return tuple(out)


def _extract_markdown_links_by_line(text: str) -> Iterator[tuple[int, str]]:
    for idx, line in enumerate(text.splitlines(), start=1):
        for m in RE_MD_LINK.finditer(line):
            yield idx, m.group("target")


def _extract_path_line_tokens_by_line(text: str) -> Iterator[tuple[int, str, int]]:
    for idx, line in enumerate(text.splitlines(), start=1):
        for m in RE_PATH_LINE.finditer(line):
            yield idx, m.group("path"), int(m.group("line"))


def _stable_sorted_unique(items: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(items)))


def _dbg(enabled: bool, msg: str) -> None:
    if enabled:
        print(f"[graphmap] {msg}", file=sys.stderr)


def _validate_schema(graph: dict) -> None:
    allowed_root = {"schema_version", "generated_from", "nodes", "edges"}
    extra_root = set(graph.keys()) - allowed_root
    if extra_root:
        raise ValueError(f"extra root keys: {sorted(extra_root)}")

    if graph.get("schema_version") != "1.0":
        raise ValueError("schema_version must be '1.0'")

    if not isinstance(graph.get("nodes"), list) or not isinstance(graph.get("edges"), list):
        raise ValueError("nodes/edges must be lists")

    if "generated_from" in graph:
        gf = graph["generated_from"]
        if not isinstance(gf, dict):
            raise ValueError("generated_from must be an object")
        allowed_gf = {"repo_ref", "inputs"}
        extra_gf = set(gf.keys()) - allowed_gf
        if extra_gf:
            raise ValueError(f"extra generated_from keys: {sorted(extra_gf)}")
        if "repo_ref" not in gf or "inputs" not in gf:
            raise ValueError("generated_from must contain repo_ref and inputs")
        if not isinstance(gf["inputs"], list):
            raise ValueError("generated_from.inputs must be a list")

    allowed_node = {"id", "type", "label", "path", "tags"}
    for i, node in enumerate(graph["nodes"]):
        if not isinstance(node, dict):
            raise ValueError(f"node[{i}] must be object")
        extra = set(node.keys()) - allowed_node
        if extra:
            raise ValueError(f"node[{i}] extra keys: {sorted(extra)}")
        for req in ("id", "type", "label"):
            if req not in node:
                raise ValueError(f"node[{i}] missing {req}")
        if node["type"] not in NODE_TYPES:
            raise ValueError(f"node[{i}] invalid type: {node['type']}")
        if "path" in node and (node["path"].startswith("/") or node["path"].startswith("~")):
            raise ValueError(f"node[{i}] path must be repo-relative: {node['path']}")
        if "tags" in node:
            if not isinstance(node["tags"], list):
                raise ValueError(f"node[{i}] tags must be list")

    allowed_edge = {"source", "target", "type", "evidence"}
    node_ids = {n["id"] for n in graph["nodes"]}
    for i, edge in enumerate(graph["edges"]):
        if not isinstance(edge, dict):
            raise ValueError(f"edge[{i}] must be object")
        extra = set(edge.keys()) - allowed_edge
        if extra:
            raise ValueError(f"edge[{i}] extra keys: {sorted(extra)}")
        for req in ("source", "target", "type"):
            if req not in edge:
                raise ValueError(f"edge[{i}] missing {req}")
        if edge["type"] not in EDGE_TYPES:
            raise ValueError(f"edge[{i}] invalid type: {edge['type']}")
        if edge["source"] not in node_ids or edge["target"] not in node_ids:
            raise ValueError(f"edge[{i}] references missing node")
        if "evidence" in edge:
            if not isinstance(edge["evidence"], list):
                raise ValueError(f"edge[{i}] evidence must be list")
            for ev in edge["evidence"]:
                if not isinstance(ev, str) or ":" not in ev:
                    raise ValueError(f"edge[{i}] invalid evidence token: {ev!r}")
                p, line = ev.rsplit(":", 1)
                if not line.isdigit():
                    raise ValueError(f"edge[{i}] invalid evidence line: {ev!r}")
                if p.startswith("/") or p.startswith("~"):
                    raise ValueError(f"edge[{i}] evidence must be repo-relative: {ev!r}")


def build_graph(repo: Path, *, debug: bool) -> tuple[list[Node], list[Edge]]:
    # Error handling rule: if an input file cannot be parsed, we skip it.
    input_files = _iter_input_files(repo)

    nodes: dict[str, Node] = {}
    edges: list[Edge] = []

    def ensure_node_for_file(rel_path: str) -> Optional[str]:
        node_type = _guess_node_type(rel_path)
        if node_type not in NODE_TYPES:
            # Spec: drop node if cannot type.
            _dbg(debug, f"skip node (untypable): {rel_path} -> {node_type}")
            return None

        node_id = _node_id_for_path(node_type, rel_path)
        if node_id in nodes:
            return node_id

        tags = _default_tags_for_path(rel_path, node_type)
        nodes[node_id] = Node(
            id=node_id,
            type=node_type,
            label=rel_path,
            path=rel_path if not rel_path.endswith("/") else rel_path,
            tags=tags or None,
        )
        return node_id

    def ensure_module_root_for_path(rel_path: str) -> Optional[str]:
        parts = Path(rel_path).parts
        if not parts:
            return None
        root = parts[0]
        if root not in MODULE_ROOTS:
            return None
        module_path = f"{root}/"
        module_id = _node_id_for_path("module", root)
        if module_id not in nodes:
            nodes[module_id] = Node(
                id=module_id,
                type="module",
                label=root,
                path=module_path,
                tags=("module",),
            )
        return module_id

    def add_edge(
        *,
        source_id: str,
        target_id: str,
        edge_type: str,
        evidence: Optional[tuple[str, ...]] = None,
    ) -> None:
        if edge_type not in EDGE_TYPES:
            return
        # Spec: if edge references missing nodes, drop it.
        if source_id not in nodes or target_id not in nodes:
            return
        edges.append(Edge(source=source_id, target=target_id, type=edge_type, evidence=evidence))

    # Seed: create nodes for all input files.
    for src_abs in input_files:
        rel_src = _posix(src_abs.relative_to(repo))
        ensure_node_for_file(rel_src)

    # Parse each input file for explicit sources.
    for src_abs in input_files:
        rel_src = _posix(src_abs.relative_to(repo))
        src_id = ensure_node_for_file(rel_src)
        if not src_id:
            continue

        try:
            text = _read_text(src_abs)
        except Exception:
            # Skip unreadable input per spec.
            _dbg(debug, f"skip source (unreadable): {rel_src}")
            continue

        for line_no, raw_target in _extract_markdown_links_by_line(text):
            rel_target = _normalize_rel_path(repo, src_abs, raw_target)
            if rel_target is None:
                continue
            target_abs = (repo / rel_target).resolve()
            if not target_abs.is_file():
                # Spec: skip unresolved link edges.
                _dbg(debug, f"skip edge (missing file): {rel_src}:{line_no} -> {rel_target}")
                continue

            tgt_id = ensure_node_for_file(rel_target)
            if not tgt_id:
                continue

            evidence = (f"{rel_src}:{line_no}",)
            add_edge(source_id=src_id, target_id=tgt_id, edge_type="references", evidence=evidence)

            module_id = ensure_module_root_for_path(rel_target)
            if module_id is not None:
                add_edge(
                    source_id=src_id, target_id=module_id, edge_type="references", evidence=evidence
                )

        for line_no, raw_path, token_line in _extract_path_line_tokens_by_line(text):
            rel_target = _normalize_rel_path(repo, src_abs, raw_path)
            if rel_target is None:
                continue
            target_abs = (repo / rel_target).resolve()
            if not target_abs.is_file():
                _dbg(
                    debug,
                    f"skip token edge (missing file): {rel_src}:{line_no} -> {rel_target}:{token_line}",
                )
                continue

            tgt_id = ensure_node_for_file(rel_target)
            if not tgt_id:
                continue

            evidence = (f"{rel_src}:{line_no}", f"{rel_target}:{token_line}")
            add_edge(source_id=src_id, target_id=tgt_id, edge_type="references", evidence=evidence)

            module_id = ensure_module_root_for_path(rel_target)
            if module_id is not None:
                add_edge(
                    source_id=src_id, target_id=module_id, edge_type="references", evidence=evidence
                )

    # Minimal agent registration mapping: docs/agents/index.md mentions .cursor/agents/*.
    agents_index = repo / "docs/agents/index.md"
    if agents_index.is_file():
        try:
            idx_id = ensure_node_for_file("docs/agents/index.md")
            text = _read_text(agents_index)
        except Exception:
            text = ""
            idx_id = ""

        if text and idx_id:
            for line_no, line in enumerate(text.splitlines(), start=1):
                m = re.search(r"(?P<path>\.cursor/agents/[A-Za-z0-9_\-]+\.md)", line)
                if not m:
                    continue
                rel_target = m.group("path")
                target_abs = (repo / rel_target).resolve()
                if not target_abs.is_file():
                    _dbg(debug, f"skip agent index edge (missing file): {rel_target}")
                    continue

                agent_id = ensure_node_for_file(rel_target)
                if not agent_id:
                    continue

                evidence = (f"docs/agents/index.md:{line_no}",)
                add_edge(
                    source_id=idx_id, target_id=agent_id, edge_type="references", evidence=evidence
                )

    # Determinism: stable ordering of nodes/edges
    node_list = sorted(nodes.values(), key=lambda n: n.id)
    edge_list = sorted(edges, key=lambda e: (e.source, e.target, e.type, e.evidence or ()))

    # Drop edges that reference missing nodes (if any were dropped) deterministically.
    node_ids = {n.id for n in node_list}
    edge_list = [e for e in edge_list if e.source in node_ids and e.target in node_ids]

    return node_list, edge_list


def _graph_to_dict(nodes: list[Node], edges: list[Edge]) -> dict:
    graph: dict = {
        "schema_version": "1.0",
        "generated_from": {
            "repo_ref": "origin/main",
            "inputs": list(INPUT_GLOBS),
        },
        "nodes": [],
        "edges": [],
    }

    for n in nodes:
        obj: dict = {"id": n.id, "type": n.type, "label": n.label}
        if n.path is not None:
            obj["path"] = n.path
        if n.tags is not None:
            obj["tags"] = list(n.tags)
        graph["nodes"].append(obj)

    for e in edges:
        obj = {"source": e.source, "target": e.target, "type": e.type}
        if e.evidence is not None:
            obj["evidence"] = list(e.evidence)
        graph["edges"].append(obj)

    _validate_schema(graph)
    return graph


def main() -> None:
    parser = argparse.ArgumentParser(description="Build GraphMap graph.json deterministically.")
    parser.add_argument("--out", required=True, help="Output path (e.g., docs/graph/graph.json)")
    parser.add_argument("--debug", action="store_true", help="Verbose stderr logs (dev-only)")
    args = parser.parse_args()

    repo = _repo_root()
    debug = bool(args.debug)

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = repo / out_path

    nodes, edges = build_graph(repo, debug=debug)
    graph = _graph_to_dict(nodes, edges)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Stable formatting: sorted keys, fixed indentation, trailing newline.
    out_path.write_text(
        json.dumps(graph, ensure_ascii=False, sort_keys=True, indent=2) + "\n", "utf-8"
    )

    print(f"OK: wrote {out_path} (nodes={len(nodes)}, edges={len(edges)})")


if __name__ == "__main__":
    main()
