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
from pydantic import BaseModel, Field

from donkit_ragops.rag_builder.evaluation import RagEvaluator

server = FastMCP(
    "rag-evaluation",
)


class BatchEvaluationArgs(BaseModel):
    input_path: str = Field(
        description=(
            "Path to input file (CSV or JSON) with fields: "
            "question, answer, relevant_passage/document"
        )
    )
    project_id: str = Field(description="Project ID for organizing results")
    output_csv_path: str | None = Field(
        default=None,
        description=(
            "Path to save results CSV. Defaults to projects/<project_id>/evaluation/results.csv"
        ),
    )
    rag_service_url: str = Field(
        default="http://localhost:8000",
        description="RAG service base URL (e.g., http://localhost:8000)",
    )
    evaluation_service_url: str | None = Field(
        default=None,
        description="Optional URL for external evaluation service (for generation metrics)",
    )
    max_concurrent: int = Field(default=5, description="Max concurrent requests to RAG service")
    max_questions: int | None = Field(
        default=None, description="Limit number of questions to process (for debugging)"
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
