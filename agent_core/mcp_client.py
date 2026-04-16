"""
MCP (Model Context Protocol) Integration
Implements client support for the "USB-C for AI" standard
"""

import json
import asyncio
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from pathlib import Path
import subprocess
import os

@dataclass
class MCPTool:
    """Represents an MCP tool"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str


class MCPClient:
    """
    MCP Client for connecting to MCP servers.
    Supports both stdio and HTTP transports.
    """
    
    def __init__(self, 
                 server_command: Optional[str] = None,
                 server_url: Optional[str] = None,
                 env_vars: Optional[Dict[str, str]] = None):
        """
        Initialize MCP client.
        
        Args:
            server_command: Command to start MCP server (stdio mode)
            server_url: URL for HTTP SSE transport
            env_vars: Environment variables for server
        """
        self.server_command = server_command
        self.server_url = server_url
        self.env_vars = env_vars or {}
        
        self.process: Optional[subprocess.Popen] = None
        self.tools: List[MCPTool] = []
        self.capabilities: Dict[str, Any] = {}
        self._initialized = False
    
    async def connect_stdio(self) -> bool:
        """
        Connect to MCP server via stdio transport.
        """
        if not self.server_command:
            raise ValueError("server_command required for stdio transport")
        
        try:
            # Start server process
            env = {**os.environ, **self.env_vars}
            self.process = subprocess.Popen(
                self.server_command.split(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            # Send initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "openclaw-agent", "version": "0.1.0"}
                }
            }
            
            response = await self._send_request(init_request)
            if response:
                self.capabilities = response.get('result', {}).get('capabilities', {})
                self._initialized = True
                
                # Load available tools
                await self._load_tools()
                return True
            
            return False
            
        except Exception as e:
            print(f"MCP connection failed: {e}")
            return False
    
    async def _send_request(self, request: Dict) -> Optional[Dict]:
        """Send JSON-RPC request via stdio"""
        if not self.process or self.process.poll() is not None:
            return None
        
        try:
            # Send request
            request_line = json.dumps(request) + '\n'
            self.process.stdin.write(request_line)
            self.process.stdin.flush()
            
            # Read response (with timeout)
            response_line = await asyncio.wait_for(
                asyncio.to_thread(self.process.stdout.readline),
                timeout=30.0
            )
            
            return json.loads(response_line)
            
        except asyncio.TimeoutError:
            print("MCP request timeout")
            return None
        except Exception as e:
            print(f"MCP request error: {e}")
            return None
    
    async def _load_tools(self):
        """Load available tools from server"""
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        
        response = await self._send_request(request)
        if response and 'result' in response:
            tools_data = response['result'].get('tools', [])
            self.tools = [
                MCPTool(
                    name=t['name'],
                    description=t.get('description', ''),
                    input_schema=t.get('inputSchema', {}),
                    server_name=self.server_command or self.server_url
                )
                for t in tools_data
            ]
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool.
        
        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        if not self._initialized:
            raise RuntimeError("MCP client not initialized")
        
        request = {
            "jsonrpc": "2.0",
            "id": hash(f"{tool_name}_{asyncio.get_event_loop().time()}"),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        response = await self._send_request(request)
        
        if not response:
            return {"error": "No response from MCP server"}
        
        if 'error' in response:
            return {"error": response['error']}
        
        return response.get('result', {})
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Get tool definitions in format suitable for LLM function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema
                }
            }
            for tool in self.tools
        ]
    
    async def disconnect(self):
        """Clean disconnect from server"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            self.process = None
        self._initialized = False


class MCPToolRegistry:
    """
    Registry for multiple MCP servers.
    Aggregates tools from multiple sources.
    """
    
    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}
        self._all_tools: Dict[str, MCPTool] = {}
    
    async def add_server(self, name: str, command: str, 
                        env_vars: Optional[Dict[str, str]] = None) -> bool:
        """
        Add and connect to an MCP server.
        
        Args:
            name: Server identifier
            command: Command to start server
            env_vars: Optional environment variables
            
        Returns:
            True if connected successfully
        """
        client = MCPClient(server_command=command, env_vars=env_vars)
        
        if await client.connect_stdio():
            self.clients[name] = client
            
            # Index tools
            for tool in client.tools:
                tool_key = f"{name}__{tool.name}"
                self._all_tools[tool_key] = tool
            
            print(f"✓ MCP server '{name}' connected with {len(client.tools)} tools")
            return True
        else:
            print(f"✗ Failed to connect MCP server '{name}'")
            return False
    
    async def call_tool(self, tool_key: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool by its registry key.
        
        Args:
            tool_key: Format "server_name__tool_name"
            arguments: Tool arguments
        """
        if "__" not in tool_key:
            return {"error": "Invalid tool key format"}
        
        server_name, tool_name = tool_key.split("__", 1)
        
        if server_name not in self.clients:
            return {"error": f"Server '{server_name}' not connected"}
        
        return await self.clients[server_name].call_tool(tool_name, arguments)
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all tools from all servers"""
        tools = []
        for tool_key, tool in self._all_tools.items():
            tools.append({
                "type": "function",
                "function": {
                    "name": tool_key,
                    "description": f"[{tool.server_name}] {tool.description}",
                    "parameters": tool.input_schema
                }
            })
        return tools
    
    def list_servers(self) -> Dict[str, int]:
        """List connected servers and tool counts"""
        return {name: len(client.tools) for name, client in self.clients.items()}
    
    async def disconnect_all(self):
        """Disconnect from all servers"""
        for client in self.clients.values():
            await client.disconnect()
        self.clients.clear()
        self._all_tools.clear()


# Pre-configured MCP servers for common use cases

COMMON_MCP_SERVERS = {
    "filesystem": {
        "command": "npx -y @modelcontextprotocol/server-filesystem /tmp/mcp_files",
        "description": "File system operations"
    },
    "github": {
        "command": "npx -y @modelcontextprotocol/server-github",
        "env": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
        "description": "GitHub API access"
    },
    "postgres": {
        "command": "npx -y @modelcontextprotocol/server-postgres postgresql://localhost/db",
        "description": "PostgreSQL database access"
    },
    "fetch": {
        "command": "uvx mcp-server-fetch",
        "description": "Web fetching"
    }
}


class MCPIntegrationHelper:
    """
    Helper class for common MCP integration patterns.
    """
    
    @staticmethod
    def setup_common_servers(registry: MCPToolRegistry, 
                            config: Dict[str, Any]) -> List[str]:
        """
        Setup common MCP servers from config.
        
        Args:
            registry: MCPToolRegistry instance
            config: Dict with server configurations
            
        Returns:
            List of successfully connected server names
        """
        connected = []
        
        for server_name, server_config in config.items():
            if server_name in COMMON_MCP_SERVERS:
                common = COMMON_MCP_SERVERS[server_name]
                command = server_config.get('command', common['command'])
                env_vars = {}
                
                # Add required env vars
                for env_key in common.get('env', []):
                    if env_key in os.environ:
                        env_vars[env_key] = os.environ[env_key]
                    elif env_key in server_config:
                        env_vars[env_key] = server_config[env_key]
                
                # This would need to be async in real usage
                # For now, just return the configuration
                connected.append({
                    'name': server_name,
                    'command': command,
                    'env': env_vars
                })
        
        return connected


# Global registry
_global_mcp_registry: Optional[MCPToolRegistry] = None

def get_mcp_registry() -> MCPToolRegistry:
    """Get global MCP registry"""
    global _global_mcp_registry
    if _global_mcp_registry is None:
        _global_mcp_registry = MCPToolRegistry()
    return _global_mcp_registry
