"""
MCP Server for RAG evaluation.

Thin wrapper over RagEvaluator from rag_builder.evaluation.
"""

from __future__ import annotations

import warnings

# Suppress all warnings immediately, before any other imports
warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="importlib._bootstrap")
warnings.simplefilter("ignore", DeprecationWarning)

import json
import os

from fastmcp import FastMCP

from donkit_ragops.rag_builder.evaluation import RagEvaluator
from donkit_ragops.schemas.tool_schemas import BatchEvaluationArgs

server = FastMCP(
    "rag-evaluation",
)


@server.tool(
    name="evaluate_batch",
    description=(
        "Run batch evaluation from a CSV or JSON file. "
        "Input fields: 'question', 'answer' (optional), 'relevant_passage'/'document'. "
        "Calculates Precision, Recall, Accuracy for retrieval."
    ).strip(),
)
async def evaluate_batch(args: BatchEvaluationArgs) -> str:
    result = await RagEvaluator.evaluate_batch(
        input_path=args.input_path,
        project_id=args.project_id,
        rag_service_url=args.rag_service_url,
        output_csv_path=args.output_csv_path,
        evaluation_service_url=args.evaluation_service_url,
        max_concurrent=args.max_concurrent,
        max_questions=args.max_questions,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


def main() -> None:
    server.run(
        transport="stdio",
        log_level=os.getenv("RAGOPS_LOG_LEVEL", "CRITICAL"),
        show_banner=False,
    )


if __name__ == "__main__":
    main()
