# Project Structure - Plan-and-Spawn Agent System

This document describes the complete file structure of the project.

## Directory Tree

```
plan-and-spawn-agent/
│
├── README.md                          # Main documentation
├── PROJECT_STRUCTURE.md               # This file
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment variables template
├── .env                              # Your actual config (don't commit!)
├── setup.sh                          # Setup script
├── test_system.py                    # Component tests
│
├── src/
│   └── plan_spawn/                   # Main package
│       ├── __init__.py               # Package initialization
│       ├── main.py                   # CLI entry point
│       │
│       ├── config/                   # Configuration
│       │   ├── __init__.py
│       │   └── settings.py           # Settings management
│       │
│       └── core/                     # Core components
│           ├── __init__.py
│           ├── models.py             # Pydantic models
│           ├── orchestrator.py       # Main orchestrator
│           ├── planner.py            # Plan generation
│           ├── executor.py           # Plan execution
│           ├── agent_runtime.py      # Agent execution
│           │
│           ├── storage/              # Storage layer
│           │   ├── __init__.py
│           │   └── artifacts.py      # Artifact management
│           │
│           └── tools/                # Tool implementations
│               ├── __init__.py
│               ├── registry.py       # Tool registry
│               ├── web_tools.py      # Web search/fetch
│               ├── file_tools.py     # File operations
│               └── llm_tools.py      # LLM utilities
│
└── artifacts/                        # Generated artifacts (gitignore)
    ├── _metadata/                    # Artifact metadata
    ├── s1/                          # Step 1 artifacts
    ├── s2/                          # Step 2 artifacts
    └── ...
```

## File Descriptions

### Root Level

- **README.md**: User-facing documentation with installation and usage instructions
- **requirements.txt**: Python package dependencies
- **.env.example**: Template for environment variables
- **.env**: Your actual configuration (API keys, etc.)
- **setup.sh**: Automated setup script
- **test_system.py**: Component test suite

### src/plan_spawn/

Main application package.

#### main.py
CLI entry point with different modes:
- `article`: Article generation mode
- `interactive`: Interactive prompt mode
- `run`: Direct objective execution
- `help`: Show help

#### config/

**settings.py**: Configuration management
- Loads environment variables
- Provides Settings singleton
- Validates critical settings

#### core/

**models.py**: Pydantic data models
- TaskRequest, Plan, Step, StepResult
- AgentSpec, Acceptance, IOSpec
- All JSON-serializable models

**orchestrator.py**: Main orchestrator
- Coordinates planner → executor
- Initializes components
- Manages execution flow

**planner.py**: Plan generation
- Uses Claude to generate plans
- Validates plan structure
- Detects circular dependencies

**executor.py**: Plan execution
- Executes steps in dependency order
- Manages execution state
- Handles failures gracefully

**agent_runtime.py**: Agent execution
- Spawns ephemeral agents
- Manages tool call loops
- Validates acceptance criteria

#### core/storage/

**artifacts.py**: Artifact management
- URI-based storage (artifact://step_id/filename)
- Save/load with metadata
- Support for text, JSON, binary

#### core/tools/

**registry.py**: Tool registry
- Tool registration and lookup
- Schema generation for Claude
- Usage tracking

**web_tools.py**: Web operations
- `web_search`: Search the web
- `web_fetch`: Fetch webpage content

**file_tools.py**: File operations
- `write_artifact`: Save artifacts
- `read_artifact`: Load artifacts
- `list_artifacts`: List artifacts

**llm_tools.py**: LLM utilities
- `llm_call`: Direct Claude calls
- `quality_check`: Content quality assessment
- `fact_verify`: Fact verification

### artifacts/

Runtime directory for generated artifacts:
- Organized by step ID
- Contains all agent outputs
- Metadata stored separately

## Data Flow

```
User Input (CLI)
    ↓
main.py
    ↓
Orchestrator
    ↓
Planner (generates Plan)
    ↓
Executor (manages execution)
    ↓
AgentRuntime (per step)
    ↓
Tools (via Registry)
    ↓
ArtifactStore (saves outputs)
    ↓
Results returned to user
```

## Key Concepts

### Plans
JSON structures defining:
- Objective
- Steps with dependencies
- Agent specifications
- Acceptance criteria

### Agents
Ephemeral agents created per step:
- Have role (ResearchAgent, WriterAgent, etc.)
- Use specific tools
- Execute autonomously
- Self-validate results

### Artifacts
All outputs stored as artifacts:
- Logical URIs: `artifact://s1/research.json`
- Physical files: `./artifacts/s1/research.json`
- Metadata tracked separately

### Tools
Functions agents can invoke:
- Registered in ToolRegistry
- Auto-injected dependencies
- Usage tracked for metrics

## Extension Points

### Adding New Tools

1. Create function in `core/tools/`
2. Use `@register_tool` decorator
3. Tool auto-available to agents

### Adding New Agent Archetypes

1. Define in `planner.py` system prompt
2. Specify role, tools, prompts
3. Planner will use in generated plans

### Custom Acceptance Criteria

1. Add new type in `Acceptance` model
2. Implement validation in `agent_runtime.py`

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-...

# Optional
BRAVE_API_KEY=...
CLAUDE_MODEL=claude-sonnet-4-5-20250929
ARTIFACTS_PATH=./artifacts
MAX_ITERATIONS_PER_STEP=15
DEFAULT_TIMEOUT_S=180
```

## Running the System

```bash
# Setup
./setup.sh
source venv/bin/activate

# Configure API key
nano .env  # Add ANTHROPIC_API_KEY

# Test
python test_system.py

# Run
python -m plan_spawn.main article "Your topic"
```

## Development Workflow

1. **Setup**: Run `setup.sh`
2. **Test**: Run `test_system.py`
3. **Develop**: Modify files in `src/plan_spawn/`
4. **Test**: Run specific tests
5. **Use**: Run via CLI

## Troubleshooting

### Import Errors
- Ensure `src/` is in Python path
- Check all `__init__.py` files exist

### API Errors
- Verify ANTHROPIC_API_KEY in `.env`
- Check API key has credits

### Tool Failures
- Check tool implementation
- Verify dependencies (aiohttp, etc.)

### Plan Generation Fails
- Check prompt in `planner.py`
- Verify Claude returns valid JSON
- Check for API rate limits

## Security Notes

- Never commit `.env` file
- Keep API keys secret
- Validate user inputs
- Sandbox tool executions (future)
