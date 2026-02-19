"""Local tools for document reading/processing."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from donkit_ragops.agent.local_tools.tools import AgentTool
from donkit_ragops.schemas.tool_schemas import ProcessDocumentsArgs

if TYPE_CHECKING:
    from donkit.llm import LLMModelAbstract


def tool_process_documents(
    llm_model: LLMModelAbstract | None = None,
    progress_callback: Any | None = None,
) -> AgentTool:
    """Tool for processing documents from various formats."""

    async def _handler(args: dict[str, Any]) -> str:
        from donkit_ragops.rag_builder.document_processing import DocumentProcessor

        parsed = ProcessDocumentsArgs(**args)

        async def file_progress(current: int, total: int, message: str) -> None:
            if progress_callback:
                progress_callback(current, total, message)

        result = await DocumentProcessor.process_documents(
            source_path=parsed.source_path,
            project_id=parsed.project_id,
            reading_format=parsed.reading_format.value,
            use_llm=parsed.use_llm,
            llm_model=llm_model,
            reader_progress_callback=progress_callback,
            file_progress_callback=file_progress if progress_callback else None,
        )
        return json.dumps(result, indent=2, ensure_ascii=False)

    schema = ProcessDocumentsArgs.model_json_schema()

    return AgentTool(
        name="process_documents",
        description=(
            "Process documents from various formats (PDF, DOCX, PPTX, XLSX, images, etc.) "
            "and convert them to text/json/markdown. "
            "Supports: PDF, DOCX/DOC, PPTX, XLSX/XLS, TXT, CSV, JSON, Images (PNG/JPG). "
            "Can process: directory (recursively), single file, or comma-separated file list. "
            "Output is saved to projects/<project_id>/processed/ directory. "
            "Returns the path to the processed directory which can be used by chunk_documents tool. "
            "Don't use this tool to get documents content! It returns only path to processed directory."
        ),
        parameters=schema,
        handler=_handler,
        is_async=True,
    )
