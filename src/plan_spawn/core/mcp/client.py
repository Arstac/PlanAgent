"""
MCP Client para PlanAgent.
Conecta con servidores MCP y registra sus tools automáticamente.
Soporta tanto servidores stdio (procesos locales) como HTTP/SSE (remotos).
"""
import asyncio
import os
from typing import Dict, List, Any, Optional, Literal
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
from rich.console import Console


class MCPClient:
    """Cliente para conectar con servidores MCP."""

    def __init__(self, tool_registry=None):
        """
        Inicializar cliente MCP.

        Args:
            tool_registry: Registro de herramientas de PlanAgent
        """
        self.tool_registry = tool_registry
        self.sessions: Dict[str, ClientSession] = {}
        self.servers: Dict[str, StdioServerParameters] = {}
        self._connection_tasks: Dict[str, asyncio.Task] = {}
        self.console = Console()

    async def connect_stdio_server(
        self,
        server_name: str,
        command: str,
        args: List[str] = None,
        env: Dict[str, str] = None
    ):
        """
        Conectar a un servidor MCP via stdio (proceso local).

        Args:
            server_name: Nombre identificador del servidor
            command: Comando para iniciar el servidor (ej: "npx")
            args: Argumentos del comando
            env: Variables de entorno

        Example:
            await mcp_client.connect_stdio_server(
                "brave-search",
                "npx",
                ["-y", "@modelcontextprotocol/server-brave-search"],
                {"BRAVE_API_KEY": "BSA..."}
            )
        """
        # Configurar parámetros del servidor
        server_params = StdioServerParameters(
            command=command,
            args=args or [],
            env=env
        )

        self.servers[server_name] = server_params
        self.console.print(f"[dim]Connecting to MCP server: {server_name}...[/dim]")

        # Crear tarea que mantiene la conexión
        connection_ready = asyncio.Event()
        connection_error = None

        async def maintain_connection():
            nonlocal connection_error
            try:
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
                                tool_description=tool.description or "",
                                tool_schema=tool.inputSchema,
                                session=session
                            )

                        self.console.print(
                            f"[green]✓[/green] Connected to MCP server: [cyan]{server_name}[/cyan]"
                        )
                        self.console.print(
                            f"  [dim]Registered {len(tools_list.tools)} tools[/dim]"
                        )

                        # Señalar que la conexión está lista
                        connection_ready.set()

                        # Mantener la conexión viva
                        await asyncio.Event().wait()  # Espera indefinida

            except Exception as e:
                connection_error = e
                connection_ready.set()
                import traceback
                self.console.print(
                    f"[red]✗ Failed to connect to {server_name}: {str(e)}[/red]"
                )
                self.console.print(f"[dim]{traceback.format_exc()}[/dim]")

        # Iniciar tarea de conexión
        task = asyncio.create_task(maintain_connection())
        self._connection_tasks[server_name] = task

        # Esperar a que la conexión esté lista
        await connection_ready.wait()

        if connection_error:
            return False

        return True

    async def connect_http_server(
        self,
        server_name: str,
        url: str,
        headers: Dict[str, str] = None,
        timeout: float = 5.0,
        sse_read_timeout: float = 300.0
    ):
        """
        Conectar a un servidor MCP via HTTP Streamable (servidor remoto).

        Args:
            server_name: Nombre identificador del servidor
            url: URL del endpoint HTTP (ej: "https://api.example.com/mcp")
            headers: Headers HTTP (ej: {"Authorization": "Bearer token"})
            timeout: Timeout para operaciones HTTP regulares (segundos)
            sse_read_timeout: Timeout para operaciones de lectura SSE (segundos)

        Example:
            await mcp_client.connect_http_server(
                "github-copilot",
                "https://api.githubcopilot.com/mcp",
                headers={"Authorization": "Bearer ghp_..."}
            )
        """
        self.console.print(f"[dim]Connecting to HTTP MCP server: {server_name}...[/dim]")

        # Crear tarea que mantiene la conexión
        connection_ready = asyncio.Event()
        connection_error = None

        async def maintain_http_connection():
            nonlocal connection_error
            try:
                async with streamablehttp_client(
                    url=url,
                    headers=headers,
                    timeout=timeout,
                    sse_read_timeout=sse_read_timeout
                ) as (read, write, get_session_id):
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
                                tool_description=tool.description or "",
                                tool_schema=tool.inputSchema,
                                session=session
                            )

                        self.console.print(
                            f"[green]✓[/green] Connected to HTTP MCP server: [cyan]{server_name}[/cyan]"
                        )
                        self.console.print(
                            f"  [dim]Registered {len(tools_list.tools)} tools[/dim]"
                        )

                        # Señalar que la conexión está lista
                        connection_ready.set()

                        # Mantener la conexión viva
                        await asyncio.Event().wait()  # Espera indefinida

            except Exception as e:
                connection_error = e
                connection_ready.set()
                import traceback
                self.console.print(
                    f"[red]✗ Failed to connect to HTTP server {server_name}: {str(e)}[/red]"
                )
                self.console.print(f"[dim]{traceback.format_exc()}[/dim]")

        # Iniciar tarea de conexión
        task = asyncio.create_task(maintain_http_connection())
        self._connection_tasks[server_name] = task

        # Esperar a que la conexión esté lista
        await connection_ready.wait()

        if connection_error:
            return False

        return True

    def _register_mcp_tool(
        self,
        server_name: str,
        tool_name: str,
        tool_description: str,
        tool_schema: Dict,
        session: ClientSession
    ):
        """Registrar una tool MCP en el ToolRegistry."""

        if not self.tool_registry:
            return

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
                if hasattr(result, 'content') and result.content:
                    # MCP devuelve una lista de content blocks
                    content_str = ""
                    for content_block in result.content:
                        if hasattr(content_block, 'text'):
                            content_str += content_block.text
                        elif hasattr(content_block, 'data'):
                            content_str += str(content_block.data)

                    return {
                        "status": "success",
                        "result": content_str,
                        "mcp_server": server_name,
                        "mcp_tool": tool_name
                    }
                else:
                    return {
                        "status": "success",
                        "result": str(result),
                        "mcp_server": server_name,
                        "mcp_tool": tool_name
                    }

            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "mcp_server": server_name,
                    "mcp_tool": tool_name
                }

        # Convertir schema MCP a formato Anthropic
        anthropic_schema = self._convert_schema_to_anthropic(tool_schema)

        # Nombre de la tool con prefijo
        full_tool_name = f"mcp_{server_name}_{tool_name}"

        # Registrar en ToolRegistry
        if hasattr(self.tool_registry, '_tools'):
            from ..tools.registry import Tool
            self.tool_registry._tools[full_tool_name] = Tool(
                name=full_tool_name,
                description=f"[MCP:{server_name}] {tool_description}",
                parameters=anthropic_schema,
                function=mcp_tool_wrapper
            )

    def _convert_schema_to_anthropic(self, mcp_schema: Dict) -> Dict:
        """
        Convertir schema JSON de MCP a formato Anthropic.

        MCP usa JSON Schema estándar.
        Anthropic también, así que mayormente es pass-through.
        """
        if not mcp_schema:
            return {
                "type": "object",
                "properties": {},
                "required": []
            }

        return mcp_schema

    async def disconnect_server(self, server_name: str):
        """Desconectar un servidor MCP específico."""
        if server_name in self._connection_tasks:
            try:
                # Cancelar la tarea de conexión (esto cerrará los context managers)
                task = self._connection_tasks[server_name]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

                # Limpiar referencias
                del self._connection_tasks[server_name]
                if server_name in self.sessions:
                    del self.sessions[server_name]

                self.console.print(f"[green]✓[/green] Disconnected from {server_name}")
            except Exception as e:
                self.console.print(f"[red]✗ Error disconnecting {server_name}: {str(e)}[/red]")

    async def disconnect_all(self):
        """Desconectar todos los servidores MCP."""
        server_names = list(self.sessions.keys())
        for server_name in server_names:
            await self.disconnect_server(server_name)

    def list_connected_servers(self) -> List[str]:
        """Listar servidores MCP conectados."""
        return list(self.sessions.keys())

    def get_server_tools(self, server_name: str) -> List[str]:
        """Obtener lista de tools de un servidor específico."""
        if not self.tool_registry or not hasattr(self.tool_registry, '_tools'):
            return []

        prefix = f"mcp_{server_name}_"
        return [
            name for name in self.tool_registry._tools.keys()
            if name.startswith(prefix)
        ]

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup all connections."""
        await self.disconnect_all()
        return False
