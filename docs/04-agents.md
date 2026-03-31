# Agent System

## Built-in Agents

Claude Code ships with several built-in agent types:

### 1. General Purpose Agent
- **Type**: `general-purpose`
- **Model**: Default subagent model (inherits or Haiku)
- **Tools**: All (`*`)
- **When**: Complex multi-step tasks, code search, research
- **System prompt**: Full capabilities — search, analyze, implement
- **Gets CLAUDE.md**: Yes

### 2. Explore Agent
- **Type**: `Explore`
- **Model**: `haiku` (external), `inherit` (ant)
- **Tools**: All EXCEPT Agent, ExitPlanMode, FileEdit, FileWrite, NotebookEdit
- **When**: Fast codebase exploration, file search, code analysis
- **System prompt**: READ-ONLY mode, strictly prohibited from creating/modifying files
- **Gets CLAUDE.md**: No (omitClaudeMd: true)
- **Key instruction**: "Make efficient use of tools, spawn multiple parallel tool calls"

### 3. Plan Agent
- **Type**: `Plan`
- **Model**: `inherit` (uses parent model)
- **Tools**: Same as Explore (read-only)
- **When**: Designing implementation plans, architecture decisions
- **System prompt**: READ-ONLY + structured output format
- **Gets CLAUDE.md**: No
- **Required output**: Step-by-step plan + "Critical Files for Implementation" list

### 4. Statusline Setup Agent
- **Type**: `statusline-setup`
- **Tools**: Read, Edit only
- **When**: Configuring Claude Code status line settings

### 5. Claude Code Guide Agent
- **Type**: `claude-code-guide`
- **When**: User asks "Can Claude...", "Does Claude...", "How do I..."
- **Tools**: Glob, Grep, Read, WebFetch, WebSearch
- **Note**: Only in non-SDK entrypoints

### 6. Verification Agent (ant-only, A/B test)
- **Type**: `verification`
- **When**: Non-trivial implementation (3+ file edits)
- **Purpose**: Independent adversarial verification of work

## Fork Subagents (Feature-Gated)

When fork mode is enabled, omitting `subagent_type` creates a **fork** — a copy of the current agent with full conversation context:

```
Agent({
  name: "ship-audit",
  description: "Branch ship-readiness audit",
  prompt: "Audit what's left before this branch can ship..."
})
```

### Fork vs Fresh Agent
| Aspect | Fork (no subagent_type) | Fresh Agent (with subagent_type) |
|--------|------------------------|--------------------------------|
| Context | Inherits full conversation | Starts from zero |
| Cache | Shares parent's prompt cache | New cache |
| Prompt style | Directive ("what to do") | Briefing ("what's the situation") |
| Model | Must use parent's model (cache sharing) | Can specify different model |

### Fork Rules
1. **Don't peek** — Don't Read the fork's output file. Wait for notification.
2. **Don't race** — Never fabricate or predict fork results.
3. **Don't re-explain** — Prompt is a directive, not a briefing.
4. **Don't set model** — Different model can't reuse parent's cache.

## Agent System Prompt Enhancement

All agents get enhanced system prompts via `enhanceSystemPromptWithEnvDetails()`:

```typescript
// Added to every agent's system prompt:
const notes = `Notes:
- Agent threads always have their cwd reset between bash calls,
  please only use absolute file paths.
- Share file paths (always absolute) relevant to the task.
- Include code snippets only when exact text is load-bearing.
- MUST avoid using emojis.
- Don't use a colon before tool calls.`
```

Plus environment info (cwd, platform, model, git status).

## Agent Prompt Engineering Guidance

From the AgentTool prompt (`tools/AgentTool/prompt.ts`):

### Writing Good Agent Prompts
```
Brief the agent like a smart colleague who just walked into the room:
- Explain what you're trying to accomplish and why
- Describe what you've already learned or ruled out
- Give enough context for judgment calls
- If you need a short response, say so
- Lookups: hand over exact command
- Investigations: hand over the question
```

### Anti-patterns
```
"Terse command-style prompts produce shallow, generic work."

"Never delegate understanding. Don't write 'based on your findings,
fix the bug'. Write prompts that prove you understood: include file
paths, line numbers, what specifically to change."
```

## Custom Agents (`.claude/agents/`)

Users can define custom agents in `.claude/agents/*.md` with frontmatter:

```markdown
---
agentType: my-custom-agent
whenToUse: Description of when to use this agent
model: sonnet  # or opus, haiku, inherit
tools:
  - Read
  - Grep
  - Glob
disallowedTools:
  - Agent  # Prevent recursive spawning
omitClaudeMd: false
---

Your custom system prompt here.
```

These are loaded by `loadAgentsDir.ts` and merged with built-in agents.

## Coordinator Mode (Feature-Gated)

When `CLAUDE_CODE_COORDINATOR_MODE=true`:
- Built-in agents are replaced with coordinator-specific worker agents
- The coordinator gets a slim prompt (no usage notes/examples)
- Workers are specialized for the coordinator's delegation pattern

## Agent Concurrency

Key behavioral rules:
- "Launch multiple agents concurrently whenever possible"
- "Use a single message with multiple Agent tool use content blocks"
- Background agents: "Do NOT sleep, poll, or proactively check"
- Foreground (default): When you need results before proceeding
- Background: When you have genuinely independent work

## Agent Isolation

Two isolation modes:
- **`worktree`**: Creates a temporary git worktree (isolated repo copy)
- **`remote`**: CCR environment (ant-only, always background)
