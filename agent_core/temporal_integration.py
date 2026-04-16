"""
Temporal Durable Execution Integration
Enables long-running, failure-resistant agent workflows with checkpointing
"""

import json
import asyncio
from typing import Optional, List, Dict, Any, Callable, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

# Temporal imports (optional dependency)
try:
    from temporalio import workflow, activity
    from temporalio.client import Client as TemporalClient
    from temporalio.worker import Worker
    TEMPORAL_AVAILABLE = True
except ImportError:
    TEMPORAL_AVAILABLE = False
    print("Warning: Temporal SDK not available, using fallback durable execution")


class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"  # Waiting for human approval
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class WorkflowCheckpoint:
    """Represents a workflow checkpoint for resumption"""
    step_number: int
    state: Dict[str, Any]
    timestamp: str
    last_action: Optional[str] = None
    human_approval_pending: bool = False


class DurableExecutionManager:
    """
    Manages durable execution with checkpointing.
    Falls back to file-based checkpointing if Temporal unavailable.
    """
    
    def __init__(self, 
                 workflow_id: Optional[str] = None,
                 checkpoint_dir: str = "/root/.openclaw/workspace/memory/checkpoints"):
        self.workflow_id = workflow_id or f"wf_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        self.checkpoints: List[WorkflowCheckpoint] = []
        self.current_step = 0
        self.status = WorkflowStatus.PENDING
        
        # Temporal client (if available)
        self._temporal_client: Optional[Any] = None
        self._using_temporal = False
    
    async def connect_temporal(self, host: str = "localhost:7233") -> bool:
        """
        Connect to Temporal server.
        
        Returns:
            True if connected successfully
        """
        if not TEMPORAL_AVAILABLE:
            print("⚠ Temporal SDK not installed, using file-based checkpointing")
            return False
        
        try:
            self._temporal_client = await TemporalClient.connect(host)
            self._using_temporal = True
            print(f"✓ Connected to Temporal at {host}")
            return True
        except Exception as e:
            print(f"⚠ Temporal connection failed: {e}")
            print("  Falling back to file-based checkpointing")
            return False
    
    async def checkpoint(self, state: Dict[str, Any], 
                        action: Optional[str] = None) -> WorkflowCheckpoint:
        """
        Create a checkpoint of current workflow state.
        
        Args:
            state: Current workflow state
            action: Description of last action taken
            
        Returns:
            Checkpoint object
        """
        checkpoint = WorkflowCheckpoint(
            step_number=self.current_step,
            state=state.copy(),
            timestamp=datetime.now().isoformat(),
            last_action=action
        )
        
        self.checkpoints.append(checkpoint)
        
        # Persist checkpoint
        await self._persist_checkpoint(checkpoint)
        
        self.current_step += 1
        return checkpoint
    
    async def _persist_checkpoint(self, checkpoint: WorkflowCheckpoint):
        """Persist checkpoint to storage"""
        if self._using_temporal:
            # Temporal handles persistence automatically
            return
        
        # File-based fallback
        checkpoint_file = self.checkpoint_dir / f"{self.workflow_id}_step_{checkpoint.step_number}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump({
                'workflow_id': self.workflow_id,
                'step_number': checkpoint.step_number,
                'state': checkpoint.state,
                'timestamp': checkpoint.timestamp,
                'last_action': checkpoint.last_action
            }, f, indent=2)
    
    async def load_checkpoint(self, step_number: Optional[int] = None) -> Optional[WorkflowCheckpoint]:
        """
        Load a checkpoint.
        
        Args:
            step_number: Specific step to load, or None for latest
            
        Returns:
            Checkpoint or None if not found
        """
        if step_number is None:
            # Return latest
            if self.checkpoints:
                return self.checkpoints[-1]
            
            # Try to load from file
            return await self._load_latest_from_file()
        else:
            # Find specific checkpoint
            for cp in self.checkpoints:
                if cp.step_number == step_number:
                    return cp
            
            # Try file
            return await self._load_from_file(step_number)
    
    async def _load_latest_from_file(self) -> Optional[WorkflowCheckpoint]:
        """Load latest checkpoint from file"""
        checkpoints = sorted(
            self.checkpoint_dir.glob(f"{self.workflow_id}_step_*.json"),
            key=lambda p: int(p.stem.split('_')[-1])
        )
        
        if not checkpoints:
            return None
        
        return await self._load_from_file_path(checkpoints[-1])
    
    async def _load_from_file(self, step_number: int) -> Optional[WorkflowCheckpoint]:
        """Load specific checkpoint from file"""
        checkpoint_file = self.checkpoint_dir / f"{self.workflow_id}_step_{step_number}.json"
        if not checkpoint_file.exists():
            return None
        return await self._load_from_file_path(checkpoint_file)
    
    async def _load_from_file_path(self, path: Path) -> WorkflowCheckpoint:
        """Load checkpoint from file path"""
        with open(path, 'r') as f:
            data = json.load(f)
        
        return WorkflowCheckpoint(
            step_number=data['step_number'],
            state=data['state'],
            timestamp=data['timestamp'],
            last_action=data.get('last_action')
        )
    
    async def request_human_approval(self, 
                                    action_description: str,
                                    context: Dict[str, Any]) -> bool:
        """
        Pause workflow for human approval.
        
        Args:
            action_description: What needs approval
            context: Additional context
            
        Returns:
            True if approved, False if denied
        """
        self.status = WorkflowStatus.PAUSED
        
        # Create checkpoint with approval pending
        checkpoint = await self.checkpoint({
            **context,
            'approval_pending': True,
            'action_description': action_description
        }, action="waiting_for_approval")
        
        checkpoint.human_approval_pending = True
        
        if self._using_temporal:
            # Temporal handles the pause/resume
            # In real implementation, would use Temporal's async completion
            print(f"⏸ Workflow {self.workflow_id} paused for human approval")
            print(f"   Action: {action_description}")
            # Return False for now - would be resolved by external signal
            return False
        else:
            # File-based: create approval request file
            approval_file = self.checkpoint_dir / f"{self.workflow_id}_approval_pending.json"
            with open(approval_file, 'w') as f:
                json.dump({
                    'workflow_id': self.workflow_id,
                    'action': action_description,
                    'context': context,
                    'checkpoint_step': checkpoint.step_number,
                    'requested_at': datetime.now().isoformat()
                }, f, indent=2)
            
            print(f"⏸ Approval required: {action_description}")
            print(f"   Check: {approval_file}")
            return False
    
    async def resume_from_checkpoint(self, 
                                    step_number: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Resume workflow from checkpoint.
        
        Args:
            step_number: Step to resume from, or None for latest
            
        Returns:
            State dictionary or None
        """
        checkpoint = await self.load_checkpoint(step_number)
        
        if checkpoint:
            self.current_step = checkpoint.step_number
            self.status = WorkflowStatus.RUNNING
            print(f"▶ Resumed workflow {self.workflow_id} from step {checkpoint.step_number}")
            return checkpoint.state
        
        return None
    
    def get_execution_trace(self) -> List[Dict[str, Any]]:
        """Get full execution trace for debugging"""
        return [
            {
                'step': cp.step_number,
                'action': cp.last_action,
                'timestamp': cp.timestamp,
                'state_keys': list(cp.state.keys())
            }
            for cp in self.checkpoints
        ]


class DurableAgentLoop:
    """
    Agent execution loop with durable execution support.
    
    Features:
    - Automatic checkpointing
    - Crash recovery
    - Human-in-the-loop pausing
    - Execution tracing
    """
    
    def __init__(self, 
                 durable_manager: DurableExecutionManager,
                 max_steps: int = 100):
        self.durable = durable_manager
        self.max_steps = max_steps
        self.on_step: Optional[Callable[[int, Dict], None]] = None
        self.on_approval_needed: Optional[Callable[[str, Dict], None]] = None
    
    async def execute(self, 
                     initial_state: Dict[str, Any],
                     step_func: Callable[[int, Dict], Dict[str, Any]],
                     should_continue: Callable[[int, Dict], bool]) -> Dict[str, Any]:
        """
        Execute durable agent loop.
        
        Args:
            initial_state: Starting state
            step_func: Function(state) -> new_state
            should_continue: Function(step, state) -> bool
            
        Returns:
            Final state
        """
        state = initial_state.copy()
        start_step = self.durable.current_step
        
        self.durable.status = WorkflowStatus.RUNNING
        
        try:
            for step in range(start_step, self.max_steps):
                # Check if should continue
                if not should_continue(step, state):
                    break
                
                # Execute step
                try:
                    new_state = await step_func(step, state)
                    state.update(new_state)
                    
                    # Checkpoint after successful step
                    await self.durable.checkpoint(state, action=f"step_{step}")
                    
                    if self.on_step:
                        self.on_step(step, state)
                    
                except Exception as e:
                    # Log error and checkpoint failed state
                    state['last_error'] = str(e)
                    await self.durable.checkpoint(state, action=f"step_{step}_failed")
                    
                    # Decide whether to retry or fail
                    if state.get('retry_count', 0) < 3:
                        state['retry_count'] = state.get('retry_count', 0) + 1
                        self.durable.status = WorkflowStatus.RETRYING
                        await asyncio.sleep(2 ** state['retry_count'])  # Exponential backoff
                    else:
                        self.durable.status = WorkflowStatus.FAILED
                        raise
            
            self.durable.status = WorkflowStatus.COMPLETED
            return state
            
        except Exception as e:
            self.durable.status = WorkflowStatus.FAILED
            state['error'] = str(e)
            return state
    
    async def execute_with_recovery(self,
                                   initial_state: Dict[str, Any],
                                   step_func: Callable[[int, Dict], Dict[str, Any]],
                                   should_continue: Callable[[int, Dict], bool]) -> Dict[str, Any]:
        """
        Execute with automatic recovery from checkpoint.
        """
        # Try to load checkpoint
        checkpoint = await self.durable.load_checkpoint()
        
        if checkpoint and checkpoint.step_number > 0:
            print(f"🔄 Recovering from checkpoint (step {checkpoint.step_number})")
            state = checkpoint.state
        else:
            state = initial_state
        
        return await self.execute(state, step_func, should_continue)


class ApprovalManager:
    """
    Manages human approvals for durable workflows.
    """
    
    def __init__(self, checkpoint_dir: str = "/root/.openclaw/workspace/memory/checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
    
    def list_pending_approvals(self) -> List[Dict[str, Any]]:
        """List all workflows waiting for approval"""
        pending = []
        
        for approval_file in self.checkpoint_dir.glob("*_approval_pending.json"):
            with open(approval_file, 'r') as f:
                data = json.load(f)
                pending.append(data)
        
        return pending
    
    def approve(self, workflow_id: str, approver: str = "human") -> bool:
        """
        Approve a pending workflow.
        
        Returns:
            True if approved successfully
        """
        approval_file = self.checkpoint_dir / f"{workflow_id}_approval_pending.json"
        
        if not approval_file.exists():
            return False
        
        # Load approval request
        with open(approval_file, 'r') as f:
            request = json.load(f)
        
        # Create approval grant file
        grant_file = self.checkpoint_dir / f"{workflow_id}_approval_granted.json"
        with open(grant_file, 'w') as f:
            json.dump({
                **request,
                'approved': True,
                'approved_by': approver,
                'approved_at': datetime.now().isoformat()
            }, f, indent=2)
        
        # Remove pending file
        approval_file.unlink()
        
        print(f"✅ Approved workflow {workflow_id}")
        return True
    
    def deny(self, workflow_id: str, reason: str = "", denier: str = "human") -> bool:
        """Deny a pending workflow"""
        approval_file = self.checkpoint_dir / f"{workflow_id}_approval_pending.json"
        
        if not approval_file.exists():
            return False
        
        with open(approval_file, 'r') as f:
            request = json.load(f)
        
        denial_file = self.checkpoint_dir / f"{workflow_id}_approval_denied.json"
        with open(denial_file, 'w') as f:
            json.dump({
                **request,
                'approved': False,
                'denied_by': denier,
                'reason': reason,
                'denied_at': datetime.now().isoformat()
            }, f, indent=2)
        
        approval_file.unlink()
        
        print(f"❌ Denied workflow {workflow_id}: {reason}")
        return True


# Convenience functions

def create_durable_workflow(workflow_id: Optional[str] = None,
                           use_temporal: bool = True) -> DurableExecutionManager:
    """
    Create a new durable workflow manager.
    
    Args:
        workflow_id: Optional workflow ID (generated if not provided)
        use_temporal: Try to connect to Temporal (fallbacks to file-based)
        
    Returns:
        DurableExecutionManager instance
    """
    manager = DurableExecutionManager(workflow_id)
    
    if use_temporal:
        # Note: This is async, caller should await connect_temporal
        pass
    
    return manager


# Example usage
async def demo_durable_execution():
    """Demonstrate durable execution"""
    
    # Create durable manager
    durable = create_durable_workflow("demo_workflow")
    await durable.connect_temporal()  # Falls back to file if Temporal unavailable
    
    # Create agent loop
    loop = DurableAgentLoop(durable, max_steps=10)
    
    # Define step function
    async def step(step_num: int, state: Dict) -> Dict:
        print(f"Executing step {step_num}")
        return {'progress': step_num * 10}
    
    # Define continuation condition
    def should_continue(step: int, state: Dict) -> bool:
        return step < 5 and state.get('progress', 0) < 50
    
    # Execute
    final_state = await loop.execute_with_recovery(
        initial_state={'progress': 0},
        step_func=step,
        should_continue=should_continue
    )
    
    print(f"Final state: {final_state}")
    print(f"Execution trace: {durable.get_execution_trace()}")


if __name__ == "__main__":
    asyncio.run(demo_durable_execution())
