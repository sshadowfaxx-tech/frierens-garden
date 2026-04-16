"""
Reflection & Self-Improvement System
Implements: Reflexion-style verbal reinforcement learning
Based on: NeurIPS 2025 self-improving agent research
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib

@dataclass
class ReflectionEntry:
    """A single reflection/lesson learned"""
    task_description: str
    outcome: str  # 'success', 'partial', 'failure'
    what_worked: List[str]
    what_failed: List[str]
    lessons_learned: List[str]
    would_do_differently: str
    timestamp: str
    tool_calls_used: List[str]
    error_messages: Optional[List[str]] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


class ReflectionEngine:
    """
    Implements self-reflection capabilities for continuous improvement.
    
    Pattern: After task completion, analyze what happened and capture
    insights for future similar tasks.
    """
    
    def __init__(self, workspace_path: str = "/root/.openclaw/workspace"):
        self.workspace = Path(workspace_path)
        self.reflections_file = self.workspace / "memory" / "reflections.jsonl"
        self.reflections_file.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache of common failures
        self.common_failures: Dict[str, int] = {}
        self.success_patterns: Dict[str, int] = {}
    
    def reflect(self, 
                task: str,
                outcome: str,
                steps_taken: List[str],
                tool_calls: List[Dict[str, Any]],
                errors: Optional[List[str]] = None,
                final_output: Optional[str] = None) -> ReflectionEntry:
        """
        Generate a reflection on completed task.
        
        Args:
            task: Original task description
            outcome: 'success', 'partial', or 'failure'
            steps_taken: List of steps executed
            tool_calls: Tools that were called
            errors: Any error messages encountered
            final_output: The final result
        """
        
        # Analyze what worked
        what_worked = []
        what_failed = []
        
        if outcome == "success":
            what_worked.append("Overall approach succeeded")
        elif outcome == "failure":
            what_failed.append("Overall approach failed")
        
        # Analyze tool usage patterns
        tool_names = [t.get('name', 'unknown') for t in tool_calls]
        
        if errors:
            for error in errors:
                if "timeout" in error.lower():
                    what_failed.append("Tool timeout - need retry logic")
                elif "permission" in error.lower() or "access" in error.lower():
                    what_failed.append("Permission/access error - check credentials")
                elif "not found" in error.lower():
                    what_failed.append("Resource not found - verify paths/IDs")
                else:
                    what_failed.append(f"Error: {error[:100]}")
        
        # Generate lessons
        lessons = []
        
        if len(tool_calls) > 10:
            lessons.append("Task required many tool calls - consider breaking into subtasks")
        
        if "search" in str(tool_names).lower() and "write" in str(tool_names).lower():
            lessons.append("Research-to-writing workflow - good pattern")
        
        if outcome == "failure" and not tool_calls:
            lessons.append("Failed before any tool use - need better initial planning")
        
        # Generate "would do differently"
        if outcome == "failure":
            would_do = "Break task into smaller steps and validate each before proceeding"
        elif len(steps_taken) > 20:
            would_do = "Plan more upfront to reduce iterative trial-and-error"
        else:
            would_do = "Similar approach next time"
        
        reflection = ReflectionEntry(
            task_description=task[:500],
            outcome=outcome,
            what_worked=what_worked,
            what_failed=what_failed,
            lessons_learned=lessons,
            would_do_differently=would_do,
            timestamp=datetime.now().isoformat(),
            tool_calls_used=tool_names,
            error_messages=errors
        )
        
        # Store it
        self._store_reflection(reflection)
        
        # Update pattern tracking
        self._update_patterns(reflection)
        
        return reflection
    
    def _store_reflection(self, reflection: ReflectionEntry):
        """Append reflection to storage"""
        with open(self.reflections_file, 'a') as f:
            f.write(json.dumps(reflection.to_dict()) + '\n')
    
    def _update_patterns(self, reflection: ReflectionEntry):
        """Track success/failure patterns"""
        task_hash = hashlib.md5(
            reflection.task_description[:100].encode()
        ).hexdigest()[:16]
        
        if reflection.outcome == "success":
            self.success_patterns[task_hash] = self.success_patterns.get(task_hash, 0) + 1
        else:
            self.common_failures[task_hash] = self.common_failures.get(task_hash, 0) + 1
    
    def get_relevant_lessons(self, task: str, limit: int = 3) -> List[str]:
        """
        Retrieve lessons from similar past tasks.
        (Simplified similarity matching)
        """
        task_words = set(task.lower().split())
        lessons = []
        
        if not self.reflections_file.exists():
            return lessons
        
        try:
            with open(self.reflections_file, 'r') as f:
                for line in f:
                    try:
                        ref = json.loads(line.strip())
                        ref_words = set(ref['task_description'].lower().split())
                        overlap = len(task_words & ref_words)
                        
                        if overlap >= 2:  # Some similarity
                            lessons.extend(ref.get('lessons_learned', []))
                            
                            # Add the "would do differently" if it was a failure
                            if ref.get('outcome') == 'failure':
                                lessons.append(f"Previously failed: {ref['would_do_differently']}")
                            
                            if len(lessons) >= limit * 3:
                                break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading reflections: {e}")
        
        # Deduplicate and return top
        seen = set()
        unique_lessons = []
        for lesson in lessons:
            if lesson not in seen:
                seen.add(lesson)
                unique_lessons.append(lesson)
                if len(unique_lessons) >= limit:
                    break
        
        return unique_lessons
    
    def get_reflection_context(self, task: str) -> str:
        """
        Get formatted reflection context for prompt enhancement.
        Call this before starting a similar task.
        """
        lessons = self.get_relevant_lessons(task)
        
        if not lessons:
            return ""
        
        context = "\n### Lessons from Similar Past Tasks:\n"
        for lesson in lessons:
            context += f"- {lesson}\n"
        
        return context


class SelfImprovementLoop:
    """
    Higher-level self-improvement orchestration.
    
    Integrates reflection with action to enable learning from experience.
    """
    
    def __init__(self):
        self.reflection_engine = ReflectionEngine()
        self.improvement_log: List[Dict] = []
    
    def execute_with_reflection(self, 
                               task: str,
                               execution_func,
                               *args, **kwargs) -> Any:
        """
        Execute a task with automatic reflection capture.
        
        Args:
            task: Description of what we're trying to do
            execution_func: The function to execute
            *args, **kwargs: Arguments for the function
            
        Returns:
            Result of execution_func
        """
        print(f"[Reflection] Starting task: {task[:100]}...")
        
        # Get relevant past lessons
        lessons_context = self.reflection_engine.get_reflection_context(task)
        if lessons_context:
            print(f"[Reflection] Found {lessons_context.count(chr(10)+'-')} relevant lessons")
        
        steps_taken = []
        tool_calls = []
        errors = []
        outcome = "unknown"
        
        try:
            # Execute the task
            result = execution_func(*args, **kwargs)
            outcome = "success"
            
            # Try to extract tool usage from result if it's a dict
            if isinstance(result, dict):
                if 'tool_calls' in result:
                    tool_calls = result['tool_calls']
                if 'steps' in result:
                    steps_taken = result['steps']
                    
        except Exception as e:
            outcome = "failure"
            errors.append(str(e))
            result = None
        
        # Generate reflection
        reflection = self.reflection_engine.reflect(
            task=task,
            outcome=outcome,
            steps_taken=steps_taken,
            tool_calls=tool_calls,
            errors=errors if errors else None,
            final_output=str(result)[:500] if result else None
        )
        
        print(f"[Reflection] Task completed: {outcome}")
        if reflection.lessons_learned:
            print(f"[Reflection] Lessons: {', '.join(reflection.lessons_learned[:2])}")
        
        return result
    
    def suggest_improvements(self) -> List[str]:
        """
        Analyze patterns and suggest systemic improvements.
        Call this periodically (e.g., daily/weekly).
        """
        suggestions = []
        
        # Check for recurring failures
        for pattern, count in self.reflection_engine.common_failures.items():
            if count >= 3:
                suggestions.append(
                    f"Recurring failure pattern detected ({count}x). "
                    "Consider adding guardrails or pre-validation."
                )
        
        # Check for success patterns to reinforce
        for pattern, count in self.reflection_engine.success_patterns.items():
            if count >= 5:
                suggestions.append(
                    f"Reliable success pattern ({count}x). Document as best practice."
                )
        
        return suggestions


# Decorator for automatic reflection

def with_reflection(task_description: str):
    """
    Decorator that automatically captures reflection after function execution.
    
    Usage:
        @with_reflection("Research AI agent architectures")
        def research_agents(query):
            # ... do research ...
            return results
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            loop = SelfImprovementLoop()
            return loop.execute_with_reflection(
                task_description,
                func,
                *args, **kwargs
            )
        return wrapper
    return decorator


# Global instance
_reflection_engine: Optional[ReflectionEngine] = None

def get_reflection_engine() -> ReflectionEngine:
    """Get global reflection engine"""
    global _reflection_engine
    if _reflection_engine is None:
        _reflection_engine = ReflectionEngine()
    return _reflection_engine
