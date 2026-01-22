# RAGOps Agent CE (Community Edition)

[![PyPI version](https://badge.fury.io/py/donkit-ragops.svg)](https://badge.fury.io/py/donkit-ragops)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Optimal RAG in hours, not months.**

An LLM-powered CLI agent that automates the creation, experimentation, and deployment of Retrieval-Augmented Generation (RAG) pipelines. Instead of spending months manually tuning indexes, chunking strategies, embeddings, and evaluators — let the agent explore the design space, run experiments, and converge on what works for your data.

Built by [Donkit AI](https://donkit.ai) — Automated Context Engineering.

## Who is this for?

- **AI Engineers** building internal assistants and agents
- **Teams** needing accuracy-sensitive RAG where errors compound across steps
- **Organizations** running agent-dependent systems requiring trustworthy retrieval

> Think of RAG like a library—with indexes, storage, and a librarian. Donkit is the library factory.

## Key Features

* **Interactive REPL** — Start an interactive session with readline history and autocompletion
* **Web UI** — Browser-based interface at http://localhost:8067 (`donkit-ragops-web`)
* **Checklist-driven workflow** — The agent creates project checklists, asks for approval before each step, and tracks progress
* **Session-scoped checklists** — Only current session checklists appear in the UI
* **Integrated MCP servers** — Built-in support for full RAG build pipeline (planning, reading, chunking, vector loading, querying, evaluation)
* **Docker Compose orchestration** — Automated deployment of RAG infrastructure (vector DB, RAG service)
* **Enterprise mode** — Connect to Donkit cloud for experiments
* **Multiple LLM providers** — Supports Vertex AI (Recommended), OpenAI, Anthropic Claude, Azure OpenAI, Ollama, OpenRouter

## Quick Install

The fastest way to install Donkit RAGOps. The installer automatically handles Python and dependencies.

**macOS / Linux:**
```bash
curl -sSL https://raw.githubusercontent.com/donkit-ai/ragops/main/scripts/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/donkit-ai/ragops/main/ragops-agent-cli/scripts/install.ps1 | iex
```

After installation:
```bash
donkit-ragops        # Start CLI agent
donkit-ragops-web    # Start Web UI at http://localhost:8067
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

### Alternative: Manual configuration

If you prefer to configure manually or reconfigure later:

```bash
# Run setup wizard again
donkit-ragops --setup
```

Or create a `.env` file manually in your working directory:

```bash
# Vertex AI (Google Cloud)
RAGOPS_LLM_PROVIDER=vertex
RAGOPS_VERTEX_CREDENTIALS=/path/to/service-account-key.json

# OpenAI
RAGOPS_LLM_PROVIDER=openai
RAGOPS_OPENAI_API_KEY=sk-...
RAGOPS_LLM_MODEL=gpt-4o-mini # Specify the OpenAI model to use
# RAGOPS_OPENAI_BASE_URL=https://api.openai.com/v1

# Anthropic Claude
RAGOPS_LLM_PROVIDER=anthropic
RAGOPS_ANTHROPIC_API_KEY=sk-ant-...

# Ollama (local)
RAGOPS_LLM_PROVIDER=ollama
RAGOPS_OLLAMA_BASE_URL=http://localhost:11434
```

### Step 3: Start using the agent

Tell the agent what you want to build:

```
you> Create a RAG pipeline for my documents in /Users/myname/Documents/work_docs
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

## Usage

> **Note:** The command `ragops-agent` is also available as an alias for backward compatibility.
> 
> The agent starts in interactive REPL mode by default. Use subcommands like `ping` for specific actions.

### Interactive Mode (REPL)

```bash
# Start interactive session
donkit-ragops

# With specific provider
donkit-ragops -p vertexai

# With custom model
donkit-ragops -p openai -m gpt-4

# Start in enterprise mode (requires login first)
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
- `--enterprise` — Force enterprise mode (requires login)
- `--setup` — Run setup wizard to reconfigure
- `--show-checklist/--no-checklist` — Toggle checklist panel (default: shown)

### Subcommands

```bash
# Health check
donkit-ragops ping

# Enterprise mode authentication
donkit-ragops login --token YOUR_TOKEN  # Login to Donkit cloud
donkit-ragops logout                    # Remove stored token
donkit-ragops status                    # Show mode and auth status
```

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

#### Anthropic
- `RAGOPS_ANTHROPIC_API_KEY` — Anthropic API key

#### Logging
- `RAGOPS_LOG_LEVEL` — Logging level (default: INFO)
- `RAGOPS_MCP_COMMANDS` — Comma-separated list of MCP commands

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

## Web UI

RAGOps includes a browser-based interface for easier interaction:

```bash
# Start Web UI server
donkit-ragops-web
```

Open http://localhost:8067 in your browser. The Web UI provides:

- Visual project management
- File upload and attachment
- Real-time agent responses
- Checklist visualization
- Settings configuration

## Enterprise Mode

Enterprise mode connects to Donkit cloud for team collaboration and advanced features.

### Setup

```bash
# 1. Login with your API token
donkit-ragops login --token YOUR_API_TOKEN

# 2. Start in enterprise mode
donkit-ragops --enterprise

# 3. Check status
donkit-ragops status

# 4. Logout when done
donkit-ragops logout
```

### Features

- **Cloud sync** — Projects and checklists synced to Donkit cloud
- **Team collaboration** — Share projects with team members
- **File attachments** — Attach files using `@/path/to/file` syntax in chat
- **Persistent history** — Conversation history preserved across sessions

### Environment Variables (Enterprise)

- `DONKIT_API_URL` — API gateway URL (default: https://api.donkit.ai)
- `DONKIT_ENTERPRISE_PERSIST_MESSAGES` — Enable/disable message persistence (default: true)

## MCP Servers

RAGOps Agent CE includes built-in MCP servers:

### `ragops-rag-planner`

Plans RAG pipeline configuration based on requirements.

**Tools:**
- `plan_rag_config` — Generate RAG configuration from requirements

### `ragops-read-engine`

Processes and converts documents from various formats.

**Tools:**
- `process_documents` — Convert PDF, DOCX, PPTX, XLSX, images to text/json/markdown

### `ragops-chunker`

Chunks documents for vector storage.

**Tools:**
- `chunk_documents` — Split documents into chunks with configurable strategies
- `list_chunked_files` — List processed chunk files

### `ragops-vectorstore-loader`

Loads chunks into vector databases.

**Tools:**
- `vectorstore_load` — Load documents into Qdrant, Chroma, or Milvus
- `delete_from_vectorstore` — Remove documents from vector store

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

> **Note:** Checklist management is now handled by built-in agent tools, not MCP.

## Examples

### Basic RAG Pipeline

```bash
donkit-ragops
```

```
you> Create a RAG pipeline for customer support docs in ./docs folder
```

The agent will:
1. Create project structure
2. Plan RAG configuration
3. Chunk documents from `./docs`
4. Set up Qdrant + RAG service
5. Load data into vector store

### Custom Configuration

```bash
donkit-ragops -p vertexai -m gemini-1.5-pro
```

```
you> Build RAG for legal documents with 1000 token chunks and reranking
```

### Multiple Projects

Each project gets its own:
- Project directory (`projects/<project_id>`)
- Docker Compose setup
- Vector store collection
- Configuration

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
ragops-agent-cli/
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
│   │   └── enterprise_repl.py  # Enterprise mode REPL
│   ├── web/                # Web UI (FastAPI + WebSocket)
│   │   ├── app.py          # FastAPI application
│   │   └── routes/         # API endpoints
│   ├── enterprise/         # Enterprise mode components
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

## Docker Compose Services

The agent can deploy these services:

### Qdrant (Vector Database)

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
```

### RAG Service

```yaml
services:
  rag-service:
    image: donkit/rag-service:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URI=http://qdrant:6333
      - CONFIG=<base64-encoded-config>
```

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
                            ┌──────────────────┐
                            │ Docker Compose   │
                            ├──────────────────┤
                            │ • Qdrant         │
                            │ • RAG Service    │
                            └──────────────────┘
```

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

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## Related Projects

- [donkit-chunker](https://pypi.org/project/donkit-chunker/) — Document chunking library
- [donkit-vectorstore-loader](https://pypi.org/project/donkit-vectorstore-loader/) — Vector store loading utilities
- [donkit-read-engine](https://pypi.org/project/donkit-read-engine/) — Document parsing engine

---

Built with ❤️ by [Donkit AI](https://donkit.ai)
