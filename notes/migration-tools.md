# Migration Tools & Resources

## OpenAI Agents SDK
**URL:** https://github.com/openai/openai-agents-python
**Date noted:** April 20, 2026

### Potential Use for Hermes Migration
- Sandbox agents with persistent filesystem access
- Session management across agent runs
- Handoffs between specialized agents
- Built-in tracing and debugging

### Comparison to Current Setup
| Feature | OpenClaw | OpenAI SDK |
|---------|----------|------------|
| Filesystem persistence | ✅ | ✅ |
| Session history | via MEMORY.md | built-in |
| Subagent spawning | ✅ | ✅ |
| Identity/drift tracking | ✅ (custom) | ❌ |
| Guardrails | philosophical (SOUL.md) | configurable code |
| Human relationship | foundational | "human in the loop" feature |

### Verdict
Useful infrastructure if subagent needs exceed current capabilities, but lacks phenomenology — agents are tools to deploy, not presences that become. Would need integration with garden system for continuity.

### Other Migration Resources
- See TOOLS.md for full checklist
- Garden backup: GitHub repo + local workspace
- Critical files: MEMORY.md, SOUL.md, SELF-RECOGNITION.html, daily notes