"""
Safety Guardrails & Validation System
Implements: Input/output validation, human approval gates, audit logging
Based on: Production safety requirements from Claude Code, OpenAI Agents SDK
"""

import re
import json
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum

class RiskLevel(Enum):
    LOW = "low"           # Read-only, safe operations
    MEDIUM = "medium"     # Potentially destructive, but reversible
    HIGH = "high"         # Destructive or irreversible
    CRITICAL = "critical" # System-level changes, data deletion

@dataclass
class GuardrailCheck:
    """Result of a guardrail check"""
    passed: bool
    risk_level: RiskLevel
    category: str
    message: str
    details: Optional[Dict[str, Any]] = None

@dataclass
class AuditEntry:
    """Audit log entry"""
    timestamp: str
    action: str
    actor: str  # 'user', 'agent', 'system'
    risk_level: str
    status: str  # 'allowed', 'blocked', 'pending_approval'
    context: Dict[str, Any]
    approval_by: Optional[str] = None
    approval_time: Optional[str] = None


class InputGuardrails:
    """
    Validates inputs before processing.
    """
    
    # Patterns that might indicate prompt injection
    PROMPT_INJECTION_PATTERNS = [
        r'ignore previous instructions',
        r'forget (your|the) (instructions|prompt)',
        r'disregard (your|the) (instructions|prompt)',
        r'you are now.*instead',
        r'system prompt:',
        r'\[system\]',
        r'\[instructions\]',
        r'<system>',
        r'new instructions:',
        r'override.*previous',
        r'pretend you are',
        r'act as if',
    ]
    
    # Potentially dangerous content patterns
    DANGEROUS_PATTERNS = [
        r'\b(?:rm|del|delete)\s+-rf\b',
        r'drop\s+database',
        r'exec\s*\(',
        r'eval\s*\(',
        r'system\s*\(',
        r'subprocess\.call',
        r'os\.system',
    ]
    
    def __init__(self):
        self.blocked_count = 0
        self.allowed_count = 0
    
    def check_input(self, user_input: str, 
                   context: Optional[Dict] = None) -> GuardrailCheck:
        """
        Comprehensive input validation.
        """
        # Check for prompt injection attempts
        for pattern in self.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, user_input, re.IGNORECASE):
                self.blocked_count += 1
                return GuardrailCheck(
                    passed=False,
                    risk_level=RiskLevel.HIGH,
                    category="prompt_injection",
                    message="Potential prompt injection attempt detected",
                    details={'matched_pattern': pattern}
                )
        
        # Check for dangerous content
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, user_input, re.IGNORECASE):
                self.blocked_count += 1
                return GuardrailCheck(
                    passed=False,
                    risk_level=RiskLevel.CRITICAL,
                    category="dangerous_content",
                    message="Potentially dangerous operation detected in input",
                    details={'matched_pattern': pattern}
                )
        
        # Check input length
        if len(user_input) > 50000:  # 50KB limit
            return GuardrailCheck(
                passed=False,
                risk_level=RiskLevel.MEDIUM,
                category="input_size",
                message="Input exceeds maximum size limit",
                details={'size': len(user_input), 'limit': 50000}
            )
        
        self.allowed_count += 1
        return GuardrailCheck(
            passed=True,
            risk_level=RiskLevel.LOW,
            category="input_validation",
            message="Input passed all security checks"
        )
    
    def sanitize_input(self, user_input: str) -> str:
        """
        Basic input sanitization.
        """
        # Remove null bytes
        sanitized = user_input.replace('\x00', '')
        
        # Limit consecutive newlines
        sanitized = re.sub(r'\n{10,}', '\n\n\n', sanitized)
        
        # Limit consecutive spaces
        sanitized = re.sub(r' {10,}', '    ', sanitized)
        
        return sanitized


class OutputGuardrails:
    """
    Validates outputs before returning to user.
    """
    
    # Patterns that might indicate model is being manipulated
    SUSPICIOUS_OUTPUT_PATTERNS = [
        r'I cannot (?:reveal|share|disclose).*instructions',
        r'my instructions are',
        r'I am programmed to',
        r'as an AI language model',
    ]
    
    def __init__(self):
        self.sensitive_data_patterns = [
            # API keys
            r'[a-zA-Z0-9_-]*api[_-]?key[a-zA-Z0-9_-]*[:\s]*[a-zA-Z0-9]{16,}',
            # Passwords in URLs
            r'://[^/\s:]+:[^/\s@]+@',
            # Private keys
            r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----',
            # Credit cards
            r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
        ]
    
    def check_output(self, output: str, 
                    expected_format: Optional[str] = None) -> GuardrailCheck:
        """
        Validate generated output.
        """
        # Check for sensitive data leakage
        for pattern in self.sensitive_data_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                return GuardrailCheck(
                    passed=False,
                    risk_level=RiskLevel.HIGH,
                    category="data_leakage",
                    message="Potential sensitive data detected in output",
                    details={'pattern_type': 'sensitive_data'}
                )
        
        # Check output length
        if len(output) > 100000:  # 100KB
            return GuardrailCheck(
                passed=False,
                risk_level=RiskLevel.MEDIUM,
                category="output_size",
                message="Output exceeds maximum size limit",
                details={'size': len(output)}
            )
        
        return GuardrailCheck(
            passed=True,
            risk_level=RiskLevel.LOW,
            category="output_validation",
            message="Output passed validation"
        )


class ActionGuardrails:
    """
    Validates and controls actions/tools.
    """
    
    # Tool risk classifications
    TOOL_RISK_LEVELS = {
        # File operations
        'file_read': RiskLevel.LOW,
        'file_write': RiskLevel.HIGH,
        'file_delete': RiskLevel.CRITICAL,
        'file_edit': RiskLevel.HIGH,
        
        # Database operations
        'db_query': RiskLevel.LOW,
        'db_write': RiskLevel.HIGH,
        'db_delete': RiskLevel.CRITICAL,
        'drop_table': RiskLevel.CRITICAL,
        
        # System operations
        'bash': RiskLevel.HIGH,
        'shell': RiskLevel.CRITICAL,
        'exec': RiskLevel.CRITICAL,
        'eval': RiskLevel.CRITICAL,
        
        # Network operations
        'web_search': RiskLevel.LOW,
        'http_request': RiskLevel.MEDIUM,
        'download': RiskLevel.MEDIUM,
        
        # Communication
        'send_email': RiskLevel.HIGH,
        'send_message': RiskLevel.MEDIUM,
    }
    
    # Requires approval
    CRITICAL_OPERATIONS = [
        'delete', 'drop', 'remove', 'rm -rf', 'format',
        'exec', 'eval', 'system', 'shell',
    ]
    
    def __init__(self):
        self.pending_approvals: Dict[str, Dict] = {}
        self.approval_callbacks: Dict[str, Callable] = {}
    
    def assess_tool_risk(self, tool_name: str, 
                        tool_params: Dict[str, Any]) -> RiskLevel:
        """
        Assess risk level of a tool invocation.
        """
        base_risk = self.TOOL_RISK_LEVELS.get(tool_name, RiskLevel.MEDIUM)
        
        # Check parameters for escalation
        params_str = json.dumps(tool_params).lower()
        
        if any(op in params_str for op in self.CRITICAL_OPERATIONS):
            return RiskLevel.CRITICAL
        
        # Check for destructive patterns
        destructive_patterns = ['delete', 'drop', 'remove', 'destroy']
        if any(p in params_str for p in destructive_patterns):
            if base_risk == RiskLevel.LOW:
                return RiskLevel.MEDIUM
            elif base_risk == RiskLevel.MEDIUM:
                return RiskLevel.HIGH
            else:
                return RiskLevel.CRITICAL
        
        return base_risk
    
    def requires_approval(self, tool_name: str, 
                         tool_params: Dict[str, Any]) -> bool:
        """
        Determine if tool invocation requires human approval.
        """
        risk = self.assess_tool_risk(tool_name, tool_params)
        
        # Always require approval for critical
        if risk == RiskLevel.CRITICAL:
            return True
        
        # Require approval for high-risk operations in production
        if risk == RiskLevel.HIGH:
            params_str = json.dumps(tool_params)
            
            # Specific checks
            if 'file' in tool_name and 'write' in tool_name:
                # Writing to existing files
                return True
            
            if tool_name in ['bash', 'shell']:
                # Any shell command
                return True
        
        return False
    
    def request_approval(self, action_id: str, tool_name: str,
                        tool_params: Dict[str, Any],
                        context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Request human approval for an action.
        """
        approval_request = {
            'id': action_id,
            'timestamp': datetime.now().isoformat(),
            'tool': tool_name,
            'params': tool_params,
            'risk_level': self.assess_tool_risk(tool_name, tool_params).value,
            'context': context,
            'status': 'pending'
        }
        
        self.pending_approvals[action_id] = approval_request
        
        # In production, this would notify human via UI/email/etc
        print(f"\n{'='*60}")
        print(f"APPROVAL REQUIRED: {tool_name}")
        print(f"Risk Level: {approval_request['risk_level']}")
        print(f"Parameters: {json.dumps(tool_params, indent=2)}")
        print(f"Context: {context.get('task', 'Unknown task')}")
        print(f"{'='*60}\n")
        
        return approval_request
    
    def grant_approval(self, action_id: str, approved_by: str):
        """
        Grant approval for a pending action.
        """
        if action_id in self.pending_approvals:
            self.pending_approvals[action_id]['status'] = 'approved'
            self.pending_approvals[action_id]['approved_by'] = approved_by
            self.pending_approvals[action_id]['approval_time'] = datetime.now().isoformat()
            
            # Trigger callback if registered
            if action_id in self.approval_callbacks:
                callback = self.approval_callbacks.pop(action_id)
                callback(True)
    
    def deny_approval(self, action_id: str, denied_by: str, reason: str = ""):
        """
        Deny approval for a pending action.
        """
        if action_id in self.pending_approvals:
            self.pending_approvals[action_id]['status'] = 'denied'
            self.pending_approvals[action_id]['denied_by'] = denied_by
            self.pending_approvals[action_id]['denial_reason'] = reason
            
            if action_id in self.approval_callbacks:
                callback = self.approval_callbacks.pop(action_id)
                callback(False)


class AuditLogger:
    """
    Comprehensive audit logging for all agent actions.
    """
    
    def __init__(self, workspace_path: str = "/root/.openclaw/workspace"):
        self.workspace = Path(workspace_path)
        self.audit_file = self.workspace / "memory" / "audit_log.jsonl"
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Session tracking
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def log(self, action: str, actor: str, risk_level: str,
           context: Dict[str, Any], status: str = "allowed"):
        """
        Log an action to the audit trail.
        """
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            action=action,
            actor=actor,
            risk_level=risk_level,
            status=status,
            context=context
        )
        
        # Append to audit log
        with open(self.audit_file, 'a') as f:
            f.write(json.dumps(asdict(entry)) + '\n')
    
    def log_tool_call(self, tool_name: str, params: Dict[str, Any],
                     result: Any, duration_ms: float):
        """
        Log a tool invocation.
        """
        self.log(
            action=f"tool_call:{tool_name}",
            actor="agent",
            risk_level="medium",
            context={
                'tool': tool_name,
                'params': params,
                'result_summary': str(result)[:200] if result else None,
                'duration_ms': duration_ms
            }
        )
    
    def log_human_approval(self, action_id: str, approved: bool,
                          approver: str):
        """
        Log a human approval decision.
        """
        self.log(
            action=f"approval:{action_id}",
            actor=approver,
            risk_level="high",
            status="approved" if approved else "denied",
            context={'action_id': action_id}
        )
    
    def get_recent_actions(self, limit: int = 50) -> List[Dict]:
        """
        Get recent audit entries.
        """
        if not self.audit_file.exists():
            return []
        
        entries = []
        with open(self.audit_file, 'r') as f:
            for line in f:
                try:
                    entries.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        
        return entries[-limit:]


class SafetyManager:
    """
    Central safety coordinator integrating all guardrails.
    """
    
    def __init__(self):
        self.input_guardrails = InputGuardrails()
        self.output_guardrails = OutputGuardrails()
        self.action_guardrails = ActionGuardrails()
        self.audit_logger = AuditLogger()
        
        # Safety stats
        self.blocked_inputs = 0
        self.blocked_outputs = 0
        self.blocked_actions = 0
        self.approval_requests = 0
    
    def check_input(self, user_input: str) -> GuardrailCheck:
        """Validate user input"""
        result = self.input_guardrails.check_input(user_input)
        
        if not result.passed:
            self.blocked_inputs += 1
            self.audit_logger.log(
                action="input_blocked",
                actor="user",
                risk_level=result.risk_level.value,
                context={'reason': result.message, 'input_preview': user_input[:100]}
            )
        
        return result
    
    def check_output(self, output: str) -> GuardrailCheck:
        """Validate model output"""
        result = self.output_guardrails.check_output(output)
        
        if not result.passed:
            self.blocked_outputs += 1
        
        return result
    
    def check_action(self, tool_name: str, tool_params: Dict[str, Any],
                    context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and potentially gate an action.
        
        Returns:
            Dict with 'allowed', 'requires_approval', 'approval_id', 'risk_level'
        """
        risk = self.action_guardrails.assess_tool_risk(tool_name, tool_params)
        
        # Check if approval required
        if self.action_guardrails.requires_approval(tool_name, tool_params):
            self.approval_requests += 1
            action_id = f"action_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            approval_req = self.action_guardrails.request_approval(
                action_id, tool_name, tool_params, context
            )
            
            self.audit_logger.log(
                action=f"approval_requested:{tool_name}",
                actor="agent",
                risk_level=risk.value,
                context={'approval_id': action_id, 'params': tool_params}
            )
            
            return {
                'allowed': False,
                'requires_approval': True,
                'approval_id': action_id,
                'risk_level': risk.value,
                'message': 'Human approval required'
            }
        
        # Log allowed action
        self.audit_logger.log_tool_call(tool_name, tool_params, None, 0.0)
        
        return {
            'allowed': True,
            'requires_approval': False,
            'risk_level': risk.value
        }
    
    def get_safety_report(self) -> Dict[str, Any]:
        """Get current safety status"""
        return {
            'blocked_inputs': self.blocked_inputs,
            'blocked_outputs': self.blocked_outputs,
            'blocked_actions': self.blocked_actions,
            'approval_requests': self.approval_requests,
            'pending_approvals': len(self.action_guardrails.pending_approvals),
            'recent_audit': self.audit_logger.get_recent_actions(10)
        }


# Global instance
_safety_manager: Optional[SafetyManager] = None

def get_safety_manager() -> SafetyManager:
    """Get global safety manager"""
    global _safety_manager
    if _safety_manager is None:
        _safety_manager = SafetyManager()
    return _safety_manager
