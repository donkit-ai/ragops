"""Local tools for RAG evaluation."""

from __future__ import annotations

import json
from typing import Any

from donkit_ragops.agent.local_tools.tools import AgentTool
from donkit_ragops.schemas.tool_schemas import BatchEvaluationArgs


def tool_evaluate_batch() -> AgentTool:
    """Tool for running batch RAG evaluation."""

    async def _handler(args: dict[str, Any]) -> str:
        from donkit_ragops.rag_builder.evaluation import RagEvaluator

        parsed = BatchEvaluationArgs(**args)
        result = await RagEvaluator.evaluate_batch(
            input_path=parsed.input_path,
            project_id=parsed.project_id,
            rag_service_url=parsed.rag_service_url,
            output_csv_path=parsed.output_csv_path,
            evaluation_service_url=parsed.evaluation_service_url,
            max_concurrent=parsed.max_concurrent,
            max_questions=parsed.max_questions,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    schema = BatchEvaluationArgs.model_json_schema()

    return AgentTool(
        name="evaluate_batch",
        description=(
            "Run batch evaluation from a CSV or JSON file. "
            "Input fields: 'question', 'answer' (optional), 'relevant_passage'/'document'. "
            "Calculates Precision, Recall, Accuracy for retrieval."
        ),
        parameters=schema,
        handler=_handler,
        is_async=True,
    )
