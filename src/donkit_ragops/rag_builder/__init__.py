"""
RAG Builder - Core business logic for RAG pipelines.

This module contains reusable components extracted from MCP servers,
allowing independent usage without FastMCP dependency.

Usage:

    # Embeddings
    from donkit_ragops.rag_builder.embeddings import create_embedder
    embedder = create_embedder("openai")

    # Config validation
    from donkit_ragops.rag_builder.config import validate_rag_config
    config = validate_rag_config(rag_config, project_id="my-project")

    # Deployment
    from donkit_ragops.rag_builder.deployment import EnvFileGenerator, ComposeManager
    env_content = EnvFileGenerator.generate(project_id, rag_config)

    # Vectorstore
    from donkit_ragops.rag_builder.vectorstore import VectorstoreService
    summary = await VectorstoreService.load(...)

    # Evaluation
    from donkit_ragops.rag_builder.evaluation import RAGMetrics, RagEvaluator
    metrics = RAGMetrics.compute_retrieval_metrics(retrieved, relevant)

    # Document processing
    from donkit_ragops.rag_builder.document_processing import DocumentProcessor
    result = await DocumentProcessor.process_documents(...)

    # Chunking
    from donkit_ragops.rag_builder.chunking import ChunkingService
    result = ChunkingService.chunk_documents(...)

    # Query
    from donkit_ragops.rag_builder.query import RagQueryClient
    result = await RagQueryClient.search_documents(...)
"""

from .chunking import ChunkingService
from .config import RagConfigValidator, validate_rag_config
from .deployment import ComposeManager, DockerEnvironment, EnvFileGenerator, LLMProviderCredentials
from .document_processing import DocumentProcessor, PathNormalizer
from .embeddings import EmbedderFactory, create_embedder
from .evaluation import DocumentNormalizer, RagEvaluator, RAGMetrics
from .pipeline import PipelineBuildResult, RagPipelineOrchestrator
from .query import RagQueryClient
from .vectorstore import VectorstoreLoader, VectorstoreLoadResult, VectorstoreService

__all__ = [
    # Embeddings
    "EmbedderFactory",
    "create_embedder",
    # Config
    "RagConfigValidator",
    "validate_rag_config",
    # Deployment
    "EnvFileGenerator",
    "LLMProviderCredentials",
    "DockerEnvironment",
    "ComposeManager",
    # Vectorstore
    "VectorstoreLoader",
    "VectorstoreLoadResult",
    "VectorstoreService",
    # Evaluation
    "RAGMetrics",
    "DocumentNormalizer",
    "RagEvaluator",
    # Document processing
    "PathNormalizer",
    "DocumentProcessor",
    # Chunking
    "ChunkingService",
    # Pipeline
    "RagPipelineOrchestrator",
    "PipelineBuildResult",
    # Query
    "RagQueryClient",
]
