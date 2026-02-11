# RAGOps Agent

[![PyPI version](https://badge.fury.io/py/donkit-ragops.svg)](https://badge.fury.io/py/donkit-ragops)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Optimal RAG in hours, not months.**

A smart, LLM-powered CLI agent that automates the entire lifecycle of Retrieval-Augmented Generation (RAG) pipelines — from creation and experimentation to deployment.
Forget spending months tweaking chunking strategies, embeddings, and vector DBs by hand. Just describe what you need, and let the agent run 100+ parallel experiments to discover what actually works for your data — fast, accurate, and infra-agnostic.

Built by [Donkit AI](https://donkit.ai/?utm_source=github) — Automated Context Engineering.

## 📚 Table of Contents

- [👥 Who is this for?](#who-is-this-for)
- [✨ Key Features](#key-features)
- [🎯 Main Capabilities](#main-capabilities)
- [⚡ Quick Install](#quick-install)
- [📦 Installation (Alternative Methods)](#installation-alternative-methods)
  - [Option A: Using pipx (Recommended)](#option-a-using-pipx-recommended)
  - [Option B: Using pip](#option-b-using-pip)
  - [Option C: Using Poetry (for development)](#option-c-using-poetry-for-development)
- [🚀 Quick Start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [Step 1: Install the package](#step-1-install-the-package)
  - [Step 2: Run the agent (first time)](#step-2-run-the-agent-first-time)
  - [Step 3: Start using the agent (local mode)](#step-3-start-using-the-agent-local-mode)
  - [Interactive Mode (REPL)](#interactive-mode-repl)
  - [Command-line Options](#command-line-options)
- [🔄 Agent Workflow](#agent-workflow)
- [🌐 Web UI](#web-ui)
- [☁️ SaaS Mode](#saas-mode)
- [🏢 Enterprise Mode](#enterprise-mode)
- [📊 Modes of work comparison](#modes-of-work-comparison)
- [🔌 MCP Servers](#mcp-servers)
  - [ragops-rag-planner](#ragops-rag-planner)
  - [ragops-read-engine](#ragops-read-engine)
  - [ragops-chunker](#ragops-chunker)
  - [ragops-vectorstore-loader](#ragops-vectorstore-loader)
  - [ragops-compose-manager](#ragops-compose-manager)
  - [ragops-rag-query](#ragops-rag-query)
  - [rag-evaluation](#rag-evaluation)
  - [donkit-ragops-mcp](#donkit-ragops-mcp)
- [💡 Examples](#examples)
  - [Basic RAG Pipeline](#basic-rag-pipeline)
  - [Custom Configuration](#custom-configuration)
  - [Multiple Projects](#multiple-projects)
- [🛠️ Development](#development)
  - [Prerequisites](#prerequisites-1)
  - [Running the CLI Locally](#running-the-cli-locally)
  - [Running Tests](#running-tests)
  - [Code Quality](#code-quality)
  - [Version Management](#version-management)
  - [Adding a New MCP Server](#adding-a-new-mcp-server)
  - [Adding a New LLM Provider](#adding-a-new-llm-provider)
- [🐳 Docker Compose Services](#docker-compose-services)
  - [Qdrant (Vector Database)](#qdrant-vector-database)
  - [Chroma (Vector Database)](#chroma-vector-database)
  - [Milvus (Vector Database)](#milvus-vector-database)
  - [RAG Service](#rag-service)
- [🏗️ Architecture](#architecture)
- [🔧 Troubleshooting](#troubleshooting)
- [📄 License](#license)
- [🔗 Related Projects](#related-projects)

## Who is this for?

- **AI Engineers** building assistants and agents
- **Teams** in need of accuracy-sensitive and multiagentic RAG where errors compound across steps
- **Organizations** aiming to reduce time-to-value for production AI deployments

## Key Features

* **Parallel Experimentation Engine** — Explores 100s of pipeline variations (chunking, vector DBs, prompts, rerankers, etc.) to find what performs best — in hours, not months.
* **Docker Compose orchestration** — Automated deployment of RAG infrastructure (vector DB, RAG service)
* **Built-in Evaluation & Scoring** — Automatically generates evaluation dataset (if needed), runs Q&A tests and scores pipeline accuracy on your real data.
* **Multiple LLM providers** — Supports Vertex AI (Recommended), OpenAI, Anthropic Claude, Azure OpenAI, Ollama, OpenRouter
* **Interactive Web UI** — Browser-based interface with real-time agent responses and visual project management
* **Session-scoped Checklists** — Structured workflow with clear stages, approvals, and progress tracking
* **Multi-mode Operation** — Local, SaaS, and Enterprise deployment options for any scale

## Main Capabilities
* **Interactive REPL** — Start an interactive session with readline history and autocompletion
* **Web UI** — Browser-based interface at http://localhost:8067 (`donkit-ragops-web`, auto-opens browser)
* **Docker Compose orchestration** — Automated deployment of RAG infrastructure (vector DB, RAG service)
* **Integrated MCP servers** — Built-in support for full RAG build pipeline (planning, reading, chunking, vector loading, querying, evaluation)
* **Checklist-driven workflow** — Each RAG project is structured as a checklist — with clear stages, approvals, and progress tracking
* **Session-scoped checklists** — Only current session checklists appear in the UI
* **SaaS mode** — Connect to Donkit cloud for experiments
* **Enterprise mode** — deploy to VPC or on-premises with no vendor lock-in (reach out to us via [https://donkit.ai](https://donkit.ai/?utm_source=github)) 

## Quick Install

The fastest way to install Donkit RAGOps. The installer automatically handles Python and dependencies.

**macOS / Linux:**
```bash
curl -sSL https://raw.githubusercontent.com/donkit-ai/ragops/main/scripts/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/donkit-ai/ragops/main/scripts/install.ps1 | iex
```

After installation:
```bash
donkit-ragops        # Start CLI agent
donkit-ragops-web    # Start Web UI (browser opens automatically at http://localhost:8067)
```

---

## Installation (Alternative Methods)

### Option A: Using pipx (Recommended)

```bash
# Install pipx if you don't have it
pip install pipx
pipx ensurepath

# Install donkit-ragops
pipx install donkit-ragops
```

### Option B: Using pip

```bash
pip install donkit-ragops
```

### Option C: Using Poetry (for development)

```bash
# Create a new project directory
mkdir ~/ragops-workspace
cd ~/ragops-workspace

# Initialize Poetry project
poetry init --no-interaction --python="^3.12"

# Add donkit-ragops
poetry add donkit-ragops

# Activate the virtual environment
poetry shell
```

After activation, you can run the agent with:
```bash
donkit-ragops
```

Or run directly without activating the shell:
```bash
poetry run donkit-ragops
```

## Quick Start

### Prerequisites

- **Python 3.12+** installed
- **Docker Desktop** installed and running (required for vector database)
  - **Windows users**: Docker Desktop with WSL2 backend is fully supported
- API key for your chosen LLM provider (Vertex AI, OpenAI, or Anthropic)

### Step 1: Install the package

```bash
pip install donkit-ragops
```

### Step 2: Run the agent (first time)

```bash
donkit-ragops
```

On first run, an **interactive setup wizard** will guide you through configuration:

1. Choose your LLM provider (Vertex AI, OpenAI, Anthropic, or Ollama)
2. Enter API key or credentials path
3. Optional: Configure log level
4. Configuration is saved to `.env` file automatically

**That's it!** No manual `.env` creation needed - the wizard handles everything.

### Reconfiguration

To reconfigure or change settings later:

```bash
# Run setup wizard to change configuration
donkit-ragops setup
```

The setup wizard allows you to:

**Local Mode:**
- Choose LLM provider (Vertex AI, OpenAI, Anthropic, Ollama, OpenRouter, Donkit)
- Configure API keys and credentials
- Set optional parameters (models, base URLs, etc.)

**SaaS Mode:**
- Login/logout with Donkit cloud
- Manage integrations (OpenRouter API keys, etc.)
- Configure cloud-based LLM providers

### Step 3: Start using the agent (local mode)

Tell the agent what you want to build:

```
> Create a RAG pipeline for my documents in /Users/myname/Documents/work_docs
```

The agent will automatically:
- ✅ Create a `projects/<project_id>/` directory
- ✅ Plan RAG configuration
- ✅ Process and chunk your documents
- ✅ Start Qdrant vector database (via Docker)
- ✅ Load data into the vector store
- ✅ Deploy RAG query service

### What gets created

```
./
├── .env                          # Your configuration (auto-created by wizard)
└── projects/
    └── my-project-abc123/        # Auto-created by agent
        ├── compose/              # Docker Compose files
        │   ├── docker-compose.yml
        │   └── .env
        ├── chunks/               # Processed document chunks
        └── rag_config.json       # RAG configuration
```

### Interactive Mode (REPL)

```bash
# Start interactive session
donkit-ragops

# With specific provider
donkit-ragops -p vertexai

# With custom model
donkit-ragops -p openai -m gpt-5.2

# Start in SaaS/enterprise mode
donkit-ragops --enterprise
```

### REPL Commands

Inside the interactive session, use these commands:

- `/help`, `/h`, `/?` — Show available commands
- `/exit`, `/quit`, `/q` — Exit the agent
- `/clear` — Clear conversation history and screen
- `/provider` — Switch LLM provider interactively
- `/model` — Switch LLM model interactively

### Command-line Options

- `-p, --provider` — Override LLM provider from settings
- `-m, --model` — Specify model name
- `-s, --system` — Custom system prompt
- `--local` — Force local mode (default)
- `--enterprise` — Force enterprise mode (requires setup with `donkit-ragops setup`)
- `--show-checklist/--no-checklist` — Toggle checklist panel (default: shown)

### Commands

```bash
# Setup wizard - configure Local or SaaS mode
donkit-ragops setup

# Health check
donkit-ragops ping

# Show current mode and authentication status
donkit-ragops status

# Auto-upgrade to latest version
donkit-ragops upgrade       # Check and upgrade (interactive)
donkit-ragops upgrade -y    # Upgrade without confirmation
```

> **Note:** The `upgrade` command automatically detects your installation method (pip, pipx, or poetry) and runs the appropriate upgrade command.

### Environment Variables

#### LLM Provider Configuration
- `RAGOPS_LLM_PROVIDER` — LLM provider name (e.g., `openai`, `vertex`, `azure_openai`, `ollama`, `openrouter`)
- `RAGOPS_LLM_MODEL` — Specify model name (e.g., `gpt-4o-mini` for OpenAI, `gemini-2.5-flash` for Vertex)

#### OpenAI / OpenRouter / Ollama
- `RAGOPS_OPENAI_API_KEY` — OpenAI API key (also used for OpenRouter and Ollama)
- `RAGOPS_OPENAI_BASE_URL` — OpenAI base URL (default: https://api.openai.com/v1)
  - OpenRouter: `https://openrouter.ai/api/v1`
  - Ollama: `http://localhost:11434/v1`
- `RAGOPS_OPENAI_EMBEDDINGS_MODEL` — Embedding model name (default: text-embedding-3-small)

#### Azure OpenAI
- `RAGOPS_AZURE_OPENAI_API_KEY` — Azure OpenAI API key
- `RAGOPS_AZURE_OPENAI_ENDPOINT` — Azure OpenAI endpoint URL
- `RAGOPS_AZURE_OPENAI_API_VERSION` — Azure API version (default: 2024-02-15-preview)
- `RAGOPS_AZURE_OPENAI_DEPLOYMENT` — Azure deployment name for chat model
- `RAGOPS_AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT` — Azure deployment name for embeddings model

#### Vertex AI (Google Cloud)
- `RAGOPS_VERTEX_CREDENTIALS` — Path to Vertex AI service account JSON
- `RAGOPS_VERTEX_PROJECT` — Google Cloud project ID (optional, extracted from credentials if not set)
- `RAGOPS_VERTEX_LOCATION` — Vertex AI location (default: us-central1)

#### Logging
- `RAGOPS_LOG_LEVEL` — Logging level (default: ERROR)

## Agent Workflow

The agent follows a structured workflow:

1. **Language Detection** — Detects user's language from first message
2. **Project Creation** — Creates project directory structure
3. **Checklist Creation** — Generates task checklist in user's language
4. **Step-by-Step Execution**:
   - Asks for permission before each step
   - Marks item as `in_progress`
   - Executes the task using appropriate MCP tool
   - Reports results
   - Marks item as `completed`
5. **Deployment** — Sets up Docker Compose infrastructure
6. **Data Loading** — Loads documents into vector store

[⬆️ Back to top](#-table-of-contents)

## Web UI

RAGOps includes a browser-based interface for easier interaction:

```bash
# Start Web UI server (browser opens automatically)
donkit-ragops-web

# Start Web UI without opening browser
donkit-ragops-web --no-browser

# Development mode with hot reload
donkit-ragops-web --dev
```

The browser will automatically open at http://localhost:8067. The Web UI provides:

- Visual project management
- File upload and attachment
- Real-time agent responses
- Checklist visualization
- Settings configuration

## SaaS Mode

SaaS mode is a fully managed cloud platform. All backend infrastructure — databases, vector stores, RAG services, and experiment runners — is hosted by Donkit. You get the same CLI interface, but with powerful cloud features.

### Setup

```bash
# 1. Run setup wizard and choose SaaS mode
donkit-ragops setup

# The wizard will guide you through:
# - Login with your API token
# - Configure integrations (OpenRouter, etc.)
# - Manage credentials

# 2. Start in SaaS mode
donkit-ragops --enterprise

# 3. Check status
donkit-ragops status
```

### Managing SaaS Configuration

Use `donkit-ragops setup` to:
- **Login/Logout** — Authenticate with Donkit cloud
- **Manage Integrations** — Add/update/remove API keys for:
  - OpenRouter (access 100+ models)
  - More providers coming soon

Your credentials are stored securely in system keyring and `.env` file.

### What's Included

- **Managed infrastructure** — No Docker, no local setup. Everything runs in Donkit cloud
- **Automated experiments** — Run 100+ RAG architecture iterations to find optimal configuration
- **Experiment tracking** — Compare chunking strategies, embeddings, retrievers side-by-side
- **Evaluation pipelines** — Batch evaluation with precision/recall/accuracy metrics
- **File attachments** — Attach files using `@/path/to/file` syntax in chat
- **Persistent history** — Conversation and project history preserved across sessions
- **MCP over HTTP** — All MCP tools executed server-side

## Enterprise Mode

Enterprise mode runs fully inside your infrastructure — no data ever leaves your network. All components — from vector databases to experiment runners — are deployed within your VPC, Kubernetes cluster, or even a single secured server. You get the same CLI and web UI, but with full control over data, compute, and compliance. No vendor lock-in, no hidden dependencies — just RAG automation, on your terms.

### What's Included

- **Self-hosted infrastructure** — Run the full Donkit stack in your VPC, Kubernetes cluster, or air-gapped server
- **Automated experiments** — Execute 100+ RAG variations locally to identify the best-performing pipeline
- **Experiment tracking** — Monitor and compare pipeline variants (chunking, retrieval, reranking) within your environment
- **Evaluation pipelines** — Run secure, on-prem evaluation with precision, recall, and answer relevancy metrics
- **Local file attachments** — Add documents from using `@/path/to/file` in chat or connect your data sources via APIs
- **Session-based state** — Preserve project and conversation history within your private deployment
- **MCP over IPC** — All orchestration runs inside your infrastructure; no external HTTP calls required

[⬆️ Back to top](#-table-of-contents)

## Modes of work comparison

| Feature | Local Mode | SaaS Mode |Enterprise Mode |
|---------|------------|------------|-----------------|
| Infrastructure | Self-hosted (Docker) | Managed by Donkit | Managed by customer |
| Vector stores | Local Qdrant/Milvus/Chroma | Cloud-hosted | Managed by customer |
| Experiments | Manual | Automated iterations | Automated iterations |
| Evaluation | Basic | Full pipeline with metrics | Full pipeline with metrics |
| Data persistence | Local files | Cloud database | Full data residency control |

## MCP Servers

RAGOps Agent includes built-in MCP servers:

### `ragops-rag-planner`

Plans RAG pipeline configuration based on requirements.

**Tools:**
- `plan_rag_config` — Generate RAG configuration from requirements

### `ragops-read-engine`

Processes and converts documents from various formats.

**Tools:**
- `process_documents` — Convert PDF, DOCX, PPTX, XLSX, images to text/JSON/markdown/TOON

### `ragops-chunker`

Chunks documents for vector storage.

**Tools:**
- `chunk_documents` — Split documents into chunks with configurable strategies
- `list_chunked_files` — List processed chunk files

### `ragops-vectorstore-loader`

Loads chunks into vector databases and manages documents.

**Tools:**
- `vectorstore_load` — Load documents into Qdrant, Chroma, or Milvus (supports incremental loading)
- `delete_from_vectorstore` — Remove documents from vector store by filename or document_id

### `ragops-compose-manager`

Manages Docker Compose infrastructure.

**Tools:**
- `init_project_compose` — Initialize Docker Compose for project
- `compose_up` — Start services
- `compose_down` — Stop services
- `compose_status` — Check service status
- `compose_logs` — View service logs

### `ragops-rag-query`

Executes RAG queries against deployed services.

**Tools:**
- `search_documents` — Search for relevant documents in vector database
- `get_rag_prompt` — Get formatted RAG prompt with retrieved context

### `rag-evaluation`

Evaluates RAG pipeline performance with batch processing.

**Tools:**
- `evaluate_batch` — Run batch evaluation from CSV/JSON, compute Precision/Recall/Accuracy

### `donkit-ragops-mcp`

**Unified MCP server** that combines all servers above into a single endpoint.

```bash
# Run unified server
donkit-ragops-mcp
```

**Claude Desktop configuration:**

```json
{
  "mcpServers": {
    "donkit-ragops-mcp": {
      "command": "donkit-ragops-mcp"
    }
  }
}
```

All tools are available with prefixes:
- `chunker_*` — Document chunking
- `compose_*` — Docker Compose orchestration
- `evaluation_*` — RAG evaluation
- `planner_*` — RAG configuration planning
- `query_*` — RAG query execution
- `reader_*` — Document reading/parsing
- `vectorstore_*` — Vector store operations

> **Note:** Checklist management is handled by built-in agent tools, not MCP.

[⬆️ Back to top](#-table-of-contents)

## Examples

### Basic RAG Pipeline

```bash
donkit-ragops
```

```
> Create a RAG pipeline for customer support docs in ../docs folder
```

The agent will:
1. Create project structure
2. Plan RAG configuration
3. Chunk documents from `../docs`
4. Set up Qdrant + RAG service
5. Load data into vector store

### Custom Configuration

```bash
donkit-ragops -p vertexai -m gemini-2.5-pro
```

```
> Build RAG for legal documents with 1000 token chunks and reranking
```

### Multiple Projects

Each project gets its own:
- Project directory (`projects/<project_id>`)
- Docker Compose setup
- Vector store collection
- Configuration

[⬆️ Back to top](#-table-of-contents)

## Development

### Prerequisites

- Python 3.12+
- [Poetry](https://python-poetry.org/) for dependency management
- Docker Desktop (for testing vector stores and RAG services)

### Setup

```bash
# Clone the repository
git clone https://github.com/donkit-ai/ragops.git
cd ragops/ragops-agent-cli

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Project Structure

```
ragops-agent/
├── src/donkit_ragops/
│   ├── agent/              # LLM agent core and local tools
│   │   ├── agent.py        # Main LLMAgent class
│   │   ├── prompts.py      # System prompts for different providers
│   │   └── local_tools/    # Built-in agent tools
│   ├── llm/                # LLM provider integrations
│   │   └── providers/      # OpenAI, Vertex, Anthropic, etc.
│   ├── mcp/                # Model Context Protocol
│   │   ├── client.py       # MCP client implementation
│   │   └── servers/        # Built-in MCP servers
│   ├── repl/               # REPL implementation
│   │   ├── base.py         # Base REPL context
│   │   ├── local_repl.py   # Local mode REPL
│   │   └── enterprise_repl.py  # SaaS/Enterprise mode REPL
│   ├── web/                # Web UI (FastAPI + WebSocket)
│   │   ├── app.py          # FastAPI application
│   │   └── routes/         # API endpoints
│   ├── enterprise/         # SaaS/Enterprise mode components
│   ├── cli.py              # CLI entry point (Typer)
│   └── config.py           # Configuration management
├── tests/                  # Test suite (170+ tests)
└── pyproject.toml          # Poetry project configuration
```

### Running the CLI Locally

```bash
# Run CLI
poetry run donkit-ragops

# Run with specific provider
poetry run donkit-ragops -p openai -m gpt-4o

# Run Web UI
poetry run donkit-ragops-web

# Run unified MCP server
poetry run donkit-ragops-mcp
```

### Building the static frontend

The Web UI is served from **`src/donkit_ragops/web/static/`**, not from `frontend/dist/`. To see your frontend changes when running in production mode (without `--dev`):

1. **From the project root**, run the full build script (it builds Vite and copies output to `static/`):

   ```bash
   ./scripts/build-frontend.sh   # macOS/Linux
   # or
   scripts/build-frontend.ps1    # Windows PowerShell
   ```

2. Restart `donkit-ragops-web` if it is already running.

If you only run `npm run build` inside `frontend/`, the result goes to `frontend/dist/` and the app will still serve the old files from `static/`. Use the script above so that the built files are copied into `static/`.

For live reload during development, use:

```bash
poetry run donkit-ragops-web --dev
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=donkit_ragops

# Run specific test file
poetry run pytest tests/test_agent.py

# Run specific test
poetry run pytest tests/test_agent.py::test_function_name -v
```

### Code Quality

```bash
# Format code (REQUIRED before commit)
poetry run ruff format .

# Lint and auto-fix (REQUIRED before commit)
poetry run ruff check . --fix

# Check without fixing
poetry run ruff check .
```

### Version Management

**IMPORTANT:** Version must be incremented in `pyproject.toml` for every PR:

```bash
# Check current version
grep "^version" pyproject.toml

# Increment version in pyproject.toml before committing
# patch: 0.4.5 → 0.4.6 (bug fixes)
# minor: 0.4.5 → 0.5.0 (new features)
# major: 0.4.5 → 1.0.0 (breaking changes)
```

### Adding a New MCP Server

**Step 1.** Create server file in `src/donkit_ragops/mcp/servers/`:

```python
from fastmcp import FastMCP
from pydantic import BaseModel, Field

server = FastMCP("my-server")

class MyToolArgs(BaseModel):
    param: str = Field(description="Parameter description")

@server.tool(name="my_tool", description="What the tool does")
async def my_tool(args: MyToolArgs) -> str:
    # Implementation
    return "result"

def main() -> None:
    server.run(transport="stdio")
```

**Step 2.** Add entry point in `pyproject.toml`:

```toml
[tool.poetry.scripts]
ragops-my-server = "donkit_ragops.mcp.servers.my_server:main"
```

**Step 3.** Mount in unified server (`donkit_ragops_mcp.py`):

```python
from .my_server import server as my_server
unified_server.mount(my_server, prefix="my")
```

### Adding a New LLM Provider

1. Create provider in `src/donkit_ragops/llm/providers/`
2. Register in `provider_factory.py`
3. Add configuration to `config.py`
4. Update `supported_models.py`

### Debugging

```bash
# Enable debug logging
RAGOPS_LOG_LEVEL=DEBUG poetry run donkit-ragops

# Debug MCP servers
RAGOPS_LOG_LEVEL=DEBUG poetry run donkit-ragops-mcp
```

[⬆️ Back to top](#-table-of-contents)

## Docker Compose Services

The agent can deploy these services using profiles:

### Qdrant (Vector Database)

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    profiles: [qdrant, full-stack]
    ports:
      - "6333:6333"  # HTTP API
      - "6334:6334"  # gRPC API
    volumes:
      - qdrant_data:/qdrant/storage
```

### Chroma (Vector Database)

```yaml
services:
  chroma:
    image: chromadb/chroma:latest
    container_name: chroma
    profiles: [chroma]
    ports:
      - "8015:8000"
    volumes:
      - chroma_data:/chroma/data
```

### Milvus (Vector Database)

Requires etcd and MinIO:

```yaml
services:
  etcd:
    image: quay.io/coreos/etcd:v3.5.5
    container_name: milvus-etcd
    profiles: [milvus]

  minio:
    image: minio/minio:latest
    container_name: milvus-minio
    profiles: [milvus]

  milvus:
    image: milvusdb/milvus:v2.3.21
    container_name: milvus-standalone
    profiles: [milvus]
    ports:
      - "19530:19530"  # Milvus API
      - "9091:9091"    # Metrics
    depends_on:
      - etcd
      - minio
```

### RAG Service

```yaml
services:
  rag-service:
    image: donkitai/rag-service:latest
    container_name: rag-service
    profiles: [rag-service, full-stack]
    ports:
      - "8000:8000"
    env_file:
      - .env
```

**Profiles:**
- `qdrant` - Qdrant vector database only
- `chroma` - Chroma vector database only
- `milvus` - Milvus vector database with dependencies
- `rag-service` - RAG service only
- `full-stack` - Qdrant + RAG service

[⬆️ Back to top](#-table-of-contents)

## Architecture

```
┌─────────────────┐
│  RAGOps Agent   │
│     (CLI)       │
└────────┬────────┘
         │
         ├── MCP Servers ───────────────┐
         │   ├── ragops-rag-planner     │
         │   ├── ragops-chunker         │
         │   ├── ragops-vectorstore     │
         │   └── ragops-compose         │
         │                              │
         └── LLM Providers ─────────────┤
             ├── Vertex AI              │
             ├── OpenAI                 │
             ├── Anthropic              │
             └── Ollama                 │
                                        │
                                        ▼
                            ┌─────────────────────────┐
                            │   Docker Compose        │
                            ├─────────────────────────┤
                            │ Vector Databases:       │
                            │  • Qdrant (6333, 6334)  │
                            │  • Chroma (8015)        │
                            │  • Milvus (19530, 9091) │
                            │    + etcd               │
                            │    + MinIO              │
                            │                         │
                            │ RAG Service:            │
                            │  • rag-service (8000)   │
                            └─────────────────────────┘
```

[⬆️ Back to top](#-table-of-contents)

## Troubleshooting

### Windows + Docker Desktop with WSL2

The agent **fully supports Windows with Docker Desktop running in WSL2 mode**. Path conversion and Docker communication are handled automatically.

**Requirements:**
- Docker Desktop for Windows with WSL2 backend enabled
- Python 3.12+ installed on Windows (not inside WSL2)
- Run the agent from Windows PowerShell or Command Prompt

**How it works:**
- The agent detects WSL2 Docker automatically
- Windows paths like `C:\Users\...` are converted to `/mnt/c/Users/...` for Docker
- No manual configuration needed

**Troubleshooting:**

```bash
# 1. Verify Docker is accessible from Windows
docker info

# 2. Check Docker reports Linux (indicates WSL2)
docker info --format "{{.OperatingSystem}}"
# Should output: Docker Desktop (or similar with "linux")

# 3. If Docker commands fail, ensure Docker Desktop is running
```

### MCP Server Connection Issues

If MCP servers fail to start:

```bash
# Check MCP server logs
RAGOPS_LOG_LEVEL=DEBUG donkit-ragops
```

### Vector Store Connection

Ensure Docker services are running:

```bash
cd projects/<project_id>
docker-compose ps
docker-compose logs qdrant
```

### Credentials Issues

Verify your credentials:

```bash
# Vertex AI
gcloud auth application-default print-access-token

# OpenAI
echo $RAGOPS_OPENAI_API_KEY
```

[⬆️ Back to top](#-table-of-contents)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## Related Projects

- [donkit-chunker](https://pypi.org/project/donkit-chunker/) — Document chunking library
- [donkit-vectorstore-loader](https://pypi.org/project/donkit-vectorstore-loader/) — Vector store loading utilities
- [donkit-read-engine](https://pypi.org/project/donkit-read-engine/) — Document parsing engine

---

Built with ❤️ by [Donkit AI](https://donkit.ai/?utm_source=github)
