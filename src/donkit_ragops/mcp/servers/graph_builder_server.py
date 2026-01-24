from __future__ import annotations

import json
import os
import re
import time
import warnings
from pathlib import Path
from typing import Any

# Suppress all warnings immediately, before any other imports
warnings.filterwarnings("ignore")
# Suppress warnings from importlib bootstrap (SWIG-related)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="importlib._bootstrap")
# Suppress all DeprecationWarnings globally
warnings.simplefilter("ignore", DeprecationWarning)

from fastmcp import FastMCP
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
from pydantic import BaseModel, Field

from donkit_ragops.schemas.config_schemas import GraphOptions


def _safe_identifier(raw: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", raw.strip())
    if not cleaned:
        return fallback
    if cleaned[0].isdigit():
        return f"{fallback}_{cleaned}"
    return cleaned


def _collect_json_files(chunks_path: str) -> list[Path]:
    json_files: list[Path] = []
    if "," in chunks_path:
        file_paths = [p.strip() for p in chunks_path.split(",")]
        for file_path_str in file_paths:
            file_path = Path(file_path_str)
            if file_path.exists() and file_path.is_file() and file_path.suffix == ".json":
                json_files.append(file_path)
    elif Path(chunks_path).is_file():
        file_path = Path(chunks_path)
        if file_path.suffix == ".json":
            json_files.append(file_path)
        else:
            raise ValueError(f"Error: file must be JSON, got {file_path.suffix}")
    elif Path(chunks_path).is_dir():
        dir_path = Path(chunks_path)
        json_files = sorted([f for f in dir_path.iterdir() if f.is_file() and f.suffix == ".json"])
    else:
        raise ValueError(f"Error: path not found: {chunks_path}")
    if not json_files:
        raise ValueError(f"Error: no JSON files found in {chunks_path}")
    return json_files


def _running_in_docker() -> bool:
    if os.path.exists("/.dockerenv"):
        return True
    try:
        with open("/proc/1/cgroup", "r", encoding="utf-8") as f:
            data = f.read()
        return "docker" in data or "containerd" in data
    except OSError:
        return False


def _normalize_graph_uri(graph_uri: str) -> str:
    if _running_in_docker():
        return graph_uri
    if "neo4j" in graph_uri and "localhost" not in graph_uri:
        return "bolt://localhost:7687"
    return graph_uri


def _wait_for_neo4j(driver: GraphDatabase.driver, retries: int = 10, delay: float = 1.0) -> None:
    last_exc: Exception | None = None
    for _ in range(retries):
        try:
            with driver.session() as session:
                session.run("RETURN 1")
            return
        except (ServiceUnavailable, OSError) as exc:
            last_exc = exc
            time.sleep(delay)
    if last_exc:
        raise last_exc


class GraphBuildArgs(BaseModel):
    chunks_path: str = Field(
        description=(
            "Path to chunked files: directory, single JSON file, or comma-separated list. "
            "Examples: '/path/to/chunked/', '/path/file.json', "
            "'/path/file1.json,/path/file2.json'"
        )
    )
    project_id: str = Field(description="Project ID for the graph build job.")
    graph_database_uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j URI outside docker (e.g., bolt://localhost:7687)",
    )
    graph_user: str = Field(default="neo4j", description="Neo4j username")
    graph_password: str | None = Field(
        default=None,
        description="Neo4j password. If unset, uses NEO4J_PASSWORD env or 'neo4j'.",
    )
    graph_options: GraphOptions = Field(default_factory=GraphOptions)


server = FastMCP("rag-graph-builder")


@server.tool(
    name="graph_build",
    description=(
        "Load chunk JSON files into Neo4j as Chunk nodes and connect adjacent chunks. "
        "Creates a fulltext index for content-based retrieval."
    ),
)
async def graph_build(args: GraphBuildArgs) -> str:
    json_files = _collect_json_files(args.chunks_path)
    password = args.graph_password or os.getenv("NEO4J_PASSWORD", "neo4j123")
    node_label = _safe_identifier(args.graph_options.node_label, "Chunk")
    edge_type = _safe_identifier(args.graph_options.edge_type, "NEXT")
    index_name = _safe_identifier(args.graph_options.index_name, "chunk_content")

    graph_uri = _normalize_graph_uri(args.graph_database_uri)
    driver = GraphDatabase.driver(graph_uri, auth=(args.graph_user, password))
    chunks_loaded = 0
    rels_created = 0
    files_loaded = 0

    try:
        _wait_for_neo4j(driver)
        with driver.session() as session:
            constraint_name = _safe_identifier(f"{node_label}_id_unique", "chunk_id_unique")
            session.run(
                (
                    f"CREATE CONSTRAINT {constraint_name} IF NOT EXISTS "
                    f"FOR (n:{node_label}) REQUIRE n.id IS UNIQUE"
                )
            )
            session.run(
                (
                    f"CREATE FULLTEXT INDEX {index_name} IF NOT EXISTS "
                    f"FOR (n:{node_label}) ON EACH [n.content]"
                )
            )

            for file_path in json_files:
                with file_path.open("r", encoding="utf-8") as f:
                    chunks = json.load(f)
                if not isinstance(chunks, list):
                    continue

                rows: list[dict[str, Any]] = []
                by_doc: dict[str, list[dict[str, Any]]] = {}
                for chunk in chunks:
                    if not isinstance(chunk, dict):
                        continue
                    content = str(chunk.get("page_content", ""))
                    metadata = chunk.get("metadata", {}) or {}
                    document_id = metadata.get("document_id") or metadata.get("filename") or "unknown"
                    chunk_index = int(metadata.get("chunk_index", 0))
                    filename = metadata.get("filename")
                    page_number = metadata.get("page_number")
                    chunk_id = f"{document_id}:{chunk_index}"
                    row = {
                        "id": chunk_id,
                        "content": content,
                        "document_id": document_id,
                        "chunk_index": chunk_index,
                        "filename": filename,
                        "page_number": page_number,
                        "type": metadata.get("type"),
                    }
                    rows.append(row)
                    by_doc.setdefault(document_id, []).append(row)

                if rows:
                    session.run(
                        (
                            f"UNWIND $rows AS row "
                            f"MERGE (c:{node_label} {{id: row.id}}) "
                            "SET c.content = row.content, "
                            "c.document_id = row.document_id, "
                            "c.chunk_index = row.chunk_index, "
                            "c.filename = row.filename, "
                            "c.page_number = row.page_number, "
                            "c.type = row.type"
                        ),
                        rows=rows,
                    )
                    chunks_loaded += len(rows)

                rel_rows: list[dict[str, str]] = []
                for _, doc_rows in by_doc.items():
                    ordered = sorted(doc_rows, key=lambda r: r["chunk_index"])
                    for left, right in zip(ordered, ordered[1:]):
                        rel_rows.append({"src": left["id"], "dst": right["id"]})

                if rel_rows:
                    session.run(
                        (
                            f"UNWIND $rels AS rel "
                            f"MATCH (a:{node_label} {{id: rel.src}}) "
                            f"MATCH (b:{node_label} {{id: rel.dst}}) "
                            f"MERGE (a)-[:{edge_type}]->(b)"
                        ),
                        rels=rel_rows,
                    )
                    rels_created += len(rel_rows)

                files_loaded += 1

        result = {
            "status": "success",
            "files_loaded": files_loaded,
            "chunks_loaded": chunks_loaded,
            "relationships_created": rels_created,
            "index_name": index_name,
            "node_label": node_label,
            "edge_type": edge_type,
        }
        return json.dumps(result, ensure_ascii=False, indent=2)
    finally:
        driver.close()


def main() -> None:
    server.run(
        transport="stdio",
        log_level=os.getenv("RAGOPS_LOG_LEVEL", "CRITICAL"),
        show_banner=False,
    )


if __name__ == "__main__":
    main()
