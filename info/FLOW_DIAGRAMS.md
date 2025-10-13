# Diagramas de Flujo Detallados - PlanAgent

## 📊 Índice
1. [Flujo Completo](#flujo-completo)
2. [Lifecycle de un Agente](#lifecycle-de-un-agente)
3. [Sistema de Tools](#sistema-de-tools)
4. [Gestión de Artifacts](#gestión-de-artifacts)
5. [Manejo de Errores](#manejo-de-errores)

---

## Flujo Completo

### Vista de Alto Nivel

```
┌──────────────────────────────────────────────────────────────────────┐
│                         PLAN-AND-SPAWN SYSTEM                        │
└──────────────────────────────────────────────────────────────────────┘

    USER INPUT: "Escribir artículo sobre peligros de IA en 2025"
         │
         │
         ▼
    ┌────────────────┐
    │   CLI Entry    │  python -m plan_spawn.main article "..."
    │   main.py      │
    └────────┬───────┘
             │
             ▼
    ┌────────────────┐
    │  Orchestrator  │  Initialize components:
    │    .run()      │  - ArtifactStore
    └────────┬───────┘  - ToolRegistry
             │          - Planner
             │          - AgentRuntime
             │          - Executor
             ├────────────────────────────────┐
             │                                │
             │ PHASE 1: PLANNING              │ PHASE 2: EXECUTION
             ▼                                ▼
    ┌────────────────┐              ┌────────────────┐
    │    Planner     │              │    Executor    │
    │                │              │                │
    │ Claude API     │              │ For each step: │
    │ "Meta-Agent"   │              │ - Build context│
    │                │              │ - Spawn agent  │
    │ Generates:     │──────Plan───▶│ - Execute      │
    │ - Steps        │              │ - Validate     │
    │ - Dependencies │              │ - Track state  │
    │ - AgentSpecs   │              │                │
    └────────────────┘              └────────┬───────┘
                                             │
                                             │ For each step
                                             ▼
                                    ┌────────────────┐
                                    │ AgentRuntime   │
                                    │ .execute_step()│
                                    └────────┬───────┘
                                             │
                                             │ Iterative tool use
                                             ▼
                                    ┌────────────────┐
                                    │  Claude API    │
                                    │  + Tools       │
                                    │  Loop until    │
                                    │  end_turn      │
                                    └────────┬───────┘
                                             │
                                             ▼
                                    ┌────────────────┐
                                    │  StepResult    │
                                    │  + Artifacts   │
                                    └────────────────┘
```

---

## Lifecycle de un Agente

### Creación y Ejecución

```
STEP CREATION (by Planner)
═══════════════════════════

┌────────────────────────────────────────────┐
│ Step {                                     │
│   id: "s1"                                 │
│   title: "Investigación sobre IA"          │
│   depends_on: []                           │
│   agent_spec: {                            │
│     role: "ResearchAgent"                  │
│     system_prompt: "Eres un agente..."     │
│     tools: ["web_search", "write_artifact"]│
│     stop_conditions: { max_calls: 20 }     │
│   }                                        │
│   acceptance: { type: "schema", ... }      │
│   status: "pending"                        │
│ }                                          │
└────────────────────────────────────────────┘
                   │
                   │ Executor picks step
                   ▼
            ┌─────────────┐
            │   RUNNING   │
            └──────┬──────┘
                   │
                   │ AgentRuntime.execute_step()
                   ▼

AGENT EXECUTION LOOP
════════════════════

Iteration 1:
┌──────────────────────────────────────────────────────────────┐
│  Claude API Request                                          │
│  ─────────────────────────────────────────────────────────   │
│  Model: claude-sonnet-4                                      │
│  System: "Eres un agente de investigación.                   │
│           Sigue estos pasos EXACTAMENTE:                     │
│           1. Usa web_search 3-5 veces                        │
│           2. Usa web_fetch 2-3 veces                         │
│           3. OBLIGATORIO: write_artifact                     │
│           4. Responde con JSON step_result"                  │
│                                                              │
│  Messages: [                                                 │
│    { role: "user",                                           │
│      content: '{"type":"execute_step","context":{...}}' }    │
│  ]                                                           │
│                                                              │
│  Tools: [web_search, web_fetch, write_artifact]             │
└──────────────────────────────────────────────────────────────┘
                   │
                   │ Claude decides: "I need to search"
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  Response                                                    │
│  ────────                                                    │
│  stop_reason: "tool_use"                                     │
│  content: [                                                  │
│    { type: "text",                                           │
│      text: "Let me search for information about AI risks" } │
│    { type: "tool_use",                                       │
│      id: "toolu_123",                                        │
│      name: "web_search",                                     │
│      input: { query: "AI risks 2025", count: 10 } }         │
│  ]                                                           │
└──────────────────────────────────────────────────────────────┘
                   │
                   │ AgentRuntime executes tool
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  Tool Execution: web_search                                  │
│  ──────────────────────────────────────────────────────      │
│  Input: { query: "AI risks 2025", count: 10 }               │
│  Injected: { step_id: "s1", artifact_store: <obj> }         │
│                                                              │
│  Result: {                                                   │
│    status: "success",                                        │
│    results: [                                                │
│      { title: "AI Risks Report", url: "...", snippet: "..." }│
│      { title: "Stanford AI Index", url: "...", ... }        │
│      ...                                                     │
│    ]                                                         │
│  }                                                           │
└──────────────────────────────────────────────────────────────┘
                   │
                   │ Add tool result to conversation
                   ▼

Iteration 2:
┌──────────────────────────────────────────────────────────────┐
│  Claude API Request                                          │
│  ─────────────────────────────────────────────────────────   │
│  Messages: [                                                 │
│    { role: "user", content: "..." }                          │
│    { role: "assistant", content: [tool_use_block] }          │
│    { role: "user", content: [tool_result_block] }            │
│  ]                                                           │
└──────────────────────────────────────────────────────────────┘
                   │
                   │ Claude decides: "Search more"
                   ▼
                [tool_use: web_search]
                   │
                   ▼
                [execute tool]
                   │
                   ▼

... (iterations 3-6: more searches and fetches)

Iteration 7:
                   │
                   │ Claude decides: "Save results"
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  Response                                                    │
│  ────────                                                    │
│  stop_reason: "tool_use"                                     │
│  content: [                                                  │
│    { type: "tool_use",                                       │
│      name: "write_artifact",                                 │
│      input: {                                                │
│        name: "research.json",                                │
│        content: '{"sources":[...],"key_points":[...],...}',  │
│        content_type: "json"                                  │
│      }                                                       │
│    }                                                         │
│  ]                                                           │
└──────────────────────────────────────────────────────────────┘
                   │
                   │ Execute write_artifact
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  Tool Result                                                 │
│  ───────────                                                 │
│  {                                                           │
│    status: "success",                                        │
│    uri: "artifact://s1/research.json",                       │
│    size: 15234                                               │
│  }                                                           │
└──────────────────────────────────────────────────────────────┘
                   │
                   │ Add to conversation
                   ▼

Iteration 8:
┌──────────────────────────────────────────────────────────────┐
│  Claude API Request                                          │
│  ─────────────────────────────────────────────────────────   │
│  Messages: [... all previous + tool_result]                  │
└──────────────────────────────────────────────────────────────┘
                   │
                   │ Claude decides: "I'm done, return result"
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  Response                                                    │
│  ────────                                                    │
│  stop_reason: "end_turn"  ← KEY: No more tools!              │
│  content: [                                                  │
│    { type: "text",                                           │
│      text: '{                                                │
│        "type": "step_result",                                │
│        "step_id": "s1",                                      │
│        "status": "ok",                                       │
│        "artifacts": ["artifact://s1/research.json"],         │
│        "summary": "Research completed with 5 sources",       │
│        "log": [],                                            │
│        "acceptance_check": {                                 │
│          "passed": true,                                     │
│          "evidence": "JSON created with required fields"     │
│        }                                                     │
│      }'                                                      │
│    }                                                         │
│  ]                                                           │
└──────────────────────────────────────────────────────────────┘
                   │
                   │ Parse JSON response
                   ▼
            ┌─────────────┐
            │  StepResult │
            │  status: ok │
            └──────┬──────┘
                   │
                   │ Validate acceptance
                   ▼
            ┌─────────────┐
            │    DONE     │
            └─────────────┘
```

---

## Sistema de Tools

### Registro e Invocación

```
TOOL REGISTRATION (at startup)
═══════════════════════════════

┌─────────────────────────────────────────────────────────────┐
│  @register_tool decorator                                   │
│                                                             │
│  @register_tool(                                            │
│      name="web_search",                                     │
│      description="Search the web using Brave API",          │
│      parameters={                                           │
│          "type": "object",                                  │
│          "properties": {                                    │
│              "query": {"type": "string"},                   │
│              "count": {"type": "number", "default": 10}     │
│          },                                                 │
│          "required": ["query"]                              │
│      }                                                      │
│  )                                                          │
│  async def web_search(query, count=10, **kwargs):           │
│      # Implementation                                       │
│      ...                                                    │
└─────────────────────────────────────────────────────────────┘
                   │
                   │ Registers in global registry
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  ToolRegistry                                               │
│  ────────────                                               │
│  tools = {                                                  │
│    "web_search": Tool(                                      │
│      name="web_search",                                     │
│      function=web_search,                                   │
│      schema={ anthropic tool schema }                       │
│    ),                                                       │
│    "web_fetch": Tool(...),                                  │
│    "write_artifact": Tool(...),                             │
│    ...                                                      │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘


TOOL INVOCATION (during agent execution)
═════════════════════════════════════════

Agent wants to use tool:
┌─────────────────────────────────────────────────────────────┐
│  Claude Response                                            │
│  ───────────────                                            │
│  {                                                          │
│    type: "tool_use",                                        │
│    id: "toolu_abc123",                                      │
│    name: "write_artifact",                                  │
│    input: {                                                 │
│      name: "research.json",                                 │
│      content: '{"sources":[...],...}',                      │
│      content_type: "json"                                   │
│    }                                                        │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
                   │
                   │ AgentRuntime._execute_tool()
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Get tool from registry                                  │
│     tool = registry.get("write_artifact")                   │
└─────────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Inject runtime dependencies                             │
│     tool_input = {                    ← From Claude         │
│       "name": "research.json",                              │
│       "content": "...",                                     │
│       "content_type": "json"                                │
│     }                                                       │
│                                                             │
│     injected_params = {               ← Added by runtime   │
│       "step_id": "s1",                                      │
│       "artifact_store": <ArtifactStore>,                    │
│       "current_step_id": "s1"                               │
│     }                                                       │
│                                                             │
│     merged = {**tool_input, **injected_params}              │
└─────────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Execute tool function                                   │
│     result = await tool.function(**merged)                  │
│                                                             │
│     ↓ Inside write_artifact():                              │
│     artifact_store.save(                                    │
│       step_id="s1",                                         │
│       name="research.json",                                 │
│       content=content                                       │
│     )                                                       │
│     → Returns "artifact://s1/research.json"                 │
└─────────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Return result to Claude                                 │
│     {                                                       │
│       "type": "tool_result",                                │
│       "tool_use_id": "toolu_abc123",                        │
│       "content": '{                                         │
│         "status": "success",                                │
│         "uri": "artifact://s1/research.json",               │
│         "size": 15234                                       │
│       }'                                                    │
│     }                                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Gestión de Artifacts

### Flujo de Escritura y Lectura

```
WRITE ARTIFACT
══════════════

Step s1 (ResearchAgent)
         │
         │ write_artifact("research.json", {...})
         ▼
┌─────────────────────────────────────────────────────────────┐
│  ArtifactStore.save()                                       │
│  ────────────────────                                       │
│  1. Create directory: artifacts/s1/                         │
│  2. Write file: artifacts/s1/research.json                  │
│  3. Write metadata: artifacts/s1/_metadata.json             │
│  4. Return URI: "artifact://s1/research.json"               │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
    Filesystem:
    artifacts/
    └── s1/
        ├── research.json          ← Actual content
        └── _metadata.json         ← {created_at, size, checksum}


READ ARTIFACT
═════════════

Step s2 (OutlineAgent) needs research data
         │
         │ read_artifact("artifact://s1/research.json")
         ▼
┌─────────────────────────────────────────────────────────────┐
│  ArtifactStore.load()                                       │
│  ───────────────────                                        │
│  1. Parse URI: "artifact://s1/research.json"                │
│     → step_id = "s1"                                        │
│     → filename = "research.json"                            │
│  2. Construct path: artifacts/s1/research.json              │
│  3. Read file content                                       │
│  4. Load metadata                                           │
│  5. Return: {                                               │
│       status: "success",                                    │
│       content: <file content>,                              │
│       metadata: {...}                                       │
│     }                                                       │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
    OutlineAgent receives the research data
    and can use it to create the outline


ARTIFACT CHAIN (Multiple Steps)
════════════════════════════════

s1 → research.json
     │
     │ (used by)
     ▼
s2 → outline.md
     │
     ├─────────────┐
     │ (used by)   │ (used by)
     ▼             ▼
s3 → intro.md    s4 → body.md
     │             │
     └──────┬──────┘
            │ (used by)
            ▼
         s5 → article.md (final)
```

---

## Manejo de Errores

### Tipos de Errores y Recovery

```
ERROR SCENARIOS
═══════════════

1. TOOL EXECUTION ERROR
───────────────────────

Agent calls tool → Tool fails
         │
         ▼
┌─────────────────────────────────────────────┐
│  Tool Result                                │
│  ───────────                                │
│  {                                          │
│    "status": "error",                       │
│    "error": "Connection timeout",           │
│    "tool": "web_fetch"                      │
│  }                                          │
└─────────────────────────────────────────────┘
         │
         │ Return error to Claude
         ▼
Claude sees error and can:
  - Retry with different parameters
  - Skip and continue with other tasks
  - Ask for clarification (via clarification request)


2. MAX_ITERATIONS EXCEEDED
──────────────────────────

Iteration 1  → tool_use → execute → tool_result
Iteration 2  → tool_use → execute → tool_result
...
Iteration 20 → tool_use → execute → tool_result
Iteration 21 → ❌ STOP
         │
         ▼
┌─────────────────────────────────────────────┐
│  StepResult                                 │
│  ──────────                                 │
│  {                                          │
│    step_id: "s1",                           │
│    status: "fail",                          │
│    summary: "Max iterations exceeded",      │
│    acceptance_check: {                      │
│      passed: false,                         │
│      evidence: "Timeout: max_calls reached" │
│    }                                        │
│  }                                          │
└─────────────────────────────────────────────┘
         │
         │ Executor marks step as failed
         ▼
    Execution STOPS
    (entire plan fails)


3. INVALID JSON RESPONSE
─────────────────────────

Agent returns:
┌─────────────────────────────────────────────┐
│  "Here's my result:                         │
│   ```json                                   │
│   {                                         │
│     "type": "step_result",                  │
│     ...                                     │
│   }                                         │
│   ```"                                      │
└─────────────────────────────────────────────┘
         │
         │ _parse_final_result() cleans it
         ▼
┌─────────────────────────────────────────────┐
│  Cleaning Process:                          │
│  1. Find first '{' or '['                   │
│  2. Remove ```json and ```                  │
│  3. Strip whitespace                        │
│  4. Parse JSON                              │
└─────────────────────────────────────────────┘
         │
         ▼
    ✅ Valid StepResult


4. CLAUDE REFUSAL
──────────────────

Claude refuses to process request
         │
         ▼
┌─────────────────────────────────────────────┐
│  Response                                   │
│  ────────                                   │
│  stop_reason: "refusal"                     │
│  content: [                                 │
│    {                                        │
│      type: "text",                          │
│      text: "I cannot help with that..."     │
│    }                                        │
│  ]                                          │
└─────────────────────────────────────────────┘
         │
         │ Detect refusal
         ▼
┌─────────────────────────────────────────────┐
│  StepResult                                 │
│  ──────────                                 │
│  {                                          │
│    status: "fail",                          │
│    summary: "Claude refused: I cannot...",  │
│    acceptance_check: {                      │
│      passed: false,                         │
│      evidence: "Refusal: ..."               │
│    }                                        │
│  }                                          │
└─────────────────────────────────────────────┘


5. ACCEPTANCE CRITERIA FAILURE
───────────────────────────────

Agent completes but output doesn't meet criteria
         │
         ▼
┌─────────────────────────────────────────────┐
│  Validate Acceptance                        │
│  ───────────────────                        │
│  Expected: schema with ["sources", ...]     │
│  Actual: schema missing "sources" field     │
└─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│  StepResult                                 │
│  ──────────                                 │
│  {                                          │
│    status: "fail",                          │
│    acceptance_check: {                      │
│      passed: false,                         │
│      evidence: "Missing required fields"    │
│    }                                        │
│  }                                          │
└─────────────────────────────────────────────┘
```

---

## Estado de Ejecución

### ExecutionState Tracking

```
┌─────────────────────────────────────────────────────────────┐
│  ExecutionState                                             │
│  ──────────────                                             │
│  {                                                          │
│    plan_id: "pln_1234567890",                               │
│    status: "running",         ← Overall status              │
│                                                             │
│    current_step: "s3",        ← Currently executing         │
│                                                             │
│    completed_steps: [         ← Successfully done           │
│      "s1", "s2"                                             │
│    ],                                                       │
│                                                             │
│    failed_steps: [],          ← Failed steps                │
│                                                             │
│    artifacts: {               ← Artifacts by step           │
│      "s1": ["artifact://s1/research.json"],                 │
│      "s2": ["artifact://s2/outline.md"]                     │
│    },                                                       │
│                                                             │
│    start_time: "2025-01-11T10:00:00Z",                      │
│    end_time: null             ← Set when done               │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘

STATE TRANSITIONS
═════════════════

Plan Created
    │ status: "running"
    │ current_step: null
    │ completed_steps: []
    ▼
Executing s1
    │ status: "running"
    │ current_step: "s1"
    │ completed_steps: []
    ▼
s1 Done ✓
    │ status: "running"
    │ current_step: "s1"
    │ completed_steps: ["s1"]
    │ artifacts: {"s1": [...]}
    ▼
Executing s2
    │ status: "running"
    │ current_step: "s2"
    │ completed_steps: ["s1"]
    ▼
s2 Done ✓
    │ status: "running"
    │ current_step: "s2"
    │ completed_steps: ["s1", "s2"]
    │ artifacts: {"s1": [...], "s2": [...]}
    ▼
...
    ▼
All Steps Done ✓
    │ status: "completed"  ← Changed!
    │ current_step: "s7"
    │ completed_steps: ["s1"..."s7"]
    │ end_time: "2025-01-11T10:15:00Z"
```

---

## Performance y Límites

### Timeouts y Límites

```
┌──────────────────────────────────────────────────────────┐
│  LIMITS PER COMPONENT                                    │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Per Agent (Step):                                       │
│  ─────────────────                                       │
│  ┌────────────────────────────┐                          │
│  │ max_calls: 20 iterations   │ ← Configurable           │
│  │ timeout: 180s per tool     │                          │
│  │ max_tokens: 4096 per call  │                          │
│  └────────────────────────────┘                          │
│                                                          │
│  Per Tool:                                               │
│  ─────────                                               │
│  ┌────────────────────────────┐                          │
│  │ web_search: 30s timeout    │                          │
│  │ web_fetch: 60s timeout     │                          │
│  │ write_artifact: 10s        │                          │
│  │ llm_call: 120s             │                          │
│  └────────────────────────────┘                          │
│                                                          │
│  Overall:                                                │
│  ────────                                                │
│  ┌────────────────────────────┐                          │
│  │ No hard limit on plan      │                          │
│  │ execution time             │                          │
│  │ (depends on # of steps)    │                          │
│  └────────────────────────────┘                          │
│                                                          │
└──────────────────────────────────────────────────────────┘

TYPICAL TIMINGS
═══════════════

Simple Article (4 steps):
┌────────────────────────────────────────┐
│ s1: Research        → 60-90s           │
│ s2: Outline         → 15-30s           │
│ s3: Write           → 30-60s           │
│ s4: Edit            → 20-40s           │
│ ────────────────────────────           │
│ TOTAL: ~2-4 minutes                    │
└────────────────────────────────────────┘

Complex Article (8 steps):
┌────────────────────────────────────────┐
│ s1: Research        → 60-120s          │
│ s2: Outline         → 20-40s           │
│ s3-s6: Write (x4)   → 120-240s         │
│ s7: Edit            → 30-60s           │
│ s8: FactCheck       → 40-80s           │
│ ────────────────────────────           │
│ TOTAL: ~5-10 minutes                   │
└────────────────────────────────────────┘
```

---

**Fin de Diagramas de Flujo**

Para más información, ver: [ARCHITECTURE.md](./ARCHITECTURE.md)
