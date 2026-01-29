from __future__ import annotations

import json
import os
import re
import socket
import warnings

# Suppress all warnings immediately, before any other imports
warnings.filterwarnings("ignore")
# Suppress warnings from importlib bootstrap (SWIG-related)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="importlib._bootstrap")
# Suppress all DeprecationWarnings globally
warnings.simplefilter("ignore", DeprecationWarning)

from fastmcp import FastMCP
from neo4j import GraphDatabase
from pydantic import BaseModel, Field

from donkit_ragops.schemas.config_schemas import GraphOptions


def _safe_identifier(raw: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", raw.strip())
    if not cleaned:
        return fallback
    if cleaned[0].isdigit():
        return f"{fallback}_{cleaned}"
    return cleaned


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


class GraphQueryArgs(BaseModel):
    query: str = Field(description="Search query text")
    k: int = Field(default=5, description="Number of top results to return")
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


class GraphInspectArgs(BaseModel):
    limit: int = Field(default=50, description="Max number of nodes/relationships to return")
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


class GraphHealthArgs(BaseModel):
    graph_database_uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j URI to check from the current runtime.",
    )
    timeout_seconds: float = Field(default=2.5, description="Connection timeout in seconds")


server = FastMCP("rag-graph-query")


@server.tool(
    name="graph_search",
    description=(
        "Search for relevant chunks using Neo4j fulltext index and expand neighbors. "
        "Returns chunk content and metadata."
    ),
)
async def graph_search(args: GraphQueryArgs) -> str:
    password = args.graph_password or os.getenv("NEO4J_PASSWORD", "neo4j123")
    node_label = _safe_identifier(args.graph_options.node_label, "Chunk")
    edge_type = _safe_identifier(args.graph_options.edge_type, "NEXT")
    index_name = _safe_identifier(args.graph_options.index_name, "chunk_content")

    graph_uri = _normalize_graph_uri(args.graph_database_uri)
    driver = GraphDatabase.driver(graph_uri, auth=(args.graph_user, password))
    try:
        with driver.session() as session:
            records = session.run(
                (
                    "CALL db.index.fulltext.queryNodes($index_name, $search_query) "
                    "YIELD node, score "
                    "RETURN node, score "
                    "ORDER BY score DESC "
                    "LIMIT $limit"
                ),
                index_name=index_name,
                search_query=args.query,
                limit=args.k,
            )
            node_ids = [record["node"].id for record in records]

            if not node_ids:
                return json.dumps(
                    {"query": args.query, "total_results": 0, "documents": []},
                    ensure_ascii=False,
                    indent=2,
                )

            max_hops = max(0, int(args.graph_options.max_hops))
            limit = max(args.k * (max_hops + 1), args.k)
            results = session.run(
                (
                    "UNWIND $node_ids AS nid "
                    "MATCH (n) WHERE id(n) = nid "
                    f"MATCH (n)-[:{edge_type}*0..{max_hops}]-(m:{node_label}) "
                    "RETURN DISTINCT m "
                    "LIMIT $limit"
                ),
                node_ids=node_ids,
                limit=limit,
            )

            documents = []
            for record in results:
                node = record["m"]
                props = dict(node)
                documents.append(
                    {
                        "content": props.get("content", ""),
                        "metadata": {
                            "document_id": props.get("document_id"),
                            "filename": props.get("filename"),
                            "page_number": props.get("page_number"),
                            "chunk_index": props.get("chunk_index"),
                            "type": props.get("type"),
                        },
                    }
                )

            response = {
                "query": args.query,
                "total_results": len(documents),
                "documents": documents,
            }
            return json.dumps(response, ensure_ascii=False, indent=2)
    finally:
        driver.close()


@server.tool(
    name="graph_overview",
    description=(
        "Return a lightweight view of the graph: counts plus sample nodes and relationships."
    ),
)
async def graph_overview(args: GraphInspectArgs) -> str:
    password = args.graph_password or os.getenv("NEO4J_PASSWORD", "neo4j123")
    node_label = _safe_identifier(args.graph_options.node_label, "Chunk")
    edge_type = _safe_identifier(args.graph_options.edge_type, "NEXT")

    graph_uri = _normalize_graph_uri(args.graph_database_uri)
    driver = GraphDatabase.driver(graph_uri, auth=(args.graph_user, password))
    try:
        with driver.session() as session:
            total_nodes = session.run(
                (f"MATCH (n:{node_label}) RETURN count(n) AS total_nodes"),
            ).single()["total_nodes"]
            total_rels = session.run(
                (
                    f"MATCH (:{node_label})-[r:{edge_type}]->(:{node_label}) "
                    "RETURN count(r) AS total_rels"
                ),
            ).single()["total_rels"]

            node_records = session.run(
                (
                    f"MATCH (n:{node_label}) "
                    "RETURN n "
                    "ORDER BY n.document_id, n.chunk_index "
                    "LIMIT $limit"
                ),
                limit=max(0, int(args.limit)),
            )
            nodes = []
            for record in node_records:
                node = record["n"]
                props = dict(node)
                nodes.append(
                    {
                        "id": props.get("id"),
                        "document_id": props.get("document_id"),
                        "chunk_index": props.get("chunk_index"),
                        "filename": props.get("filename"),
                        "page_number": props.get("page_number"),
                        "type": props.get("type"),
                    }
                )

            rel_records = session.run(
                (
                    f"MATCH (a:{node_label})-[r:{edge_type}]->(b:{node_label}) "
                    "RETURN a.id AS src, b.id AS dst "
                    "LIMIT $limit"
                ),
                limit=max(0, int(args.limit)),
            )
            relationships = [{"src": rec["src"], "dst": rec["dst"]} for rec in rel_records]

            response = {
                "node_label": node_label,
                "edge_type": edge_type,
                "total_nodes": total_nodes,
                "total_relationships": total_rels,
                "nodes": nodes,
                "relationships": relationships,
            }
            return json.dumps(response, ensure_ascii=False, indent=2)
    finally:
        driver.close()


@server.tool(
    name="graph_health",
    description="Check Neo4j connectivity with a TCP connect test.",
)
async def graph_health(args: GraphHealthArgs) -> str:
    timeout = max(0.1, float(args.timeout_seconds))
    uri = _normalize_graph_uri(args.graph_database_uri)
    host_port = uri.replace("bolt://", "").replace("neo4j://", "")
    if "/" in host_port:
        host_port = host_port.split("/", 1)[0]
    if ":" in host_port:
        host, port_str = host_port.rsplit(":", 1)
        port = int(port_str)
    else:
        host = host_port
        port = 7687

    result: dict[str, object] = {
        "graph_database_uri": args.graph_database_uri,
        "host": host,
        "port": port,
        "ok": False,
    }
    try:
        with socket.create_connection((host, port), timeout=timeout):
            result["ok"] = True
    except Exception as e:
        result["error"] = str(e)

    return json.dumps(result, ensure_ascii=False, indent=2)


def main() -> None:
    server.run(
        transport="stdio",
        log_level=os.getenv("RAGOPS_LOG_LEVEL", "CRITICAL"),
        show_banner=False,
    )


if __name__ == "__main__":
    main()
