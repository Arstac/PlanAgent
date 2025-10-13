"""
Script de prueba para verificar integración MCP.
"""
import asyncio
import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from plan_spawn.core.orchestrator import Orchestrator


async def test_mcp():
    """Test básico de MCP integration."""
    print("🧪 Testing MCP Integration\n")

    # Crear orchestrator (esto debería inicializar MCP)
    orchestrator = Orchestrator()

    try:
        # Forzar conexión a servidores MCP
        print("Attempting to connect to MCP servers...\n")
        await orchestrator._connect_mcp_servers()

        # Listar servidores conectados
        connected = orchestrator.mcp_client.list_connected_servers()
        print(f"\n📡 Connected MCP servers: {connected}")

        # Listar todas las tools
        all_tools = orchestrator.tool_registry.list_all()
        print(f"\n🔧 Total tools available: {len(all_tools)}")

        # Filtrar tools MCP
        tool_names = [t.name for t in all_tools]
        mcp_tools = [name for name in tool_names if name.startswith("mcp_")]
        print(f"   MCP tools: {len(mcp_tools)}")
        print(f"   Native tools: {len(all_tools) - len(mcp_tools)}")

        if mcp_tools:
            print(f"\n📋 MCP Tools registered:")
            for tool in sorted(mcp_tools):
                print(f"   - {tool}")

        print("\n✅ MCP Integration test completed!")

    finally:
        # Cleanup: desconectar todos los servidores MCP
        print("\n🧹 Cleaning up MCP connections...")
        await orchestrator.mcp_client.disconnect_all()


if __name__ == "__main__":
    asyncio.run(test_mcp())
