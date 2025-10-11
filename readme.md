# Plan-and-Spawn Agent System

Sistema de orquestación de agentes autónomos basado en el patrón Plan-and-Spawn. Permite descomponer tareas complejas en subtareas ejecutadas por agentes especializados efímeros.

## 🚀 Características

- **Planificación Inteligente**: Claude genera planes adaptativos según la tarea
- **Agentes Autónomos**: Cada agente puede usar herramientas, re-planificar y tomar decisiones
- **Especialización**: Arquetipos predefinidos (Research, Writer, Editor, etc.)
- **Trazabilidad**: Sistema de artifacts con URIs lógicas
- **CLI Interactivo**: Interface de línea de comandos con Rich

## 📁 Estructura del Proyecto

```
plan-and-spawn-agent/
├── src/
│   └── plan_spawn/
│       ├── __init__.py
│       ├── main.py                 # CLI entry point
│       ├── core/
│       │   ├── __init__.py
│       │   ├── models.py           # Pydantic models
│       │   ├── planner.py          # Plan generation
│       │   ├── executor.py         # Plan execution
│       │   ├── agent_runtime.py    # Agent execution
│       │   ├── orchestrator.py     # Main orchestrator
│       │   ├── storage/
│       │   │   ├── __init__.py
│       │   │   └── artifacts.py    # Artifact management
│       │   └── tools/
│       │       ├── __init__.py
│       │       ├── registry.py     # Tool registry
│       │       ├── web_tools.py    # Web search & fetch
│       │       ├── file_tools.py   # File operations
│       │       └── llm_tools.py    # LLM utilities
│       └── config/
│           ├── __init__.py
│           └── settings.py         # Configuration
├── artifacts/                      # Generated artifacts
├── .env                           # Environment variables
├── requirements.txt
└── README.md
```

## 🛠️ Instalación

```bash
# 1. Clonar repositorio
git clone <repo-url>
cd plan-and-spawn-agent

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env y añadir tu ANTHROPIC_API_KEY
```

## 🎯 Uso

### Generar un Artículo

```bash
python -m plan_spawn.main article "Los riesgos de la inteligencia artificial en 2025"
```

### Modo Interactivo

```bash
python -m plan_spawn.main interactive
```

### Ver Artifacts Generados

```bash
ls -la artifacts/
```

## 📊 Ejemplo de Flujo

```
Usuario: "Escribe un artículo sobre IA cuántica"
    ↓
Planner: Genera plan con 6 steps
    ↓
Executor: Ejecuta secuencialmente con dependencias
    ├─ s1: ResearchAgent busca información
    ├─ s2: OutlineAgent estructura contenido
    ├─ s3: WriterAgent escribe intro
    ├─ s4: WriterAgent escribe cuerpo
    ├─ s5: WriterAgent escribe conclusión
    └─ s6: EditorAgent revisa y finaliza
    ↓
Resultado: artifact://s6/article_final.md
```

## 🔧 Configuración Avanzada

### Ajustar Autonomía de Agentes

En `config/settings.py`:
```python
MAX_ITERATIONS_PER_STEP = 15  # Aumentar para mayor autonomía
```

### Añadir Nuevas Herramientas

1. Crear función en `core/tools/`
2. Registrar en registry
3. Añadir a lista de tools disponibles

### Personalizar Arquetipos

Editar prompts en `core/planner.py` → `_build_planner_system_prompt()`

## 💰 Costes Estimados

| Tarea | Tokens | Coste Aprox. |
|-------|--------|--------------|
| Artículo corto (500 palabras) | 30K-50K | $0.30-$0.50 |
| Artículo medio (1500 palabras) | 70K-100K | $0.70-$1.00 |
| Investigación profunda | 150K+ | $1.50+ |

*Basado en Claude Sonnet 4.5 pricing*

## 🐛 Troubleshooting

**Error: "ANTHROPIC_API_KEY not found"**
- Verifica que `.env` existe y contiene la clave

**Error: "Tool execution failed"**
- Revisa logs en `artifacts/<step_id>/logs.txt`
- Verifica conexión a internet para web_search/web_fetch

**Agente no termina (loop infinito)**
- Revisa `MAX_ITERATIONS_PER_STEP` en `.env`
- El agente se detendrá automáticamente al límite

## 📝 Licencia

MIT License
