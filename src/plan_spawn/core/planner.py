"""
Plan generation using OpenAI as the planner.
Decomposes tasks into executable subtasks with specialized agents.
"""
import json
from datetime import datetime
from openai import OpenAI
from .models import TaskRequest, PlanResponse, Plan
from ..config.settings import settings


class Planner:
    """
    Generates execution plans by decomposing tasks into subtasks.
    Uses OpenAI to create intelligent, adaptive plans.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.client = OpenAI(api_key=self.api_key)
        self.model = settings.OPENAI_MODEL
    
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
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=8000,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )

            # Extract JSON from response
            response_text = response.choices[0].message.content
            
            # Clean markdown code blocks if present
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]  # Remove ```json
            if response_text.startswith("```"):
                response_text = response_text[3:]  # Remove ```
            if response_text.endswith("```"):
                response_text = response_text[:-3]  # Remove trailing ```
            response_text = response_text.strip()

            # Fix invalid control characters in JSON strings
            # This handles newlines and other control characters that should be escaped
            response_text = self._fix_json_control_characters(response_text)

            # Parse JSON
            plan_json = json.loads(response_text)

            # Fix common acceptance type errors before validation
            plan_json = self._fix_acceptance_types(plan_json)

            plan_response = PlanResponse(**plan_json)

            return plan_response.plan

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse plan JSON: {e}\nResponse: {response_text}")
        except Exception as e:
            # Log the problematic JSON for debugging
            import sys
            print(f"\n[DEBUG] Plan JSON that failed validation:", file=sys.stderr)
            print(json.dumps(plan_json if 'plan_json' in locals() else {}, indent=2, ensure_ascii=False), file=sys.stderr)
            raise RuntimeError(f"Failed to create plan: {e}")

    def _fix_acceptance_types(self, plan_json: dict) -> dict:
        """
        Fix common acceptance type errors in the plan JSON.
        OpenAI sometimes generates invalid acceptance types despite clear instructions.
        This method corrects them to valid types.
        """
        VALID_TYPES = {"schema", "file_exists", "text_checks", "numeric_bounds", "llm_review"}

        # Mapping of invalid types to their correct equivalents
        TYPE_CORRECTIONS = {
            "must_contain": "text_checks",
            "min_chars": "text_checks",
            "file_exists_and_correct_structure": "text_checks",
            "content_validation": "text_checks",
            "json_schema": "schema",
            "validate_json": "schema",
            "file_check": "file_exists",
            "exists": "file_exists",
        }

        if "plan" in plan_json and "steps" in plan_json["plan"]:
            for step in plan_json["plan"]["steps"]:
                if "acceptance" in step and "type" in step["acceptance"]:
                    acceptance_type = step["acceptance"]["type"]

                    # If type is invalid, try to correct it
                    if acceptance_type not in VALID_TYPES:
                        corrected_type = TYPE_CORRECTIONS.get(acceptance_type, "text_checks")
                        print(f"[WARNING] Correcting invalid acceptance type '{acceptance_type}' -> '{corrected_type}' in step {step.get('id', 'unknown')}")
                        step["acceptance"]["type"] = corrected_type

        return plan_json

    def _fix_json_control_characters(self, text: str) -> str:
        """
        Fix unescaped control characters in JSON strings.
        This is needed because LLMs sometimes generate JSON with literal newlines
        inside string values, which is invalid JSON.
        """
        import re

        # Strategy: Find string values and escape control characters within them
        # We need to be careful to only escape characters inside quoted strings

        result = []
        in_string = False
        escape_next = False

        for i, char in enumerate(text):
            if escape_next:
                result.append(char)
                escape_next = False
                continue

            if char == '\\':
                result.append(char)
                escape_next = True
                continue

            if char == '"':
                in_string = not in_string
                result.append(char)
                continue

            # If we're inside a string, escape control characters
            if in_string:
                if char == '\n':
                    result.append('\\n')
                elif char == '\r':
                    result.append('\\r')
                elif char == '\t':
                    result.append('\\t')
                elif ord(char) < 32:  # Other control characters
                    result.append(f'\\u{ord(char):04x}')
                else:
                    result.append(char)
            else:
                result.append(char)

        return ''.join(result)

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

# TIPOS DE ACCEPTANCE CRITERIA (CRÍTICO)

SOLO puedes usar estos 5 tipos de acceptance. NO inventes otros:

1. **"schema"**: Valida estructura JSON
   - Requiere: path_ref, schema (con "required" y "properties")
   - Ejemplo: {"type": "schema", "path_ref": "artifact://s1/data.json", "schema": {"required": ["field1"], "properties": {...}}}

2. **"file_exists"**: Verifica que el archivo exista
   - Requiere: path_ref
   - Ejemplo: {"type": "file_exists", "path_ref": "artifact://s1/output.md"}

3. **"text_checks"**: Valida contenido de texto
   - Requiere: path_ref
   - Opcional: min_chars, must_contain (lista de strings que deben aparecer)
   - Ejemplo: {"type": "text_checks", "path_ref": "artifact://s1/article.md", "min_chars": 1000, "must_contain": ["## Introducción", "## Conclusión"]}

4. **"numeric_bounds"**: Valida rangos numéricos
   - Requiere: path_ref, bounds
   - Ejemplo: {"type": "numeric_bounds", "path_ref": "artifact://s1/metrics.json", "bounds": {"accuracy": {"min": 0.8}}}

5. **"llm_review"**: Revisión cualitativa por LLM
   - Requiere: path_ref, rubric (lista de criterios)
   - Ejemplo: {"type": "llm_review", "path_ref": "artifact://s1/essay.md", "rubric": ["Coherencia", "Gramática correcta"]}

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
- Acceptance: type "text_checks" con must_contain ["## Introducción", "## Conclusión"]
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
- Acceptance: type "text_checks" con min_chars (ej: 500 para intro, 1500 para cuerpo)
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

4. **Acceptance criteria** (USA SOLO LOS 5 TIPOS PERMITIDOS):
   - TIPOS VÁLIDOS: "schema", "file_exists", "text_checks", "numeric_bounds", "llm_review"
   - NO uses otros tipos como "must_contain" o "min_chars" como tipo (son CAMPOS de "text_checks")
   - Preferir "schema" o "text_checks" (deterministas)
   - Usar "llm_review" solo cuando necesario
   - Para validar texto con requisitos: usa "text_checks" con campos min_chars y/o must_contain

5. **Dependencias**:
   - Orden lógico: research → outline → writing → editing
   - OutlineAgent depends_on: ["s1"] (research)
   - WriterAgent depends_on: ["s2"] (outline)
   - EditorAgent depends_on: todos los WriterAgent

# IMPORTANTE
- NO generes texto markdown (```json)
- NO agregues explicaciones fuera del JSON
- ASEGÚRATE de que todos los saltos de línea dentro de strings JSON estén escapados como \\n
- Todos los system_prompt deben recordar responder en JSON
- Los agents son autónomos: pueden hacer múltiples tool_calls
- IDs de steps simples: s1, s2, s3, etc.
- El JSON debe ser válido y parseable: usa \\n para nuevas líneas, \\t para tabs, \\" para comillas
- CRÍTICO: En acceptance.type SOLO usa: "schema", "file_exists", "text_checks", "numeric_bounds", "llm_review"
"""
    
    def _build_planner_user_prompt(self, task: TaskRequest) -> str:
        """Build user prompt with task details."""
        prompt_data = {
            "objective": task.objective,
            "constraints": task.constraints,
            "context": task.context,
            "available_tools": task.available_tools,
            "reminder": "IMPORTANTE: En acceptance.type usa SOLO estos valores: 'schema', 'file_exists', 'text_checks', 'numeric_bounds', 'llm_review'"
        }
        return json.dumps(prompt_data, indent=2, ensure_ascii=False)
    
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