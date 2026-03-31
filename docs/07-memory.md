# Memory System

## Overview

Claude Code has a persistent memory system built from three layers:
1. **CLAUDE.md files** — Project-level instructions
2. **Auto-memory** (`~/.claude/projects/<hash>/memory/`) — Persistent cross-session memory
3. **Memory attachments** — Injected into conversations as needed

## CLAUDE.md System

### Discovery Order
CLAUDE.md files are discovered by walking up from the working directory:

```
1. ~/.claude/CLAUDE.md                          (global user instructions)
2. ~/.claude/projects/<project-hash>/CLAUDE.md  (project-specific user instructions)
3. <project-root>/CLAUDE.md                     (project instructions, committed)
4. <project-root>/.claude/CLAUDE.md             (project instructions, gitignored)
5. Additional directories (--add-dir)
```

### Priority
- Instructions in CLAUDE.md override defaults
- Project CLAUDE.md can override global CLAUDE.md
- CLAUDE.md content is cached for the session (`setCachedClaudeMdContent`)

### Content Injection
CLAUDE.md content is injected into `getUserContext()`:
```typescript
const claudeMd = getClaudeMds(filterInjectedMemoryFiles(await getMemoryFiles()))
return { claudeMd, currentDate: `Today's date is ${date}` }
```

This becomes part of the user context, prepended to the conversation.

### Disabling CLAUDE.md
- `CLAUDE_CODE_DISABLE_CLAUDE_MDS=true` — Hard off
- `--bare` mode — Skips auto-discovery, but honors `--add-dir`

## Auto-Memory System (`memdir/`)

### Structure
```
~/.claude/projects/<project-hash>/memory/
├── MEMORY.md           # Index file (≤200 lines, ≤25KB)
├── user_role.md        # Memory file with frontmatter
├── feedback_testing.md
├── project_goals.md
├── reference_slack.md
└── ...
```

### Memory File Format
```markdown
---
name: User Role
description: User is a senior backend engineer focused on Go services
type: user
---

Content of the memory...
```

### Memory Types
1. **user** — Role, preferences, knowledge level
2. **feedback** — Corrections and validated approaches
3. **project** — Ongoing work, goals, decisions
4. **reference** — Pointers to external systems

### MEMORY.md Index
- One line per memory, under ~150 chars
- Format: `- [Title](file.md) — one-line hook`
- Max 200 lines — truncated after that
- Always loaded into conversation context
- Has NO frontmatter (it's an index, not a memory)

### Memory Prompt (`memdir.ts`)

The memory prompt is loaded via `loadMemoryPrompt()` and includes:
- Memory type definitions with examples
- What NOT to save (code patterns, git history, debugging solutions)
- How to save (frontmatter + MEMORY.md update)
- When to access memories
- Trust-but-verify guidance

### Key Constraints
```
MEMORY.md max: 200 lines, 25KB
Each memory: own file with frontmatter
Never write content directly into MEMORY.md
Check for existing memory before creating new
Organize semantically, not chronologically
```

### Memory Relevance
The system includes `findRelevantMemories.ts` for finding memories relevant to the current context. Memories can be prefetched at turn start.

### Trust-but-Verify Pattern

From the memory prompt:
```
"A memory that names a specific function, file, or flag is a claim
that it existed WHEN THE MEMORY WAS WRITTEN. It may have been renamed,
removed, or never merged. Before recommending it:
- If the memory names a file path: check the file exists.
- If the memory names a function or flag: grep for it.
'The memory says X exists' is not the same as 'X exists now.'"
```

## Context Injection Flow

```
Session Start
    ↓
getSystemContext() [memoized]
├── Git status (branch, status, recent commits)
└── Cache breaker (ant-only debugging)
    ↓
getUserContext() [memoized]
├── CLAUDE.md files (all discovered)
├── Memory files (auto-memory)
└── Current date
    ↓
prependUserContext() — adds to system prompt
appendSystemContext() — adds to system prompt
    ↓
System prompt sent with each API call
```

### Attachment Messages

Some context is injected as attachment messages (not system prompt):
- Agent listing (to avoid busting prompt cache)
- Skill discovery results
- MCP instructions (when delta mode enabled)
- Memory files (nested memory attachments)

This keeps the system prompt static and cacheable while still providing dynamic context.

## Team Memory (Feature-Gated: TEAMMEM)

For team/multi-agent scenarios:
- `teamMemPaths.ts` — Paths for team-level memory
- `teamMemPrompts.ts` — Team memory prompt templates
- Shared across team members/agents

## Memory Scan

`memoryScan.ts` — Scans memory files for relevance:
- Used during prefetch
- Checks memory age (`memoryAge.ts`)
- Filters stale or irrelevant memories
