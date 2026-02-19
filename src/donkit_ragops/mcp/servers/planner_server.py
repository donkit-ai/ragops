from __future__ import annotations

import warnings

# Suppress all warnings immediately, before any other imports
warnings.filterwarnings("ignore")
# Suppress warnings from importlib bootstrap (SWIG-related)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="importlib._bootstrap")
# Suppress all DeprecationWarnings globally
warnings.simplefilter("ignore", DeprecationWarning)
import os

from fastmcp import FastMCP

from donkit_ragops.schemas.tool_schemas import RagConfigPlanArgs

server = FastMCP(
    "rag-config-planner",
)


@server.tool(
    name="rag_config_plan",
    description=(
        "Suggest a RAG configuration (vectorstore/chunking/retriever/ranker) "
        "for the given project and sources. "
        "IMPORTANT: When passing rag_config parameter, ensure embedder.embedder_type "
        "is explicitly set to match user's choice (openai, vertex, or azure_openai). "
        "Do not rely on defaults."
    ),
)
async def rag_config_plan(args: RagConfigPlanArgs) -> str:
    plan = args.rag_config.model_dump_json()
    return plan


def main() -> None:
    server.run(
        transport="stdio",
        log_level=os.getenv("RAGOPS_LOG_LEVEL", "CRITICAL"),
        show_banner=False,
    )


if __name__ == "__main__":
    main()
