# Migración de Claude (Anthropic) a OpenAI

Este documento describe los cambios realizados para migrar PlanAgent de la API de Claude (Anthropic) a la API de OpenAI.

## Resumen de Cambios

Se ha migrado completamente el sistema de agentes de Claude API a OpenAI API. Todos los archivos principales han sido actualizados.

---

## 📋 Archivos Modificados

### 1. **[settings.py](src/plan_spawn/config/settings.py)**
- `ANTHROPIC_API_KEY` → `OPENAI_API_KEY`
- `CLAUDE_MODEL` → `OPENAI_MODEL` (default: `gpt-4o`)
- Validación actualizada para requerir `OPENAI_API_KEY`

### 2. **[planner.py](src/plan_spawn/core/planner.py)**
- Import: `from anthropic import Anthropic` → `from openai import OpenAI`
- Cliente: `Anthropic(api_key=...)` → `OpenAI(api_key=...)`
- Llamada API: `client.messages.create()` → `client.chat.completions.create()`
- System prompt: Parámetro `system` movido a array `messages` con `role="system"`
- Respuesta: `response.content[0].text` → `response.choices[0].message.content`

### 3. **[agent_runtime.py](src/plan_spawn/core/agent_runtime.py)**
- Import: `from anthropic import Anthropic` → `from openai import OpenAI`
- Cliente: `Anthropic(api_key=...)` → `OpenAI(api_key=...)`
- Mensajes: System prompt incluido en array `messages` con `role="system"`
- Tool calling:
  - Estructura completamente reescrita para API de OpenAI
  - `response.stop_reason` → `response.choices[0].finish_reason`
  - Stop reasons: `"end_turn"` → `"stop"`, `"tool_use"` → `"tool_calls"`, `"max_tokens"` → `"length"`
  - Tool results: `{"type": "tool_result", ...}` → `{"role": "tool", "tool_call_id": ..., "content": ...}`
- Parsing respuesta: `response.content[0].text` → `response.choices[0].message.content`

### 4. **[llm_tools.py](src/plan_spawn/core/tools/llm_tools.py)**
- Import: `from anthropic import Anthropic` → `from openai import OpenAI`
- Tres funciones actualizadas:
  - `llm_call()`: Cliente y llamada API actualizados
  - `quality_check()`: Cliente y llamada API actualizados
  - `fact_verify()`: Cliente y llamada API actualizados
- Respuestas: `response.content[0].text` → `response.choices[0].message.content`
- Usage tokens: `input_tokens`/`output_tokens` → `prompt_tokens`/`completion_tokens`

### 5. **[requirements.txt](requirements.txt)**
- `anthropic>=0.34.0` → `openai>=1.0.0`

### 6. **Nuevos archivos**
- `.env.example`: Plantilla con variables de entorno para OpenAI
- `MIGRATION_TO_OPENAI.md`: Este documento

---

## 🔧 Instrucciones de Instalación

### Paso 1: Actualizar dependencias

Desinstala Anthropic e instala OpenAI:

```bash
pip uninstall anthropic -y
pip install openai>=1.0.0
```

O reinstala todas las dependencias:

```bash
pip install -r requirements.txt
```

### Paso 2: Configurar API Key

Edita tu archivo `.env` y reemplaza la API key de Anthropic con tu API key de OpenAI:

```env
# ANTES (Anthropic)
ANTHROPIC_API_KEY=sk-ant-api03-...

# DESPUÉS (OpenAI)
OPENAI_API_KEY=sk-proj-...
```

Puedes obtener tu API key de OpenAI en: https://platform.openai.com/api-keys

### Paso 3: Configurar el modelo (opcional)

El modelo por defecto es `gpt-4o`. Si quieres usar otro modelo, configúralo en `.env`:

```env
OPENAI_MODEL=gpt-4o        # Recomendado (más rápido y económico)
# OPENAI_MODEL=gpt-4-turbo  # Alternativa (más contexto)
# OPENAI_MODEL=gpt-4        # Modelo base (más lento)
```

### Paso 4: Verificar instalación

Ejecuta tu aplicación para verificar que todo funciona:

```bash
python -m plan_spawn.main "tu tarea aquí"
```

---

## 🔄 Diferencias entre APIs

| Aspecto | Claude (Anthropic) | OpenAI | Impacto |
|---------|-------------------|--------|---------|
| **Llamada básica** | `client.messages.create()` | `client.chat.completions.create()` | Cambio en código |
| **System prompt** | Parámetro `system` separado | Incluido en `messages` con `role="system"` | Cambio estructural |
| **Tool calling** | `stop_reason="tool_use"` | `finish_reason="tool_calls"` | Cambio en lógica |
| **Tool results** | `type="tool_result"` con `tool_use_id` | `role="tool"` con `tool_call_id` | Cambio en formato |
| **Respuesta texto** | `response.content[0].text` | `response.choices[0].message.content` | Cambio en parsing |
| **Contexto** | 200K tokens (Sonnet 4.5) | 128K tokens (GPT-4o) | ⚠️ Menor capacidad |
| **Costo** | Más caro por token | Más económico | ✅ Beneficio |

---

## ⚠️ Limitaciones Conocidas

1. **Menor capacidad de contexto**: GPT-4o/4-turbo tiene 128K tokens vs 200K de Claude Sonnet 4.5
   - **Solución**: Si necesitas más contexto, considera dividir tareas en subtareas más pequeñas

2. **Cambios en razonamiento**: Los modelos pueden razonar de manera diferente
   - **Solución**: Prueba los system prompts y ajústalos si es necesario

3. **Tool calling**: OpenAI requiere formato específico para tool calls
   - **Solución**: Ya implementado en la migración

---

## 🧪 Testing

Después de la migración, prueba los siguientes escenarios:

1. **Planificación básica**: Verifica que el planner genera planes correctos
2. **Tool calling**: Verifica que los agentes pueden usar herramientas (web_search, write_artifact, etc.)
3. **Ejecución multi-step**: Verifica que los steps se ejecutan en orden con dependencias
4. **Manejo de errores**: Verifica que los errores se manejan correctamente

---

## 📊 Comparación de Modelos OpenAI

| Modelo | Contexto | Velocidad | Costo | Uso Recomendado |
|--------|----------|-----------|-------|-----------------|
| **gpt-4o** | 128K | Rápido | Medio | ✅ Recomendado para producción |
| **gpt-4-turbo** | 128K | Medio | Alto | Para tareas complejas |
| **gpt-4** | 8K | Lento | Alto | No recomendado |
| **gpt-3.5-turbo** | 16K | Muy rápido | Bajo | Para desarrollo/testing |

---

## 🐛 Troubleshooting

### Error: "OPENAI_API_KEY is required"
- Verifica que el archivo `.env` existe y contiene `OPENAI_API_KEY=...`
- Verifica que la key empieza con `sk-proj-` o `sk-`

### Error: "Invalid API key"
- Verifica que copiaste la key completa sin espacios
- Verifica que la key es válida en https://platform.openai.com/api-keys

### Error: "Rate limit exceeded"
- OpenAI tiene límites de tasa (RPM/TPM)
- Espera unos segundos o considera actualizar tu plan de OpenAI

### Los agentes no funcionan como antes
- Los modelos de OpenAI razonan diferente a Claude
- Considera ajustar los system prompts en [planner.py](src/plan_spawn/core/planner.py)

---

## 💡 Ventajas de la Migración

✅ **Costos reducidos**: OpenAI generalmente es más económico
✅ **Amplio soporte**: API muy utilizada con mucha documentación
✅ **Modelos rápidos**: gpt-4o es muy rápido
✅ **Flexibilidad**: Varios modelos para elegir según necesidad

---

## 📚 Referencias

- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [OpenAI Python Library](https://github.com/openai/openai-python)
- [OpenAI Pricing](https://openai.com/pricing)

---

## 🔙 Rollback (Volver a Claude)

Si necesitas volver a Claude, los cambios están en Git. Simplemente:

```bash
git revert <commit-hash>
pip install anthropic>=0.34.0
# Restaurar .env con ANTHROPIC_API_KEY
```

---

**Migración completada exitosamente** ✅
*Fecha: 2025-01-13*
