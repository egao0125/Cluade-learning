# Community Methods for Using Claude Code Effectively

Compiled from community GitHub repos, discussions, and analysis of Claude Code's source.

## Key Community Repos

### 1. nirholas/claude-code
- Archives the leaked Claude Code source with exploration tools
- Built an MCP server for exploring the source code
- Key insight: The `src/` directory is preserved as-is for study
- Provides linting and type-checking infrastructure for the source

### 2. Leonxlnx/claude-code-system-prompts
- Extracted and documented Claude Code's full system prompts
- Tracks prompt changes across versions
- Community reference for understanding Claude's behavioral instructions

### 3. instructkr/claude-code (Korean community)
- Korean-language guide and analysis of Claude Code
- Focus on practical usage patterns and CLAUDE.md optimization
- Community tips for Korean-language projects

## Understanding the System Prompt — What Matters Most

From source analysis, the most impactful parts of the system prompt are:

### 1. CLAUDE.md is Your Lever
The system prompt explicitly says:
```
"Codebase and user instructions are shown below. Be sure to adhere
to these instructions. IMPORTANT: These instructions OVERRIDE any
default behavior and you MUST follow them exactly as written."
```

This means CLAUDE.md instructions have **higher priority than the built-in system prompt**. This is the #1 mechanism for customizing Claude Code's behavior.

### 2. Output Style Overrides
```json
// settings.json
{
  "outputStyle": "custom-style-name"
}
```
Output styles can replace the entire "Doing tasks" section of the system prompt. This is a powerful but underused customization point.

### 3. The Permission Mode Hierarchy
```
bypass > auto > default
```
For trusted automation, `bypass` mode eliminates permission prompts entirely. For semi-trusted work, `auto` mode with the yolo classifier handles ~90% of decisions automatically.

## CLAUDE.md Engineering Techniques

### Technique 1: Override Default Behavior
```markdown
# CLAUDE.md
- Always use pnpm instead of npm
- Never create new test files; add tests to existing files
- Use Japanese for all code comments
- Skip type annotations on local variables (TypeScript can infer them)
```

### Technique 2: Project Context Injection
```markdown
# CLAUDE.md
## Architecture
This is a Next.js 14 app with App Router. API routes are in app/api/.
State management uses Zustand. Database is Prisma + PostgreSQL.

## Testing
Run tests: `pnpm test`
Run specific: `pnpm test -- --grep "pattern"`
Tests use Vitest, not Jest.
```

### Technique 3: Workflow Automation via Hooks
```json
// .claude/settings.json
{
  "hooks": {
    "post_tool_use": [{
      "command": "scripts/auto-lint.sh",
      "if": "FileEdit"
    }],
    "pre_tool_use": [{
      "command": "scripts/check-branch.sh",
      "if": "Bash(git push *)"
    }]
  }
}
```

### Technique 4: Custom Agents for Specialized Work
```markdown
<!-- .claude/agents/db-migration.md -->
---
agentType: db-migration
whenToUse: Creating or reviewing database migrations
model: opus
tools:
  - Read
  - Grep
  - Glob
  - Bash
---

You are a database migration specialist. When creating migrations:
1. Check existing migration numbering
2. Verify no conflicting migrations
3. Generate both up and down migrations
4. Test with dry-run before applying
```

### Technique 5: Memory-Driven Continuity
```markdown
<!-- In CLAUDE.md -->
## First Action Every Session
1. Read shared_state.md (source of truth)
2. Read tasks/lessons.md (mistake prevention)
3. Review recent git log for context
```

## Prompt Engineering for Claude Code

### What Works (from source analysis)

1. **Be specific, not vague**: Claude Code's system prompt says "terse command-style prompts produce shallow, generic work"

2. **Front-load context**: The system prompt tells agents to "brief like a smart colleague who just walked into the room"

3. **Explain WHY**: The prompt says "explain what you're trying to accomplish and WHY" — not just what to do

4. **Scope boundaries**: "Be specific about scope: what's in, what's out, what another agent is handling"

5. **Don't delegate understanding**: "Don't write 'based on your findings, fix the bug.' Write prompts that prove you understood: include file paths, line numbers, what specifically to change."

### What Doesn't Work

1. **Over-engineering prompts**: Claude Code already has extensive system prompts. Adding redundant instructions wastes context.

2. **Fighting the defaults**: Instead of adding "don't do X" for things Claude already avoids, focus on positive instructions.

3. **Micro-managing tool usage**: Claude Code has sophisticated tool selection logic. Prescribing specific tools usually reduces quality.

## Performance Optimization Techniques

### 1. Leverage Prompt Caching
- Keep CLAUDE.md stable — changes bust the cache
- The system prompt split (static/dynamic) means most of the prompt is cached globally
- Agent lists were moved to attachments specifically to avoid busting the cache

### 2. Use Subagents for Parallel Work
```
// Good: parallel research
Agent({ subagent_type: "Explore", prompt: "Find all API endpoints" })
Agent({ subagent_type: "Explore", prompt: "Find all database models" })
// Both run concurrently

// Bad: serial research
"First find all API endpoints, then find all database models"
```

### 3. Fork Subagents for Context Management
When fork mode is available:
- Fork for research that would pollute your context
- Fork for implementation that produces verbose tool output
- Don't fork for quick lookups (overhead > benefit)

### 4. Use Plan Mode for Complex Tasks
Plan mode is read-only — prevents premature implementation:
```
/plan → explore and design → exit plan mode → implement
```

### 5. Token Budget for Large Tasks
```
"+500k" or "spend 2M tokens" — tells Claude to keep working until budget is used
```

## Community-Discovered Patterns

### The Orchestrator Pattern
```markdown
<!-- CLAUDE.md -->
## Orchestrator Rules
- I am the orchestrator. I NEVER write code myself.
- ALL work goes through subagents — no exceptions.
- If I catch myself writing more than 3 lines of analysis, STOP and spawn a subagent.
- NEVER fix and verify with same agent — spawn separate QA agent.
```

### The Lesson Loop Pattern
```markdown
<!-- CLAUDE.md -->
## Self-Improvement
- After ANY correction from user: update tasks/lessons.md
- Write rules that prevent the same mistake
- Review lessons at session start
```

### The Verification Gate Pattern
```markdown
<!-- CLAUDE.md -->
## Verification Before Done
- Never mark a task complete without proving it works
- Run tests, check logs, demonstrate correctness
- Ask yourself: "Would a staff engineer approve this?"
```

### The Shared State Pattern
```markdown
<!-- shared_state.md -->
## Current Sprint
- Goal: Ship v2.0 by 2026-04-15
- Blocked: Waiting on API team for auth changes

## Active PRs
- #142: Add user search (in review)
- #145: Fix pagination bug (ready to merge)
```

## Hidden Features Worth Knowing

1. **`/fast` toggle** — Same Opus model, faster output (not a different model!)
2. **`! command`** — Run a shell command directly from the prompt
3. **ToolSearch** — Deferred tools aren't loaded until searched for, saving context
4. **Scratchpad** — Per-session temp directory for Claude to write working files
5. **Worktrees** — Agents can work in isolated git worktrees
6. **Skill system** — `/commit`, `/simplify`, `/verify` are skills, not commands
7. **MCP servers** — Can extend Claude Code with any MCP-compatible server
8. **Background tasks** — Long-running bash commands run in background, notification on completion

## What the Source Reveals About Best Practices

### From the Code Style Instructions:
> "Three similar lines of code is better than a premature abstraction."

### From the Actions Section:
> "A user approving an action once does NOT mean they approve it in all contexts."

### From the Agent Prompt:
> "Never delegate understanding."

### From the Output Efficiency:
> "If you can say it in one sentence, don't use three."

### From the Doing Tasks Section:
> "Don't retry the identical action blindly, but don't abandon a viable approach after a single failure either."
