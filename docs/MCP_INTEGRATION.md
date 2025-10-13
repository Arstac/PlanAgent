# Integración MCP en PlanAgent

## 🎯 Objetivo

Permitir que PlanAgent use **servidores MCP** como fuente de herramientas, en lugar de solo tools hardcodeadas.

---

## 📋 ¿Qué es MCP?

**Model Context Protocol (MCP)** es un protocolo estándar creado por Anthropic para conectar LLMs con herramientas externas.

### Beneficios:

1. **Ecosistema** - Reutilizar servidores MCP existentes
2. **Modularidad** - Añadir/quitar capabilities dinámicamente
3. **Seguridad** - Control granular de permisos
4. **Mantenibilidad** - Las tools están desacopladas

---

## 🏗️ Arquitectura Propuesta

### ANTES (Actual):
```
┌──────────────────────────────────────┐
│         PlanAgent                    │
│                                      │
│  ┌────────────────────────────────┐ │
│  │   ToolRegistry                 │ │
│  │                                │ │
│  │  - web_search (hardcoded)      │ │
│  │  - web_fetch (hardcoded)       │ │
│  │  - write_artifact (hardcoded)  │ │
│  │  - llm_call (hardcoded)        │ │
│  └────────────────────────────────┘ │
└──────────────────────────────────────┘
```

### DESPUÉS (Con MCP):
```
┌──────────────────────────────────────────────────────┐
│                   PlanAgent                          │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │   ToolRegistry (Enhanced)                      │ │
│  │                                                │ │
│  │  ┌──────────────────────────────────────────┐ │ │
│  │  │  Native Tools (hardcoded)                │ │ │
│  │  │  - write_artifact                        │ │ │
│  │  │  - read_artifact                         │ │ │
│  │  │  - llm_call                              │ │ │
│  │  └──────────────────────────────────────────┘ │ │
│  │                                                │ │
│  │  ┌──────────────────────────────────────────┐ │ │
│  │  │  MCP Client                              │ │ │
│  │  │                                          │ │ │
│  │  │  Connects to:                            │ │ │
│  │  │  ├─ filesystem-server                    │ │ │
│  │  │  ├─ brave-search-server                  │ │ │
│  │  │  ├─ github-server                        │ │ │
│  │  │  ├─ postgres-server                      │ │ │
│  │  │  └─ custom-server                        │ │ │
│  │  │                                          │ │ │
│  │  │  Auto-registers all tools from servers  │ │ │
│  │  └──────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
          │         │         │         │
          ▼         ▼         ▼         ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
    │FS Server│ │Brave Srv│ │GitHub   │ │Custom   │
    │         │ │         │ │Server   │ │Server   │
    └─────────┘ └─────────┘ └─────────┘ └─────────┘
```

---

## 💻 Implementación

### 1. Crear Cliente MCP

**Archivo:** `src/plan_spawn/core/mcp/client.py`

```python
"""
MCP Client para PlanAgent.
Conecta con servidores MCP y registra sus tools automáticamente.
"""
import asyncio
from typing import Dict, List, Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from ..tools.registry import ToolRegistry


class MCPClient:
    """Cliente para conectar con servidores MCP."""

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.sessions: Dict[str, ClientSession] = {}
        self.servers: Dict[str, StdioServerParameters] = {}

    async def connect_server(
        self,
        server_name: str,
        command: str,
        args: List[str] = None,
        env: Dict[str, str] = None
    ):
        """
        Conectar a un servidor MCP.

        Args:
            server_name: Nombre identificador del servidor
            command: Comando para iniciar el servidor (ej: "npx")
            args: Argumentos del comando
            env: Variables de entorno

        Example:
            await mcp_client.connect_server(
                "brave-search",
                "npx",
                ["-y", "@modelcontextprotocol/server-brave-search"],
                {"BRAVE_API_KEY": "BSA..."}
            )
        """
        try:
            # Configurar parámetros del servidor
            server_params = StdioServerParameters(
                command=command,
                args=args or [],
                env=env
            )

            self.servers[server_name] = server_params

            # Conectar al servidor
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Inicializar sesión
                    await session.initialize()

                    # Guardar sesión
                    self.sessions[server_name] = session

                    # Listar y registrar tools
                    tools_list = await session.list_tools()

                    for tool in tools_list.tools:
                        self._register_mcp_tool(
                            server_name=server_name,
                            tool_name=tool.name,
                            tool_description=tool.description,
                            tool_schema=tool.inputSchema,
                            session=session
                        )

                    print(f"✓ Connected to MCP server: {server_name}")
                    print(f"  Registered {len(tools_list.tools)} tools")

        except Exception as e:
            print(f"✗ Failed to connect to {server_name}: {str(e)}")
            raise

    def _register_mcp_tool(
        self,
        server_name: str,
        tool_name: str,
        tool_description: str,
        tool_schema: Dict,
        session: ClientSession
    ):
        """Registrar una tool MCP en el ToolRegistry."""

        # Crear función wrapper que llama al servidor MCP
        async def mcp_tool_wrapper(**kwargs) -> Dict[str, Any]:
            """Wrapper que ejecuta la tool en el servidor MCP."""
            try:
                # Filtrar parámetros inyectados por PlanAgent
                mcp_params = {
                    k: v for k, v in kwargs.items()
                    if k not in ['step_id', 'artifact_store', 'current_step_id']
                }

                # Llamar al servidor MCP
                result = await session.call_tool(tool_name, mcp_params)

                # Convertir resultado MCP a formato PlanAgent
                return {
                    "status": "success",
                    "result": result.content,
                    "mcp_server": server_name
                }

            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "mcp_server": server_name
                }

        # Registrar en ToolRegistry
        self.tool_registry.register_tool(
            name=f"mcp_{server_name}_{tool_name}",
            function=mcp_tool_wrapper,
            description=f"[MCP:{server_name}] {tool_description}",
            parameters=tool_schema
        )

    async def disconnect_all(self):
        """Desconectar todos los servidores MCP."""
        for server_name, session in self.sessions.items():
            try:
                await session.close()
                print(f"✓ Disconnected from {server_name}")
            except Exception as e:
                print(f"✗ Error disconnecting {server_name}: {str(e)}")

    def list_connected_servers(self) -> List[str]:
        """Listar servidores MCP conectados."""
        return list(self.sessions.keys())
```

---

### 2. Configuración de Servidores MCP

**Archivo:** `config/mcp_servers.json`

```json
{
  "servers": [
    {
      "name": "filesystem",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/arnau/Documents/PlanAgent/workspace"],
      "enabled": true,
      "description": "Read/write files in workspace"
    },
    {
      "name": "brave-search",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "${BRAVE_API_KEY}"
      },
      "enabled": true,
      "description": "Web search via Brave Search API"
    },
    {
      "name": "github",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      },
      "enabled": false,
      "description": "GitHub operations (issues, PRs, repos)"
    },
    {
      "name": "postgres",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "POSTGRES_CONNECTION_STRING": "${POSTGRES_URL}"
      },
      "enabled": false,
      "description": "PostgreSQL database operations"
    },
    {
      "name": "puppeteer",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
      "enabled": false,
      "description": "Browser automation"
    }
  ]
}
```

---

### 3. Cargar Servidores MCP al Inicio

**Modificar:** `src/plan_spawn/core/orchestrator.py`

```python
from .mcp.client import MCPClient
import json
from pathlib import Path


class Orchestrator:
    def __init__(self):
        self.console = Console()

        # Initialize components
        self.artifact_store = ArtifactStore(str(settings.ARTIFACTS_PATH))
        self.tool_registry = get_registry()

        # Initialize MCP Client
        self.mcp_client = MCPClient(self.tool_registry)

        # Load and connect to MCP servers
        asyncio.create_task(self._connect_mcp_servers())

        self._register_all_tools()

        self.planner = Planner()
        self.agent_runtime = AgentRuntime(
            tool_registry=self.tool_registry,
            artifact_store=self.artifact_store
        )
        self.executor = Executor(self.agent_runtime)

    async def _connect_mcp_servers(self):
        """Conectar a servidores MCP configurados."""
        config_path = Path(__file__).parent.parent.parent / "config" / "mcp_servers.json"

        if not config_path.exists():
            self.console.print("[yellow]No MCP servers config found[/yellow]")
            return

        with open(config_path) as f:
            config = json.load(f)

        for server in config.get("servers", []):
            if not server.get("enabled", False):
                continue

            try:
                # Expandir variables de entorno
                env = {}
                if "env" in server:
                    for key, value in server["env"].items():
                        if value.startswith("${") and value.endswith("}"):
                            env_var = value[2:-1]
                            env[key] = os.getenv(env_var, "")
                        else:
                            env[key] = value

                # Conectar al servidor
                await self.mcp_client.connect_server(
                    server_name=server["name"],
                    command=server["command"],
                    args=server.get("args", []),
                    env=env if env else None
                )

            except Exception as e:
                self.console.print(
                    f"[red]Failed to connect to MCP server {server['name']}: {str(e)}[/red]"
                )

    def __del__(self):
        """Cleanup: desconectar servidores MCP."""
        if hasattr(self, 'mcp_client'):
            asyncio.create_task(self.mcp_client.disconnect_all())
```

---

### 4. Actualizar Planner para Incluir Tools MCP

**Modificar:** `src/plan_spawn/core/planner.py`

El planner ahora verá automáticamente las tools de MCP:

```python
# En _build_planner_system_prompt():

# Obtener lista de todas las tools disponibles
available_tools = self.tool_registry.list_all()

# Filtrar tools MCP
mcp_tools = [t for t in available_tools if t.startswith("mcp_")]
native_tools = [t for t in available_tools if not t.startswith("mcp_")]

# Añadir al prompt:
system_prompt += f"""

# HERRAMIENTAS DISPONIBLES

## Herramientas Nativas de PlanAgent:
{', '.join(native_tools)}

## Herramientas desde Servidores MCP:
{', '.join(mcp_tools)}

Los agentes pueden usar CUALQUIERA de estas herramientas.
"""
```

---

## 🎯 Casos de Uso con MCP

### 1. Análisis de Repositorio GitHub

**Servidores MCP necesarios:**
- `@modelcontextprotocol/server-github`

**Plan generado:**
```
s1: RepoAnalysisAgent
    → mcp_github_list_repos
    → mcp_github_get_issues
    → mcp_github_get_prs

s2: CodeQualityAgent
    → mcp_filesystem_read_file (de cada archivo .py)
    → Analizar código

s3: ReportAgent
    → Generar reporte de estado del repo
```

### 2. ETL de Base de Datos

**Servidores MCP necesarios:**
- `@modelcontextprotocol/server-postgres`

**Plan generado:**
```
s1: DataExtractAgent
    → mcp_postgres_query
    → Extraer datos de producción

s2: DataTransformAgent
    → Limpiar y transformar datos

s3: DataLoadAgent
    → mcp_postgres_execute
    → Cargar en tabla destino
```

### 3. Web Scraping Avanzado

**Servidores MCP necesarios:**
- `@modelcontextprotocol/server-puppeteer`

**Plan generado:**
```
s1: NavigationAgent
    → mcp_puppeteer_navigate
    → mcp_puppeteer_screenshot

s2: ScrapingAgent
    → mcp_puppeteer_evaluate (JS en página)
    → Extraer datos

s3: DataProcessingAgent
    → Procesar y estructurar datos
```

---

## 📦 Instalación de Servidores MCP

### Prerequisitos:
```bash
# Node.js (para servidores MCP de Anthropic)
brew install node

# Python MCP SDK
pip install mcp
```

### Servidores Recomendados:

```bash
# 1. Filesystem (leer/escribir archivos)
npx -y @modelcontextprotocol/server-filesystem

# 2. Brave Search (búsqueda web)
npx -y @modelcontextprotocol/server-brave-search

# 3. GitHub (operaciones GitHub)
npx -y @modelcontextprotocol/server-github

# 4. PostgreSQL (base de datos)
npx -y @modelcontextprotocol/server-postgres

# 5. Puppeteer (automatización web)
npx -y @modelcontextprotocol/server-puppeteer
```

---

## 🔧 Testing

### Test de Conexión MCP:

```python
# tests/test_mcp_integration.py

import pytest
from plan_spawn.core.mcp.client import MCPClient
from plan_spawn.core.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_mcp_connection():
    """Test conectar a servidor MCP filesystem."""
    registry = ToolRegistry()
    client = MCPClient(registry)

    # Conectar a filesystem server
    await client.connect_server(
        server_name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "."]
    )

    # Verificar que tools fueron registradas
    tools = registry.list_all()
    assert any("mcp_filesystem" in t for t in tools)

    # Cleanup
    await client.disconnect_all()


@pytest.mark.asyncio
async def test_mcp_tool_execution():
    """Test ejecutar una tool MCP."""
    registry = ToolRegistry()
    client = MCPClient(registry)

    await client.connect_server(
        server_name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "."]
    )

    # Ejecutar tool
    read_tool = registry.get("mcp_filesystem_read_file")
    result = await read_tool.function(path="README.md")

    assert result["status"] == "success"
    assert "content" in result["result"]

    await client.disconnect_all()
```

---

## 🎓 Documentación de Referencia

### MCP Protocol:
- **Docs:** https://modelcontextprotocol.io/
- **GitHub:** https://github.com/modelcontextprotocol
- **Servers:** https://github.com/modelcontextprotocol/servers

### Python SDK:
- **PyPI:** https://pypi.org/project/mcp/
- **Quickstart:** https://modelcontextprotocol.io/quickstart

---

## 🚀 Roadmap de Integración MCP

### Fase 1: Setup Básico ✅
- [x] Documentar arquitectura
- [ ] Implementar MCPClient
- [ ] Configuración de servidores
- [ ] Tests básicos

### Fase 2: Servidores Core
- [ ] Integrar filesystem server
- [ ] Integrar brave-search server
- [ ] Integrar github server
- [ ] Testing de cada servidor

### Fase 3: Uso en Agentes
- [ ] Actualizar planner para incluir tools MCP
- [ ] Crear arquetipos que usen tools MCP
- [ ] Documentar patrones de uso

### Fase 4: Servidores Custom
- [ ] Template para crear servidores MCP custom
- [ ] Servidor MCP para artifacts de PlanAgent
- [ ] Servidor MCP para logging/telemetry

---

## 💡 Ventajas de la Integración MCP

1. **Ecosistema** - Acceso a 50+ servidores MCP existentes
2. **Estandarización** - Protocolo oficial de Anthropic
3. **Modularidad** - Añadir/quitar capabilities sin cambiar código
4. **Comunidad** - Compartir y reutilizar servidores
5. **Futuro** - MCP será el estándar para tool-calling

---

## ⚠️ Consideraciones

### Seguridad:
- **Sandbox** - Los servidores MCP pueden acceder al filesystem
- **Permisos** - Configurar accesos granulares
- **API Keys** - Gestionar secrets de forma segura

### Performance:
- **Latencia** - Comunicación inter-proceso añade latency
- **Conexiones** - Gestionar ciclo de vida de conexiones
- **Errores** - Manejar caídas de servidores MCP

### Compatibilidad:
- **Versiones** - MCP está en desarrollo activo
- **Dependencias** - Node.js requerido para servidores de Anthropic
- **Testing** - Necesita tests robustos

---

**¿Listo para implementar?** 🚀

Siguiente paso: Crear el `MCPClient` y probar con el servidor filesystem.
