"""
Enhanced Agent Core Package - Production Ready

Implements Tier 1 Frontier Features:
- Vector Embeddings for Semantic Memory (ChromaDB)
- MCP Protocol for Tool Integration
- Temporal Durable Execution

Plus: Reflection, Planning, Safety (from previous implementation)
"""

__version__ = "0.2.0"

# Core Systems
from .memory_system import (
    MemoryManager, 
    WorkingMemory,
    SessionMemory, 
    VectorMemory,
    get_memory
)

from .reflection_system import (
    ReflectionEngine,
    SelfImprovementLoop,
    with_reflection,
    get_reflection_engine
)

from .planning_system import (
    Planner,
    PlanExecutor,
    Plan,
    ThoughtNode,
    ReasoningStrategy
)

from .safety_system import (
    SafetyManager,
    InputGuardrails,
    OutputGuardrails,
    ActionGuardrails,
    AuditLogger,
    RiskLevel,
    get_safety_manager
)

# NEW: MCP Integration
from .mcp_client import (
    MCPClient,
    MCPToolRegistry,
    MCPIntegrationHelper,
    MCPTool,
    get_mcp_registry,
    COMMON_MCP_SERVERS
)

# NEW: Temporal Durable Execution
from .temporal_integration import (
    DurableExecutionManager,
    DurableAgentLoop,
    ApprovalManager,
    WorkflowCheckpoint,
    WorkflowStatus,
    create_durable_workflow
)

# Main Agent
from .enhanced_agent import (
    EnhancedAgent,
    AgentConfig,
    create_enhanced_agent
)

__all__ = [
    # Version
    '__version__',
    
    # Core Agent
    'EnhancedAgent',
    'AgentConfig', 
    'create_enhanced_agent',
    
    # Memory (NEW: Vector-based)
    'MemoryManager',
    'WorkingMemory',
    'SessionMemory',
    'VectorMemory',
    'get_memory',
    
    # Reflection
    'ReflectionEngine',
    'SelfImprovementLoop',
    'with_reflection',
    'get_reflection_engine',
    
    # Planning
    'Planner',
    'PlanExecutor',
    'Plan',
    'ThoughtNode',
    'ReasoningStrategy',
    
    # Safety
    'SafetyManager',
    'InputGuardrails',
    'OutputGuardrails',
    'ActionGuardrails',
    'AuditLogger',
    'RiskLevel',
    'get_safety_manager',
    
    # NEW: MCP
    'MCPClient',
    'MCPToolRegistry',
    'MCPIntegrationHelper',
    'MCPTool',
    'get_mcp_registry',
    'COMMON_MCP_SERVERS',
    
    # NEW: Temporal
    'DurableExecutionManager',
    'DurableAgentLoop',
    'ApprovalManager',
    'WorkflowCheckpoint',
    'WorkflowStatus',
    'create_durable_workflow',
]
