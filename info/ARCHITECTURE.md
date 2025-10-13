# Arquitectura del Sistema PlanAgent

## 📋 Tabla de Contenidos
1. [Visión General](#visión-general)
2. [Flujo de Ejecución](#flujo-de-ejecución)
3. [Componentes Principales](#componentes-principales)
4. [Creación de Agentes](#creación-de-agentes)
5. [Ciclo de Vida de un Step](#ciclo-de-vida-de-un-step)
6. [Herramientas (Tools)](#herramientas-tools)
7. [Artifacts](#artifacts)
8. [Diagramas de Flujo](#diagramas-de-flujo)

---

## Visión General

**PlanAgent** es un sistema de orquestación de agentes autónomos que descompone tareas complejas en subtareas ejecutables. Cada subtarea es realizada por un agente efímero especializado que tiene autonomía para usar herramientas iterativamente.

### Filosofía del Sistema
- **Plan-and-Spawn**: Primero se genera un plan, luego se spawanean agentes para ejecutarlo
- **Agentes Efímeros**: Los agentes se crean para una tarea específica y mueren al terminarla
- **Alta Autonomía**: Cada agente puede hacer múltiples llamadas a herramientas sin supervisión
- **Artifact-Driven**: Los agentes comunican resultados mediante artifacts (archivos)

---

## Flujo de Ejecución

### 1. Punto de Entrada

```bash
python -m plan_spawn.main article "Peligros de la IA en 2025"
```

**Archivo:** `src/plan_spawn/main.py`

```python
async def main():
    # 1. Parsear comando de línea
    command = sys.argv[1]  # "article"
    objective = " ".join(sys.argv[2:])  # "Peligros de la IA en 2025"

    # 2. Llamar al modo correspondiente
    if command == "article":
        await run_article_mode(objective)
```

### 2. Inicialización del Orchestrator

**Archivo:** `src/plan_spawn/core/orchestrator.py`

```python
class Orchestrator:
    def __init__(self):
        # Componentes principales
        self.artifact_store = ArtifactStore()      # Gestión de artifacts
        self.tool_registry = get_registry()        # Registro de herramientas
        self.planner = Planner()                   # Generador de planes
        self.agent_runtime = AgentRuntime()        # Ejecutor de agentes
        self.executor = Executor()                 # Orquestador de steps
```

### 3. Generación del Plan

**Archivo:** `src/plan_spawn/core/planner.py`

El Planner usa Claude como un "meta-agente" para descomponer la tarea:

```
Usuario: "Escribir artículo sobre peligros de IA"
         ↓
    [Planner]
         ↓
Plan con 7 steps:
  s1: ResearchAgent    → Investigar información
  s2: OutlineAgent     → Crear estructura (depende de s1)
  s3: WriterAgent      → Redactar intro (depende de s2)
  s4: WriterAgent      → Redactar cuerpo (depende de s2)
  s5: WriterAgent      → Redactar conclusión (depende de s2)
  s6: EditorAgent      → Revisar artículo (depende de s3,s4,s5)
  s7: FactCheckerAgent → Verificar datos (depende de s6)
```

**Estructura del Plan:**
```json
{
  "plan_id": "pln_1234567890",
  "objective": "Peligros de la IA en 2025",
  "steps": [
    {
      "id": "s1",
      "title": "Investigación sobre peligros de IA",
      "depends_on": [],
      "agent_spec": {
        "role": "ResearchAgent",
        "system_prompt": "Eres un agente de investigación...",
        "tools": ["web_search", "web_fetch", "write_artifact"],
        "io": {
          "input_refs": [],
          "output_decl": [{"name": "research.json", "type": "json"}]
        },
        "stop_conditions": {
          "max_calls": 20,
          "accept_on": "acceptance_pass"
        }
      },
      "acceptance": {
        "type": "schema",
        "path_ref": "artifact://s1/research.json",
        "schema": {
          "required": ["sources", "key_points", "summary"]
        }
      }
    }
    // ... más steps
  ]
}
```

### 4. Ejecución del Plan

**Archivo:** `src/plan_spawn/core/executor.py`

El Executor coordina la ejecución respetando dependencias:

```python
async def execute_plan(self, plan: Plan):
    # 1. Calcular orden de ejecución (topological sort)
    execution_order = self._compute_execution_order(plan)
    # Ejemplo: ['s1', 's2', 's3', 's4', 's5', 's6', 's7']

    # 2. Ejecutar cada step secuencialmente
    for step_id in execution_order:
        step = self._get_step(plan, step_id)

        # 3. Construir contexto del step
        context = self._build_step_context(plan, step, state)
        # Incluye: objective, artifacts de dependencias, contexto inline

        # 4. Ejecutar el step
        result = await self.agent_runtime.execute_step(step, context)

        # 5. Validar resultado
        if result.acceptance_check.passed:
            state.completed_steps.append(step_id)
            state.artifacts[step_id] = result.artifacts
        else:
            state.failed_steps.append(step_id)
            break  # Fallo crítico
```

---

## Componentes Principales

### 1. Planner

**Responsabilidad:** Generar planes de ejecución usando Claude

```python
class Planner:
    async def create_plan(self, task: TaskRequest) -> Plan:
        # 1. Construir system prompt con arquetipos de agentes
        system_prompt = self._build_planner_system_prompt()

        # 2. Construir user prompt con objetivo y restricciones
        user_prompt = self._build_planner_user_prompt(task)

        # 3. Llamar a Claude API
        response = self.client.messages.create(
            model="claude-sonnet-4",
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        # 4. Parsear JSON y validar plan
        plan = PlanResponse(**json.loads(response.content[0].text))
        return plan.plan
```

**Arquetipos de Agentes Disponibles:**
- **ResearchAgent**: Busca información (web_search, web_fetch)
- **OutlineAgent**: Crea estructura del artículo (read_artifact, llm_call)
- **WriterAgent**: Redacta contenido (read_artifact, llm_call)
- **EditorAgent**: Revisa y mejora (read_artifact, quality_check)
- **FactCheckerAgent**: Verifica datos (web_search, fact_verify)

### 2. AgentRuntime

**Responsabilidad:** Ejecutar steps individuales spawneando agentes efímeros

```python
class AgentRuntime:
    async def execute_step(self, step: Step, context: Dict) -> StepResult:
        # 1. Inicializar conversación
        messages = [{
            "role": "user",
            "content": json.dumps({
                "type": "execute_step",
                "step_id": step.id,
                "context": context
            })
        }]

        # 2. Loop de herramientas (máximo max_calls iteraciones)
        iteration = 0
        max_iterations = step.agent_spec.stop_conditions.max_calls

        while iteration < max_iterations:
            iteration += 1

            # 3. Llamar a Claude con tools disponibles
            response = self.client.messages.create(
                model="claude-sonnet-4",
                system=step.agent_spec.system_prompt,
                messages=messages,
                tools=tool_schemas
            )

            # 4. Procesar respuesta según stop_reason
            if response.stop_reason == "end_turn":
                # Agente terminó → parsear step_result
                return self._parse_final_result(response)

            elif response.stop_reason == "tool_use":
                # Agente quiere usar herramientas
                for tool_use in response.content:
                    result = await self._execute_tool(
                        tool_use.name,
                        tool_use.input,
                        step.id
                    )
                    tool_results.append(result)

                # Añadir a conversación y continuar
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

            elif response.stop_reason == "max_tokens":
                # Hit límite de tokens → ejecutar tools pendientes
                # y pedir al agente que continúe
                ...

        # 5. Timeout: max_iterations alcanzado
        return StepResult(status="fail", summary="Max iterations exceeded")
```

### 3. Executor

**Responsabilidad:** Coordinar ejecución de múltiples steps con dependencias

**Algoritmo de Ejecución:**
1. **Topological Sort**: Ordenar steps respetando `depends_on`
2. **Ejecución Secuencial**: Ejecutar steps en orden
3. **Context Building**: Pasar artifacts de dependencias al step actual
4. **Validación**: Verificar acceptance criteria
5. **Error Handling**: Detener en caso de fallo crítico

### 4. ArtifactStore

**Responsabilidad:** Gestionar archivos generados por agentes

```python
class ArtifactStore:
    base_path = "./artifacts"

    def save(self, step_id: str, name: str, content: str) -> str:
        # Guardar en: artifacts/s1/research.json
        path = self.base_path / step_id / name
        path.write_text(content)
        return f"artifact://{step_id}/{name}"

    def load(self, uri: str) -> str:
        # Cargar desde URI: artifact://s1/research.json
        step_id, name = self._parse_uri(uri)
        path = self.base_path / step_id / name
        return path.read_text()
```

### 5. ToolRegistry

**Responsabilidad:** Registrar y ejecutar herramientas disponibles

```python
class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, name: str, function: Callable, schema: Dict):
        self.tools[name] = Tool(name, function, schema)

    def get_schemas_for_agent(self, role: str, tool_names: List[str]):
        # Devolver schemas de tools permitidas para este agente
        return [self.tools[name].schema for name in tool_names]
```

---

## Creación de Agentes

### ¿Cómo se Crea un Agente?

**Los agentes NO son objetos persistentes**. Son efímeros y se "materializan" mediante:

1. **System Prompt Dinámico**: El Planner genera un system prompt específico
2. **Contexto Inyectado**: Se pasa información del objetivo y artifacts previos
3. **Tools Disponibles**: Se especifican qué herramientas puede usar
4. **API Call a Claude**: Cada iteración es una llamada API con el contexto completo

### Ejemplo de Creación de ResearchAgent

**Generado por Planner:**
```json
{
  "role": "ResearchAgent",
  "system_prompt": "Eres un agente de investigación.

  Sigue estos pasos EXACTAMENTE:
  1. Usa web_search 3-5 veces para buscar información
  2. Usa web_fetch 2-3 veces para profundizar
  3. OBLIGATORIO: write_artifact con research.json
  4. Responde INMEDIATAMENTE con JSON step_result

  DESPUÉS de write_artifact, NO uses más herramientas.
  Tu PRÓXIMA respuesta debe ser SOLO:
  {\"type\":\"step_result\",\"step_id\":\"s1\",\"status\":\"ok\",...}",

  "tools": ["web_search", "web_fetch", "write_artifact"]
}
```

**Ejecución:**
```python
# Iteración 1
response = anthropic.messages.create(
    model="claude-sonnet-4",
    system="Eres un agente de investigación...",
    messages=[
        {"role": "user", "content": '{"type":"execute_step","context":{...}}'}
    ],
    tools=[web_search_schema, web_fetch_schema, write_artifact_schema]
)
# Claude decide: quiero usar web_search
# stop_reason = "tool_use"

# Iteración 2
response = anthropic.messages.create(
    ...
    messages=[
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": [tool_use_block]},
        {"role": "user", "content": [tool_result_block]}
    ]
)
# Claude decide: quiero usar web_search otra vez
# stop_reason = "tool_use"

# ... (3-5 iteraciones más)

# Iteración 7
# Claude decide: ya tengo suficiente info, voy a guardar
# usa write_artifact → tool_result: success

# Iteración 8
# Claude decide: ya terminé, devuelvo resultado
# stop_reason = "end_turn"
# content: '{"type":"step_result","step_id":"s1",...}'
```

---

## Ciclo de Vida de un Step

### Diagrama de Estados

```
┌─────────┐
│ PENDING │  (Step creado por Planner)
└────┬────┘
     │
     ▼
┌─────────┐
│ RUNNING │  (Executor llama a AgentRuntime)
└────┬────┘
     │
     ├──────────┐
     ▼          ▼
┌──────┐   ┌───────┐
│ DONE │   │ ERROR │
└──────┘   └───────┘
```

### Fases Detalladas

#### Fase 1: Inicialización
```python
step = Step(
    id="s1",
    title="Investigación sobre peligros de IA",
    status="pending",
    agent_spec=AgentSpec(...),
    acceptance=Acceptance(...)
)
```

#### Fase 2: Ejecución (Loop de Herramientas)
```
Iteración 1: web_search("AI risks 2025") → 10 resultados
Iteración 2: web_search("AI security threats") → 8 resultados
Iteración 3: web_search("AI job displacement") → 12 resultados
Iteración 4: web_fetch("https://stanford.edu/ai-index") → contenido HTML
Iteración 5: web_fetch("https://safe.ai/risks") → contenido HTML
Iteración 6: write_artifact("research.json", {...}) → artifact://s1/research.json
Iteración 7: end_turn → JSON step_result
```

#### Fase 3: Validación
```python
# Validar formato del resultado
result = StepResult(**json.loads(agent_response))

# Validar acceptance criteria
if acceptance.type == "schema":
    artifact_content = artifact_store.load(acceptance.path_ref)
    validate_schema(artifact_content, acceptance.schema)

# Marcar como DONE o ERROR
if result.acceptance_check.passed:
    step.status = "done"
else:
    step.status = "error"
```

---

## Herramientas (Tools)

### Registro de Herramientas

**Archivo:** `src/plan_spawn/core/tools/web_tools.py`

```python
@register_tool(
    name="web_search",
    description="Buscar información en la web usando Brave Search API",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Consulta de búsqueda"},
            "count": {"type": "number", "description": "Número de resultados"}
        },
        "required": ["query"]
    }
)
async def web_search(query: str, count: int = 10, **kwargs) -> Dict:
    # Implementación de búsqueda web
    results = await brave_api.search(query, count)
    return {
        "status": "success",
        "results": results
    }
```

### Herramientas Disponibles

| Herramienta | Descripción | Parámetros |
|-------------|-------------|------------|
| `web_search` | Buscar en web | query, count |
| `web_fetch` | Obtener contenido de URL | url |
| `write_artifact` | Guardar archivo | name, content, content_type |
| `read_artifact` | Leer archivo | uri |
| `list_artifacts` | Listar artifacts | step_id |
| `llm_call` | Llamar a LLM para tarea específica | prompt, context |
| `quality_check` | Verificar calidad de texto | content, criteria |
| `fact_verify` | Verificar hechos | claim, sources |

### Inyección de Dependencias

Las herramientas reciben parámetros inyectados automáticamente:

```python
# Lo que el agente pide:
tool_input = {"name": "research.json", "content": "{...}"}

# Lo que se ejecuta:
injected_params = {
    "step_id": "s1",
    "artifact_store": self.artifact_store,
    "current_step_id": "s1"
}
merged = {**tool_input, **injected_params}

result = await write_artifact(**merged)
```

---

## Artifacts

### Sistema de URIs

Los artifacts usan un sistema de URIs para identificación:

```
artifact://<step_id>/<filename>

Ejemplos:
artifact://s1/research.json
artifact://s2/outline.md
artifact://s3/introduction.md
```

### Estructura de Directorios

```
artifacts/
├── _metadata/          # Metadatos de artifacts
├── s1/                 # Artifacts del step 1
│   ├── research.json
│   └── _metadata.json
├── s2/                 # Artifacts del step 2
│   ├── outline.md
│   └── _metadata.json
├── s3/
│   ├── introduction.md
│   └── _metadata.json
└── ...
```

### Metadatos de Artifacts

```json
{
  "uri": "artifact://s1/research.json",
  "step_id": "s1",
  "filename": "research.json",
  "content_type": "json",
  "created_at": "2025-01-11T10:30:00Z",
  "size_bytes": 15234,
  "checksum": "sha256:abc123..."
}
```

---

## Diagramas de Flujo

### Flujo Completo de Ejecución

```
┌─────────────┐
│   Usuario   │
│ "article X" │
└──────┬──────┘
       │
       ▼
┌──────────────┐
│  main.py     │
│ Parsear args │
└──────┬───────┘
       │
       ▼
┌─────────────────┐
│  Orchestrator   │
│ .run(objective) │
└──────┬──────────┘
       │
       ├─────────────────────────────┐
       ▼                             ▼
┌─────────────┐              ┌──────────────┐
│  Planner    │              │  Executor    │
│ Crear plan  │─────Plan────▶│ Ejecutar     │
│             │              │ steps        │
└─────────────┘              └──────┬───────┘
                                    │
                                    │ Para cada step:
                                    ▼
                             ┌──────────────┐
                             │AgentRuntime  │
                             │.execute_step │
                             └──────┬───────┘
                                    │
                                    │ Loop iterativo:
                                    ▼
                             ┌──────────────┐
                             │Claude API    │
                             │+ Tools       │
                             └──────┬───────┘
                                    │
                                    ▼
                             ┌──────────────┐
                             │StepResult    │
                             │+ Artifacts   │
                             └──────────────┘
```

### Flujo de un Agente Individual

```
┌───────────────────────────────────────────┐
│        Agent Iteration Loop               │
│                                           │
│  ┌─────────────────────────────────────┐ │
│  │ 1. Claude API Call                  │ │
│  │    - System prompt                  │ │
│  │    - Conversación                   │ │
│  │    - Tool schemas                   │ │
│  └────────────┬────────────────────────┘ │
│               │                           │
│               ▼                           │
│  ┌─────────────────────────────────────┐ │
│  │ 2. Check stop_reason                │ │
│  └────────┬────────────┬────────────┬──┘ │
│           │            │            │    │
│   ┌───────▼──┐   ┌────▼────┐  ┌───▼───┐│
│   │end_turn  │   │tool_use │  │max_tok││
│   └────┬─────┘   └────┬────┘  └───┬───┘│
│        │              │            │    │
│    ┌───▼────┐    ┌───▼─────┐  ┌──▼───┐│
│    │Parse   │    │Execute  │  │Handle││
│    │result  │    │tools    │  │      ││
│    │        │    │         │  │      ││
│    │EXIT ✓  │    │Loop ↻   │  │Loop ↻││
│    └────────┘    └─────────┘  └──────┘│
│                                         │
└─────────────────────────────────────────┘
```

### Comunicación entre Steps vía Artifacts

```
Step s1 (ResearchAgent)
    │
    │ write_artifact
    ▼
┌──────────────────┐
│ artifact://s1/   │
│ research.json    │
└────────┬─────────┘
         │
         │ read_artifact
         ▼
Step s2 (OutlineAgent)
    │
    │ write_artifact
    ▼
┌──────────────────┐
│ artifact://s2/   │
│ outline.md       │
└────────┬─────────┘
         │
         │ read_artifact
         ▼
Step s3 (WriterAgent)
    │
    │ write_artifact
    ▼
┌──────────────────┐
│ artifact://s3/   │
│ article.md       │
└──────────────────┘
```

---

## Configuración

### Variables de Entorno

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
BRAVE_API_KEY=BSA...          # Opcional, para web_search
MAX_ITERATIONS_PER_STEP=20
MAX_TOKENS_PER_CALL=4096
CLAUDE_MODEL=claude-sonnet-4
ARTIFACTS_PATH=./artifacts
```

### Ajustar Comportamiento de Agentes

**En `planner.py`:**
- Modificar system prompts de arquetipos
- Ajustar límites de tool calls
- Cambiar criterios de aceptación

**En `agent_runtime.py`:**
- Modificar `max_iterations` default
- Ajustar timeout de tools
- Cambiar estrategia de parsing de respuestas

---

## Debugging y Logging

### Niveles de Logging

El sistema ahora provee logging detallado en tiempo real:

```
→ Executing s1: Investigación sobre peligros de IA
  Agent: ResearchAgent
  → Iteration 1/20
    🔧 web_search
      ✓ Success
  → Iteration 2/20
    🔧 web_search
      ✓ Success
  → Iteration 3/20
    🔧 write_artifact
      ✓ Success
  → Iteration 4/20
    (end_turn)
  ✓ Completed in 45.2s
  Artifacts: artifact://s1/research.json
```

### Logs de Error Detallados

Cuando un step falla, se muestran los últimos 30 logs:

```
✗ Failed: Agent did not return valid JSON
Evidence: Invalid JSON response
Execution log (last 30 entries):
  Iteration 1
  Tool call: web_search
  Tool result: success
  Iteration 2
  Tool call: web_fetch
  Tool result: error
    Error details: Connection timeout after 30s
  ...
```

---

## Extensibilidad

### Añadir Nuevas Herramientas

```python
# src/plan_spawn/core/tools/my_tools.py

@register_tool(
    name="my_custom_tool",
    description="Description for Claude",
    parameters={
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."}
        },
        "required": ["param1"]
    }
)
async def my_custom_tool(param1: str, step_id: str = None, **kwargs) -> Dict:
    # Tu implementación
    result = do_something(param1)
    return {"status": "success", "result": result}
```

### Añadir Nuevos Arquetipos de Agentes

En `planner.py`, añadir al system prompt:

```python
**MyCustomAgent**: Descripción del agente
- Tools: tool1, tool2, tool3
- Genera: output_file.ext con formato específico
- Acceptance: tipo de validación
- System prompt con PASOS:
  1. Paso 1
  2. Paso 2
  3. OBLIGATORIO: write_artifact
  4. Responder JSON
```

---

## Limitaciones Conocidas

1. **Planner no siempre perfecto**: Puede generar planes con acceptance criteria inválidos
2. **Agentes pueden loopearse**: Si system prompt no es suficientemente directivo
3. **Sin paralelización**: Steps se ejecutan secuencialmente (no en paralelo)
4. **Sin replanificación**: Si un step falla, no se regenera el plan
5. **Sin persistencia**: Si el proceso se interrumpe, se pierde el progreso

---

## Próximas Mejoras

- [ ] Retry automático de steps fallidos
- [ ] Replanificación dinámica
- [ ] Ejecución paralela de steps independientes
- [ ] Persistencia de estado a disco
- [ ] Dashboard web para monitoreo en tiempo real
- [ ] Soporte para múltiples modelos (GPT-4, Gemini, etc.)
- [ ] Cache de resultados de herramientas
- [ ] Validación más robusta de planes generados

---

## Referencias

- **Anthropic API Docs**: https://docs.anthropic.com/
- **Tool Use Guide**: https://docs.anthropic.com/en/docs/build-with-claude/tool-use
- **Agentic Patterns**: https://www.anthropic.com/research/building-effective-agents

---

**Versión del documento:** 1.0
**Última actualización:** 2025-01-11
