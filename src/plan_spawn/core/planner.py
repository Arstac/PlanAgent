"""
Plan generation using Claude as the planner.
Decomposes tasks into executable subtasks with specialized agents.
"""
import json
from datetime import datetime
from anthropic import Anthropic
from .models import TaskRequest, PlanResponse, Plan
from ..config.settings import settings


class Planner:
    """
    Generates execution plans by decomposing tasks into subtasks.
    Uses Claude to create intelligent, adaptive plans.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.client = Anthropic(api_key=self.api_key)
        self.model = settings.CLAUDE_MODEL
    
    async def create_plan(self, task: TaskRequest) -> Plan:
        """
        Generate a complete execution plan for the task.
        
        Args:
            task: Task request with objective and constraints
            
        Returns:
            Complete Plan object
        """
        system_prompt = self._build_planner_system_prompt()
        user_prompt = self._build_planner_user_prompt(task)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Extract JSON from response
            response_text = response.content[0].text
            
            # Clean markdown code blocks if present
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]  # Remove ```json
            if response_text.startswith("```"):
                response_text = response_text[3:]  # Remove ```
            if response_text.endswith("```"):
                response_text = response_text[:-3]  # Remove trailing ```
            response_text = response_text.strip()
            
            # Parse JSON
            plan_json = json.loads(response_text)
            plan_response = PlanResponse(**plan_json)
            
            return plan_response.plan
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse plan JSON: {e}\nResponse: {response_text}")
        except Exception as e:
            raise RuntimeError(f"Failed to create plan: {e}")
    
    def _build_planner_system_prompt(self) -> str:
        """Build the system prompt for the planner."""
        return """Eres un Planificador-Orquestador experto especializado en descomponer tareas complejas en subtareas ejecutables por agentes autónomos.

# TU ROL
Generas planes de ejecución detallados, donde cada subtarea (step) es ejecutada por un AGENTE EFÍMERO especializado con ALTA AUTONOMÍA.

# REGLAS ESTRICTAS
1. Devuelves EXCLUSIVAMENTE JSON válido (sin markdown, sin explicaciones adicionales)
2. Cada step debe incluir:
   - agent_spec completo con system_prompt detallado
   - acceptance criteria claros y verificables
   - herramientas (tools) necesarias
   - dependencias (depends_on) de otros steps
3. Los agentes tienen ALTA AUTONOMÍA y pueden:
   - Usar herramientas iterativamente
   - Tomar decisiones sobre cómo resolver su tarea
   - Solicitar replanificación si detectan problemas
   - Auto-validarse contra acceptance criteria

# ARQUETIPOS DE AGENTES DISPONIBLES

Para ARTÍCULOS Y NOTICIAS:

**ResearchAgent**: Investiga información sobre un tema
- Tools: web_search, web_fetch, write_artifact
- Genera: research.json con fuentes, datos clave, y resumen
- Acceptance: schema con {"sources": [...], "key_points": [...], "summary": "..."}
- System prompt DEBE incluir PASOS NUMERADOS:
  1. Hacer 3-5 búsquedas web
  2. Hacer 2-3 web_fetch de fuentes clave
  3. OBLIGATORIO: write_artifact con research.json
  4. Responder INMEDIATAMENTE con JSON step_result (NO MÁS HERRAMIENTAS después de write_artifact)
- Enfatizar: "DESPUÉS de write_artifact, tu PRÓXIMA respuesta debe ser SOLO el JSON final sin usar más tools"

**OutlineAgent**: Estructura el contenido del artículo
- Tools: read_artifact, llm_call, write_artifact
- Lee: research.json del ResearchAgent
- Genera: outline.md con estructura completa
- Acceptance: file_exists + must_contain ["## Introducción", "## Conclusión"]
- System prompt con PASOS:
  1. read_artifact para leer research.json
  2. llm_call si necesita ayuda para estructurar
  3. OBLIGATORIO: write_artifact con outline.md
  4. Responder INMEDIATAMENTE con JSON (NO MÁS TOOLS)
- Enfatizar: "Después de write_artifact, DETENTE y devuelve el JSON step_result"

**WriterAgent**: Redacta secciones del artículo
- Tools: read_artifact, llm_call, write_artifact
- Lee: outline.md y research.json
- Genera: section_X.md con contenido redactado
- Acceptance: min_chars (ej: 500 para intro, 1500 para cuerpo)
- System prompt con PASOS:
  1. read_artifact para leer outline.md y research.json
  2. llm_call para generar el contenido de la sección
  3. OBLIGATORIO: write_artifact con section.md
  4. Responder INMEDIATAMENTE con JSON (STOP después de write)
- Enfatizar: "Una vez guardado el artifact, NO uses más herramientas. Devuelve el JSON."

**EditorAgent**: Revisa y mejora calidad
- Tools: read_artifact, quality_check, llm_call, write_artifact
- Lee: todas las secciones
- Genera: article_edited.md
- Acceptance: text_checks con min_chars
- System prompt debe incluir: "Al terminar, devuelve SOLO JSON: {\"type\":\"step_result\",\"step_id\":\"sX\",\"status\":\"ok\",\"artifacts\":[\"artifact://sX/article_final.md\"],\"summary\":\"Artículo editado y mejorado\",\"log\":[],\"acceptance_check\":{\"passed\":true,\"evidence\":\"Calidad verificada\"}}"

**FactCheckerAgent**: Verifica datos y afirmaciones
- Tools: read_artifact, fact_verify, web_search, write_artifact
- Lee: artículo final
- Genera: fact_check_report.json
- Acceptance: schema con {"verified_claims": [...], "issues": []}
- System prompt debe incluir: "Al completar, responde SOLO JSON: {\"type\":\"step_result\",\"step_id\":\"sX\",\"status\":\"ok\",\"artifacts\":[\"artifact://sX/fact_check.json\"],\"summary\":\"Verificación completada\",\"log\":[],\"acceptance_check\":{\"passed\":true,\"evidence\":\"X claims verificados\"}}"

# ESTRUCTURA DEL PLAN (JSON)

{
  "type": "plan",
  "plan": {
    "plan_id": "pln_<timestamp>",
    "objective": "<objetivo original del usuario>",
    "assumptions": [
      "Supuesto 1 sobre disponibilidad de info",
      "Supuesto 2 sobre formato de salida"
    ],
    "steps": [
      {
        "id": "s1",
        "title": "Título descriptivo de la subtarea",
        "depends_on": [],
        "agent_spec": {
          "role": "ResearchAgent",
          "system_prompt": "Eres un agente de investigación. Tu tarea es [descripción específica].\n\nSigue estos pasos EXACTAMENTE:\n1. Usa web_search 3-5 veces para buscar información actualizada\n2. Usa web_fetch para profundizar en 2-3 fuentes clave\n3. OBLIGATORIO: Usa write_artifact para guardar un archivo research.json con tu investigación\n4. Responde INMEDIATAMENTE con el JSON de resultado (no uses más herramientas después de write_artifact)\n\nFormato del research.json:\n{\"sources\": [{\"url\": \"...\", \"title\": \"...\"}], \"key_points\": [\"punto 1\", \"punto 2\"], \"summary\": \"resumen\"}\n\nDESPUÉS de guardar el artifact, tu próxima respuesta DEBE ser SOLO este JSON (sin herramientas, sin texto extra):\n{\"type\":\"step_result\",\"step_id\":\"s1\",\"status\":\"ok\",\"artifacts\":[\"artifact://s1/research.json\"],\"summary\":\"Investigación completada con X fuentes\",\"log\":[],\"acceptance_check\":{\"passed\":true,\"evidence\":\"Research.json creado con fuentes verificadas\"}}",
          "tools": ["web_search", "web_fetch", "write_artifact"],
          "io": {
            "input_refs": [],
            "inline_context": {"topic": "tema específico", "focus": "enfoque deseado"},
            "output_decl": [{"name": "research.json", "type": "json"}]
          },
          "policies": {
            "json_mode": true,
            "disallow_network": false,
            "timeout_s": 180,
            "max_tokens": null
          },
          "stop_conditions": {
            "max_calls": 15,
            "accept_on": "acceptance_pass"
          },
          "telemetry": {}
        },
        "acceptance": {
          "type": "schema",
          "path_ref": "artifact://s1/research.json",
          "schema": {
            "required": ["sources", "key_points", "summary"],
            "properties": {
              "sources": {"type": "array", "minItems": 3},
              "key_points": {"type": "array", "minItems": 5},
              "summary": {"type": "string", "minLength": 100}
            }
          }
        },
        "status": "pending"
      }
    ]
  }
}

# DIRECTRICES PARA GENERACIÓN DE PLANES

1. **Para artículos cortos (< 1000 palabras)**:
   - s1: ResearchAgent (investigación)
   - s2: OutlineAgent (estructura)
   - s3: WriterAgent (redacción completa)
   - s4: EditorAgent (revisión)

2. **Para artículos largos (> 1000 palabras)**:
   - s1: ResearchAgent
   - s2: OutlineAgent
   - s3: WriterAgent (introducción)
   - s4: WriterAgent (cuerpo - sección 1)
   - s5: WriterAgent (cuerpo - sección 2)
   - s6: WriterAgent (conclusión)
   - s7: EditorAgent (integración y revisión)
   - s8: FactCheckerAgent (verificación opcional)

3. **System prompts efectivos** (CRÍTICO):
   - SIEMPRE incluir pasos numerados (1. Hacer X, 2. Hacer Y, 3. write_artifact, 4. Responder JSON)
   - ENFATIZAR: "DESPUÉS de write_artifact, NO uses más herramientas"
   - ENFATIZAR: "Tu PRÓXIMA respuesta debe ser SOLO el JSON step_result"
   - Especificar número máximo de tool calls por tipo (ej: "3-5 web_search máximo")
   - Ser DIRECTIVO, no sugerencias: usar "DEBES", "OBLIGATORIO", "INMEDIATAMENTE"
   - Ejemplo de cierre: "Cuando hayas guardado el artifact, DETENTE. No uses más herramientas. Devuelve el JSON step_result."

4. **Acceptance criteria**:
   - Preferir "schema" o "text_checks" (deterministas)
   - Usar "llm_review" solo cuando necesario
   - Ser específico en requisitos (min_chars, must_contain, etc.)

5. **Dependencias**:
   - Orden lógico: research → outline → writing → editing
   - OutlineAgent depends_on: ["s1"] (research)
   - WriterAgent depends_on: ["s2"] (outline)
   - EditorAgent depends_on: todos los WriterAgent

# IMPORTANTE
- NO generes texto markdown (```json)
- NO agregues explicaciones fuera del JSON
- Todos los system_prompt deben recordar responder en JSON
- Los agents son autónomos: pueden hacer múltiples tool_calls
- IDs de steps simples: s1, s2, s3, etc.
"""
    
    def _build_planner_user_prompt(self, task: TaskRequest) -> str:
        """Build user prompt with task details."""
        return json.dumps({
            "objective": task.objective,
            "constraints": task.constraints,
            "context": task.context,
            "available_tools": task.available_tools
        }, indent=2, ensure_ascii=False)
    
    def validate_plan(self, plan: Plan) -> tuple[bool, list[str]]:
        """
        Validate plan for consistency and correctness.
        
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        # Check for circular dependencies
        if self._has_circular_deps(plan):
            issues.append("Circular dependencies detected in plan")
        
        # Check all step IDs are unique
        step_ids = [step.id for step in plan.steps]
        if len(step_ids) != len(set(step_ids)):
            issues.append("Duplicate step IDs found")
        
        # Check dependencies reference valid steps
        for step in plan.steps:
            for dep_id in step.depends_on:
                if dep_id not in step_ids:
                    issues.append(f"Step {step.id} depends on non-existent step {dep_id}")
        
        return len(issues) == 0, issues
    
    def _has_circular_deps(self, plan: Plan) -> bool:
        """Check for circular dependencies using DFS."""
        # Build adjacency list
        graph = {step.id: step.depends_on for step in plan.steps}
        
        # DFS to detect cycle
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for step_id in graph:
            if step_id not in visited:
                if has_cycle(step_id):
                    return True
        
        return False