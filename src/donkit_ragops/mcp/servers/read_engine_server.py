"""
MCP Server for document reading/parsing.

Thin wrapper over DocumentProcessor from rag_builder.document_processing.
"""

import warnings

# Suppress all warnings immediately, before any other imports
warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="importlib._bootstrap")
warnings.simplefilter("ignore", DeprecationWarning)
import asyncio
import json
import os

from fastmcp import Context, FastMCP

from donkit_ragops.rag_builder.document_processing import DocumentProcessor
from donkit_ragops.schemas.tool_schemas import ProcessDocumentsArgs

server = FastMCP(
    "rag-read-engine",
)


@server.tool(
    name="process_documents",
    description=(
        "Process documents from various formats (PDF, DOCX, PPTX, XLSX, images, etc.) "
        "and convert them to text/json/markdown. "
        "Supports: PDF, DOCX/DOC, PPTX, XLSX/XLS, TXT, CSV, JSON, Images (PNG/JPG). "
        "Can process: directory (recursively), single file, or comma-separated file list. "
        "Output is saved to projects/<project_id>/processed/ directory. "
        "Returns the path to the processed directory which can be used by chunk_documents tool. "
        "Don't use this tool to get documents content! It returns only path to processed directory."
    ).strip(),
)
async def process_documents(args: ProcessDocumentsArgs, ctx: Context) -> str:
    main_loop = asyncio.get_event_loop()

    def reader_progress(current: int, total: int, message: str | None = None) -> None:
        try:
            asyncio.run_coroutine_threadsafe(
                ctx.report_progress(progress=current, total=total, message=message), main_loop
            )
        except Exception:
            pass

    async def file_progress(current: int, total: int, message: str) -> None:
        await ctx.report_progress(progress=current, total=total, message=message)

    result = await DocumentProcessor.process_documents(
        source_path=args.source_path,
        project_id=args.project_id,
        reading_format=args.reading_format.value,
        use_llm=args.use_llm,
        reader_progress_callback=reader_progress,
        file_progress_callback=file_progress,
    )
    return json.dumps(result, indent=2, ensure_ascii=False)


def main() -> None:
    server.run(
        transport="stdio",
        log_level=os.getenv("RAGOPS_LOG_LEVEL", "CRITICAL"),
        show_banner=False,
    )


if __name__ == "__main__":
    main()
