"""
Planning & Reasoning Module
Implements: Chain of Thought, Tree of Thoughts, ReAct pattern
Based on: Yao et al. CoT/ToT/ReAct research
"""

import json
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

class ReasoningStrategy(Enum):
    CHAIN_OF_THOUGHT = "cot"           # Linear reasoning
    TREE_OF_THOUGHTS = "tot"           # Branching exploration
    REACT = "react"                     # Thought → Action → Observation

@dataclass
class ThoughtNode:
    """A single node in a reasoning tree"""
    content: str
    parent: Optional['ThoughtNode'] = None
    children: List['ThoughtNode'] = field(default_factory=list)
    score: float = 0.0  # Evaluation score (0-1)
    depth: int = 0
    is_terminal: bool = False
    
    def add_child(self, content: str) -> 'ThoughtNode':
        """Add a child thought"""
        child = ThoughtNode(
            content=content,
            parent=self,
            depth=self.depth + 1
        )
        self.children.append(child)
        return child
    
    def get_path(self) -> List[str]:
        """Get the path from root to this node"""
        path = []
        current = self
        while current:
            path.append(current.content)
            current = current.parent
        return list(reversed(path))


@dataclass
class Plan:
    """A structured plan with steps"""
    goal: str
    steps: List[Dict[str, Any]]
    current_step: int = 0
    status: str = "pending"  # pending, in_progress, completed, failed
    
    def to_dict(self) -> Dict:
        return {
            'goal': self.goal,
            'steps': self.steps,
            'current_step': self.current_step,
            'status': self.status
        }


class Planner:
    """
    Planning system implementing multiple reasoning strategies.
    """
    
    def __init__(self, llm_call_func: Optional[Callable] = None):
        """
        Args:
            llm_call_func: Function to call LLM for reasoning.
                          Should accept prompt string, return response string.
        """
        self.llm_call = llm_call_func
        self.plan_history: List[Plan] = []
    
    # ==================== Chain of Thought ====================
    
    def chain_of_thought(self, problem: str, max_steps: int = 5) -> str:
        """
        Simple linear reasoning: break problem into steps and solve sequentially.
        
        Returns: Reasoning chain as formatted string
        """
        if not self.llm_call:
            # Fallback without LLM
            return f"Let's think step by step about: {problem}"
        
        prompt = f"""Break down this problem into {max_steps} steps and solve it:

Problem: {problem}

Think through this step by step. For each step:
1. State what you're doing
2. Show your reasoning
3. Move to the next step

Format:
Step 1: [what you're doing]
Reasoning: [your thinking]
..."""
        
        return self.llm_call(prompt)
    
    # ==================== Tree of Thoughts ====================
    
    def tree_of_thoughts(self, 
                        problem: str,
                        num_branches: int = 3,
                        max_depth: int = 3,
                        evaluation_func: Optional[Callable[[str], float]] = None) -> ThoughtNode:
        """
        Explore multiple reasoning paths and select best one.
        
        Args:
            problem: The problem to solve
            num_branches: How many alternatives to generate at each step
            max_depth: Maximum depth of tree
            evaluation_func: Function to score a thought (0-1)
            
        Returns: Root node of thought tree
        """
        # Create root
        root = ThoughtNode(content=problem)
        
        if not self.llm_call:
            return root
        
        # Build tree breadth-first
        current_level = [root]
        
        for depth in range(max_depth):
            next_level = []
            
            for node in current_level:
                # Generate branches
                branches = self._generate_branches(node.content, num_branches)
                
                for branch_content in branches:
                    child = node.add_child(branch_content)
                    
                    # Score the thought
                    if evaluation_func:
                        child.score = evaluation_func(branch_content)
                    else:
                        child.score = self._default_evaluate(branch_content)
                    
                    next_level.append(child)
            
            current_level = next_level
        
        return root
    
    def _generate_branches(self, context: str, num: int) -> List[str]:
        """Generate alternative next steps"""
        if not self.llm_call:
            return [f"Alternative {i+1}" for i in range(num)]
        
        prompt = f"""Given this context:
{context}

Generate {num} different ways to proceed or approach this.
Number them 1-{num}. Be concise."""
        
        response = self.llm_call(prompt)
        
        # Parse branches from response
        branches = []
        for line in response.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('*')):
                # Remove numbering/bullets
                cleaned = line.lstrip('0123456789.-* ')
                if cleaned:
                    branches.append(cleaned)
        
        # Ensure we have at least some branches
        while len(branches) < num:
            branches.append(f"Alternative approach {len(branches)+1}")
        
        return branches[:num]
    
    def _default_evaluate(self, thought: str) -> float:
        """Default evaluation: prefer longer, more specific thoughts"""
        # Simple heuristic: length-based with specificity bonus
        score = min(len(thought) / 100, 1.0)
        
        # Bonus for actionable words
        action_words = ['step', 'plan', 'approach', 'method', 'strategy']
        for word in action_words:
            if word in thought.lower():
                score += 0.1
        
        return min(score, 1.0)
    
    def get_best_path(self, root: ThoughtNode) -> List[str]:
        """Get highest-scoring path from root to leaf"""
        best_path = []
        best_score = 0.0
        
        def dfs(node: ThoughtNode, current_path: List[str], current_score: float):
            nonlocal best_path, best_score
            
            current_path = current_path + [node.content]
            current_score += node.score
            
            if not node.children or node.is_terminal:
                # Leaf node - check if best
                avg_score = current_score / len(current_path)
                if avg_score > best_score:
                    best_score = avg_score
                    best_path = current_path
            else:
                for child in node.children:
                    dfs(child, current_path, current_score)
        
        for child in root.children:
            dfs(child, [root.content], root.score)
        
        return best_path if best_path else [root.content]
    
    # ==================== ReAct Pattern ====================
    
    def create_react_plan(self, goal: str, available_tools: List[Dict[str, Any]]) -> Plan:
        """
        Create a ReAct-style plan: Thought → Action → Observation loop
        
        Args:
            goal: What to achieve
            available_tools: List of available tools with descriptions
        """
        steps = []
        
        # Initial observation/thought
        steps.append({
            'type': 'thought',
            'content': f'I need to accomplish: {goal}',
            'tool': None
        })
        
        # Plan structure based on goal analysis
        if 'research' in goal.lower() or 'find' in goal.lower():
            steps.extend([
                {'type': 'thought', 'content': 'Break down research subtopics', 'tool': None},
                {'type': 'action', 'content': 'Search for initial information', 'tool': 'web_search'},
                {'type': 'observation', 'content': 'Review search results', 'tool': None},
                {'type': 'thought', 'content': 'Identify knowledge gaps', 'tool': None},
                {'type': 'action', 'content': 'Deep dive on specific topics', 'tool': 'web_search'},
                {'type': 'observation', 'content': 'Synthesize findings', 'tool': None},
            ])
        
        elif 'code' in goal.lower() or 'implement' in goal.lower():
            steps.extend([
                {'type': 'thought', 'content': 'Analyze requirements', 'tool': None},
                {'type': 'action', 'content': 'Review existing codebase', 'tool': 'file_read'},
                {'type': 'observation', 'content': 'Understand current structure', 'tool': None},
                {'type': 'thought', 'content': 'Plan implementation approach', 'tool': None},
                {'type': 'action', 'content': 'Write code', 'tool': 'file_write'},
                {'type': 'observation', 'content': 'Review and test', 'tool': None},
            ])
        
        elif 'write' in goal.lower() or 'create' in goal.lower():
            steps.extend([
                {'type': 'thought', 'content': 'Outline structure', 'tool': None},
                {'type': 'action', 'content': 'Gather source material', 'tool': 'web_search'},
                {'type': 'observation', 'content': 'Review gathered info', 'tool': None},
                {'type': 'thought', 'content': 'Draft content sections', 'tool': None},
                {'type': 'action', 'content': 'Write content', 'tool': 'file_write'},
                {'type': 'observation', 'content': 'Review and refine', 'tool': None},
            ])
        
        else:
            # Generic plan
            steps.extend([
                {'type': 'thought', 'content': 'Analyze the task', 'tool': None},
                {'type': 'action', 'content': 'Gather necessary information', 'tool': 'web_search'},
                {'type': 'observation', 'content': 'Process information', 'tool': None},
                {'type': 'thought', 'content': 'Formulate approach', 'tool': None},
                {'type': 'action', 'content': 'Execute plan', 'tool': None},
                {'type': 'observation', 'content': 'Verify results', 'tool': None},
            ])
        
        # Final step
        steps.append({
            'type': 'thought',
            'content': 'Task complete - summarize results',
            'tool': None
        })
        
        plan = Plan(goal=goal, steps=steps)
        self.plan_history.append(plan)
        return plan
    
    def execute_react_step(self, plan: Plan, execute_func: Callable) -> Any:
        """
        Execute the current step in a ReAct plan.
        
        Args:
            plan: The plan being executed
            execute_func: Function to execute the step (takes step dict, returns result)
            
        Returns:
            Result of step execution
        """
        if plan.current_step >= len(plan.steps):
            plan.status = "completed"
            return None
        
        step = plan.steps[plan.current_step]
        plan.status = "in_progress"
        
        print(f"[ReAct] Step {plan.current_step + 1}/{len(plan.steps)}: {step['type']}")
        print(f"  {step['content'][:100]}...")
        
        try:
            result = execute_func(step)
            plan.current_step += 1
            return result
        except Exception as e:
            plan.status = "failed"
            raise
    
    # ==================== Planning Utilities ====================
    
    def estimate_complexity(self, task: str) -> Dict[str, Any]:
        """Estimate task complexity to choose appropriate strategy"""
        
        complexity = {
            'score': 0,
            'strategy': ReasoningStrategy.CHAIN_OF_THOUGHT,
            'reasoning': []
        }
        
        task_lower = task.lower()
        
        # Check for multi-step indicators
        multi_step_indicators = [
            'and then', 'followed by', 'multiple', 'several',
            'research', 'analyze', 'compare', 'evaluate'
        ]
        for indicator in multi_step_indicators:
            if indicator in task_lower:
                complexity['score'] += 1
                complexity['reasoning'].append(f"Multi-step indicator: '{indicator}'")
        
        # Check for decision points
        if any(word in task_lower for word in ['choose', 'select', 'decide', 'best', 'optimal']):
            complexity['score'] += 2
            complexity['reasoning'].append("Requires decision making / evaluation")
        
        # Check for open-endedness
        if any(word in task_lower for word in ['improve', 'optimize', 'design', 'create']):
            complexity['score'] += 1
            complexity['reasoning'].append("Open-ended creative task")
        
        # Choose strategy
        if complexity['score'] >= 4:
            complexity['strategy'] = ReasoningStrategy.TREE_OF_THOUGHTS
            complexity['reasoning'].append("High complexity - using Tree of Thoughts")
        elif 'tool' in task_lower or 'search' in task_lower or 'file' in task_lower:
            complexity['strategy'] = ReasoningStrategy.REACT
            complexity['reasoning'].append("Involves tool use - using ReAct")
        else:
            complexity['reasoning'].append("Standard complexity - using Chain of Thought")
        
        return complexity
    
    def create_plan(self, goal: str) -> Plan:
        """
        Create appropriate plan based on task complexity.
        """
        complexity = self.estimate_complexity(goal)
        
        if complexity['strategy'] == ReasoningStrategy.REACT:
            return self.create_react_plan(goal, available_tools=[])
        else:
            # Simple sequential plan
            return Plan(
                goal=goal,
                steps=[
                    {'type': 'thought', 'content': 'Analyze requirements', 'tool': None},
                    {'type': 'action', 'content': 'Execute task', 'tool': None},
                    {'type': 'observation', 'content': 'Verify results', 'tool': None},
                ]
            )


class PlanExecutor:
    """
    Executes plans with error handling and adaptation.
    """
    
    def __init__(self, planner: Planner):
        self.planner = planner
        self.execution_log: List[Dict] = []
    
    def execute_plan(self, plan: Plan, step_executor: Callable, 
                     on_error: str = "pause") -> Dict[str, Any]:
        """
        Execute a full plan with error handling.
        
        Args:
            plan: Plan to execute
            step_executor: Function to execute each step
            on_error: 'pause', 'skip', or 'retry'
            
        Returns:
            Execution results summary
        """
        results = []
        errors = []
        
        while plan.current_step < len(plan.steps):
            step = plan.steps[plan.current_step]
            
            try:
                result = step_executor(step)
                results.append({
                    'step': plan.current_step,
                    'status': 'success',
                    'result': result
                })
                plan.current_step += 1
                
            except Exception as e:
                errors.append({
                    'step': plan.current_step,
                    'error': str(e),
                    'step_content': step.get('content', '')
                })
                
                if on_error == "pause":
                    plan.status = "paused"
                    break
                elif on_error == "skip":
                    plan.current_step += 1
                elif on_error == "retry":
                    # Will retry same step
                    pass
        
        if plan.current_step >= len(plan.steps):
            plan.status = "completed"
        
        return {
            'plan': plan.to_dict(),
            'results': results,
            'errors': errors,
            'success': len(errors) == 0
        }
