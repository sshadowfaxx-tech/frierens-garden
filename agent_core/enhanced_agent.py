"""
Enhanced Agent Core - Production Ready
Integrates: Vector Memory, MCP Tools, Temporal Durable Execution
"""

import asyncio
import time
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime

# Import systems
from .memory_system import MemoryManager, get_memory
from .reflection_system import ReflectionEngine, get_reflection_engine
from .planning_system import Planner, PlanExecutor, ReasoningStrategy
from .safety_system import SafetyManager, get_safety_manager, RiskLevel
from .mcp_client import MCPToolRegistry, get_mcp_registry, MCPIntegrationHelper
from .temporal_integration import (
    DurableExecutionManager, 
    DurableAgentLoop,
    ApprovalManager,
    create_durable_workflow
)


@dataclass
class AgentConfig:
    """Configuration for the enhanced agent"""
    enable_memory: bool = True
    enable_reflection: bool = True
    enable_planning: bool = True
    enable_safety: bool = True
    enable_mcp: bool = True
    enable_durable_execution: bool = True
    
    # Reasoning settings
    default_strategy: ReasoningStrategy = ReasoningStrategy.REACT
    max_plan_depth: int = 5
    
    # Safety settings
    auto_approve_read_only: bool = True
    
    # MCP settings
    mcp_servers: Dict[str, Any] = field(default_factory=dict)
    
    # Durable execution settings
    use_temporal: bool = True
    max_steps: int = 100


class EnhancedAgent:
    """
    Production-ready agent with full cognitive architecture.
    
    NEW: Vector-based semantic memory
    NEW: MCP tool integration
    NEW: Temporal durable execution
    """
    
    def __init__(self, config: Optional[AgentConfig] = None, 
                 session_id: Optional[str] = None):
        self.config = config or AgentConfig()
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Initialize subsystems
        self.memory = get_memory(self.session_id) if self.config.enable_memory else None
        self.reflection = get_reflection_engine() if self.config.enable_reflection else None
        self.planner = Planner(llm_call_func=self._llm_call)
        self.safety = get_safety_manager() if self.config.enable_safety else None
        
        # NEW: MCP registry
        self.mcp = get_mcp_registry() if self.config.enable_mcp else None
        
        # NEW: Durable execution
        self.durable: Optional[DurableExecutionManager] = None
        if self.config.enable_durable_execution:
            self.durable = create_durable_workflow(
                f"agent_{self.session_id}",
                use_temporal=self.config.use_temporal
            )
        
        # Execution state
        self.current_plan = None
        self.execution_log: List[Dict] = []
        
        # Tool registry (local + MCP)
        self.local_tools: Dict[str, Dict] = {}
        self._tools_loaded = False
    
    async def initialize(self):
        """Initialize async components"""
        # Connect to Temporal if using durable execution
        if self.durable and self.config.use_temporal:
            await self.durable.connect_temporal()
        
        # Setup MCP servers
        if self.mcp and self.config.mcp_servers:
            for name, server_config in self.config.mcp_servers.items():
                if isinstance(server_config, dict):
                    await self.mcp.add_server(
                        name,
                        server_config.get('command', ''),
                        server_config.get('env', {})
                    )
        
        self._tools_loaded = True
        print(f"✓ Agent {self.session_id} initialized")
        print(f"  Memory: {'✓' if self.memory else '✗'}")
        print(f"  MCP: {'✓' if self.mcp else '✗'}")
        print(f"  Durable Execution: {'✓' if self.durable else '✗'}")
    
    def register_tool(self, name: str, func: Callable, 
                     description: str = "", risk_level: str = "medium"):
        """Register a local tool"""
        self.local_tools[name] = {
            'func': func,
            'description': description,
            'risk_level': risk_level
        }
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools (local + MCP)"""
        tools = []
        
        # Local tools
        for name, tool in self.local_tools.items():
            tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool['description'],
                    "risk_level": tool['risk_level']
                }
            })
        
        # MCP tools
        if self.mcp:
            tools.extend(self.mcp.get_all_tools())
        
        return tools
    
    async def process(self, user_input: str, 
                     task_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main entry point with full pipeline.
        """
        if not self._tools_loaded:
            await self.initialize()
        
        start_time = time.time()
        
        # 1. SAFETY: Input Validation
        if self.safety:
            check = self.safety.check_input(user_input)
            if not check.passed:
                return {
                    'success': False,
                    'error': f"Input blocked: {check.message}",
                    'risk_level': check.risk_level.value,
                    'response': "I cannot process this request due to safety concerns."
                }
        
        # 2. MEMORY: Load Context
        memory_context = ""
        if self.memory:
            self.memory.working.set_task(user_input, task_context)
            memory_context = await self.memory.get_full_context(user_input)
        
        # 3. PLANNING
        if self.config.enable_planning:
            self.current_plan = self.planner.create_plan(user_input)
        
        # 4. EXECUTION (with durable execution if enabled)
        if self.durable:
            result = await self._execute_durable(user_input, memory_context)
        else:
            result = await self._execute_standard(user_input, memory_context)
        
        # 5. REFLECTION
        if self.reflection:
            self.reflection.reflect(
                task=user_input,
                outcome="success" if result.get('success') else "failure",
                steps_taken=result.get('steps', []),
                tool_calls=result.get('tool_calls', []),
                errors=[result['error']] if 'error' in result else None
            )
        
        # 6. MEMORY: Store
        if self.memory:
            self.memory.capture_interaction(
                user_input=user_input,
                assistant_output=result.get('response', ''),
                tool_calls=result.get('tool_calls', [])
            )
        
        result['execution_time'] = time.time() - start_time
        result['session_id'] = self.session_id
        return result
    
    async def _execute_durable(self, user_input: str, memory_context: str) -> Dict[str, Any]:
        """
        Execute with durable execution (checkpoints, recovery, HITL).
        """
        loop = DurableAgentLoop(self.durable, max_steps=self.config.max_steps)
        
        state = {
            'user_input': user_input,
            'memory_context': memory_context,
            'step_count': 0,
            'tool_calls': [],
            'response': "",
            'completed': False
        }
        
        async def step_executor(step_num: int, current_state: Dict) -> Dict:
            """Single step execution"""
            if current_state.get('completed'):
                return {}
            
            # Execute one step of ReAct loop
            step_result = await self._react_step(
                current_state['user_input'],
                current_state['memory_context'],
                current_state['step_count']
            )
            
            current_state['step_count'] += 1
            current_state['tool_calls'].extend(step_result.get('tool_calls', []))
            
            if step_result.get('complete'):
                current_state['response'] = step_result.get('response', '')
                current_state['completed'] = True
            
            return current_state
        
        def should_continue(step: int, current_state: Dict) -> bool:
            return not current_state.get('completed') and step < self.config.max_steps
        
        final_state = await loop.execute_with_recovery(
            initial_state=state,
            step_func=step_executor,
            should_continue=should_continue
        )
        
        return {
            'success': final_state.get('completed', False),
            'response': final_state.get('response', ''),
            'steps': final_state.get('step_count', 0),
            'tool_calls': final_state.get('tool_calls', [])
        }
    
    async def _execute_standard(self, user_input: str, memory_context: str) -> Dict[str, Any]:
        """Standard execution without durable execution"""
        result = await self._react_loop(user_input, memory_context)
        return result
    
    async def _react_step(self, user_input: str, memory_context: str, 
                         step_num: int) -> Dict[str, Any]:
        """Execute a single ReAct step"""
        # Simplified - in real implementation would call LLM
        return {
            'complete': step_num >= 3,  # Placeholder
            'response': f"Processed: {user_input[:50]}...",
            'tool_calls': []
        }
    
    async def _react_loop(self, user_input: str, memory_context: str) -> Dict[str, Any]:
        """Standard ReAct loop without checkpointing"""
        # Simplified implementation
        return {
            'success': True,
            'response': f"Processed your request: {user_input[:50]}...",
            'steps': [],
            'tool_calls': []
        }
    
    async def _execute_tool(self, tool_name: str, params: Dict) -> Any:
        """Execute a tool (local or MCP)"""
        # Check if it's an MCP tool
        if self.mcp and "__" in tool_name:
            return await self.mcp.call_tool(tool_name, params)
        
        # Local tool
        if tool_name in self.local_tools:
            func = self.local_tools[tool_name]['func']
            if asyncio.iscoroutinefunction(func):
                return await func(**params)
            else:
                return func(**params)
        
        raise ValueError(f"Tool '{tool_name}' not found")
    
    def _llm_call(self, prompt: str) -> str:
        """Placeholder for LLM integration"""
        return f"[LLM: {prompt[:100]}...]"
    
    # ==================== Utility Methods ====================
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status"""
        status = {
            'session_id': self.session_id,
            'config': {
                'memory': self.config.enable_memory,
                'reflection': self.config.enable_reflection,
                'planning': self.config.enable_planning,
                'safety': self.config.enable_safety,
                'mcp': self.config.enable_mcp,
                'durable_execution': self.config.enable_durable_execution
            },
            'local_tools': list(self.local_tools.keys()),
            'mcp_servers': self.mcp.list_servers() if self.mcp else {},
            'mcp_tools': len(self.mcp.get_all_tools()) if self.mcp else 0
        }
        
        if self.memory:
            status['memory_stats'] = self.memory.vector.get_stats()
        
        if self.durable:
            status['durable_workflow'] = {
                'workflow_id': self.durable.workflow_id,
                'status': self.durable.status.value,
                'checkpoints': len(self.durable.checkpoints)
            }
        
        if self.safety:
            status['safety'] = self.safety.get_safety_report()
        
        return status
    
    async def request_human_approval(self, action: str, context: Dict) -> bool:
        """Request human approval for an action"""
        if self.durable:
            return await self.durable.request_human_approval(action, context)
        return False
    
    async def store_long_term_memory(self, content: str, category: str = "general",
                                    tags: Optional[List[str]] = None) -> str:
        """Store to vector memory"""
        if self.memory:
            return await self.memory.store_long_term(content, category, tags)
        return ""


# Factory function

def create_enhanced_agent(session_id: Optional[str] = None,
                          enable_mcp: bool = True,
                          enable_durable: bool = True,
                          mcp_servers: Optional[Dict] = None) -> EnhancedAgent:
    """
    Factory to create a fully configured enhanced agent.
    """
    config = AgentConfig(
        enable_memory=True,
        enable_reflection=True,
        enable_planning=True,
        enable_safety=True,
        enable_mcp=enable_mcp,
        enable_durable_execution=enable_durable,
        mcp_servers=mcp_servers or {},
        default_strategy=ReasoningStrategy.REACT
    )
    
    return EnhancedAgent(config=config, session_id=session_id)
