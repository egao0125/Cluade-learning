# Claude Code Architecture

## Overview

Claude Code is a TypeScript application built with Bun, React (Ink for terminal UI), and the Anthropic API. It operates as both an interactive REPL and a headless SDK/agent engine.

## Directory Structure

```
src/
├── entrypoints/           # CLI bootstrap, SDK entry, MCP servers
│   ├── cli.tsx            # Bootstrap entry — fast paths before full import
│   └── init.ts            # Memoized initialization pipeline
├── main.tsx               # ~5000 lines — CLI arg parsing, auth, REPL launch
├── query.ts               # ~1500 lines — The agentic loop (prompt→stream→tools→repeat)
├── QueryEngine.ts         # ~1000 lines — Headless query processor for SDK
├── Tool.ts                # Core Tool protocol & ToolUseContext
├── Task.ts                # Background task abstraction
├── commands.ts            # Command registry (100+ slash commands)
├── context.ts             # System & user context builders
├── constants/
│   ├── prompts.ts         # System prompt construction (THE key file)
│   ├── systemPromptSections.ts  # Section registry pattern
│   └── cyberRiskInstruction.ts  # Security instruction (Safeguards team owned)
├── tools/                 # 40+ tool implementations
│   ├── AgentTool/         # Subagent spawning
│   ├── BashTool/          # Shell execution
│   ├── FileEditTool/      # File editing
│   ├── FileReadTool/      # File reading
│   ├── FileWriteTool/     # File writing
│   ├── GlobTool/          # File search
│   ├── GrepTool/          # Content search
│   ├── WebFetchTool/      # HTTP fetching
│   ├── WebSearchTool/     # Web search
│   ├── ToolSearchTool/    # Deferred tool discovery
│   └── ...
├── commands/              # 100+ slash command implementations
├── components/            # 146 React (Ink) UI components
├── hooks/                 # 87 React hooks for REPL features
├── services/
│   ├── api/               # Anthropic API client & streaming
│   ├── mcp/               # MCP server integration
│   ├── compact/           # 4 compaction strategies
│   ├── analytics/         # Telemetry & feature gates (GrowthBook)
│   ├── lsp/               # LSP server integration
│   └── plugins/           # Plugin loading
├── skills/                # Bundled skills (verify, simplify, commit, etc.)
├── state/                 # Zustand store for REPL state
├── memdir/                # Auto-memory system
├── ink/                   # Custom Ink fork (React→terminal renderer)
├── utils/                 # 331 utility modules
└── types/                 # Shared TypeScript types
```

## Boot Sequence

### 1. Bootstrap (`entrypoints/cli.tsx`)

```
process.argv → fast-path checks → dynamic import main.tsx
```

**Fast paths** (zero full-module loading):
- `--version` → print version, exit
- `--dump-system-prompt` → render system prompt, exit (ant-only)
- `--claude-in-chrome-mcp` → Chrome extension MCP server
- `--computer-use-mcp` → Computer use MCP server
- `--daemon-worker` → Daemon supervisor
- `ps`, `logs`, `attach`, `kill` → Background session management

**Optimization**: Every import is `await import()` — nothing loads unless needed.

### 2. Initialization (`entrypoints/init.ts`)

Memoized — runs exactly once:
1. Config validation & env vars
2. CA certs & proxy setup
3. Graceful shutdown handlers
4. First-party event logging (OpenTelemetry)
5. OAuth account info
6. Policy limits & remote settings
7. Git repo detection
8. LSP server manager
9. Scratchpad directory
10. Telemetry (deferred after trust dialog)

### 3. Main (`main.tsx`)

```
CLI args (commander.js) → analytics → auth → permissions → plugins → skills → MCP servers → REPL
```

Key operations:
- Parse 50+ CLI flags
- Set up cost tracking & usage limits
- Load plugins from `~/.claude/plugins/`
- Register bundled skills
- Connect MCP servers (async, non-blocking)
- Launch REPL or run in print/SDK mode

### 4. REPL (`screens/REPL.tsx`)

A massive React component (~2000+ lines) managing:
- Message history & persistence
- Query submission & streaming
- UI state, permissions, cost tracking
- Background tasks & teammate management
- Message selection & scrollback
- Voice integration

## Core Abstractions

### Tool Protocol (`Tool.ts`)

Every tool implements:
```typescript
type Tool = {
  name: string
  inputSchema: ZodSchema       // Input validation
  call(args, context, canUseTool, parentMessage, onProgress)  // Execution
  description(input, options)   // Dynamic description
  prompt(options)               // Prompt text for model
  checkPermissions(input, ctx)  // Permission check
  isReadOnly(input)             // Read-only flag
  isConcurrencySafe(input)      // Can run in parallel
  maxResultSizeChars: number    // Disk offload threshold
  // ... 30+ more methods for rendering, permissions, etc.
}
```

`ToolUseContext` is the dependency injection container — 50+ fields including:
- `abortController` — cancellation
- `readFileState` — LRU file cache
- `getAppState/setAppState` — Zustand store access
- `setToolJSX` — UI rendering
- `messages` — conversation history
- `toolDecisions` — hook decisions cache

### Task System (`Task.ts`)

Background tasks with typed IDs:
```
'b' → local_bash
'a' → local_agent
'r' → remote_agent
't' → in_process_teammate
'w' → local_workflow
'm' → monitor_mcp
'd' → dream
```

Output written to disk (`~/.claude/.tasks/`) to avoid memory explosion.

### Feature Gates (`bun:bundle`)

```typescript
import { feature } from 'bun:bundle'

if (feature('KAIROS')) {
  // Dead-code eliminated in builds where KAIROS is disabled
}
```

Known feature gates:
- `KAIROS` / `KAIROS_BRIEF` — Proactive/autonomous features
- `COORDINATOR_MODE` — Multi-agent coordination
- `DAEMON` / `BRIDGE_MODE` — Background daemon
- `VOICE_MODE` — Voice input
- `HISTORY_SNIP` — History compaction
- `REACTIVE_COMPACT` — Proactive compaction
- `CONTEXT_COLLAPSE` — Context optimization
- `EXPERIMENTAL_SKILL_SEARCH` — Skill discovery
- `VERIFICATION_AGENT` — Adversarial verification
- `TOKEN_BUDGET` — Token budget mode
- `ABLATION_BASELINE` — For A/B testing

## Key Patterns

### 1. Lazy Loading
All heavy modules use dynamic `require()` / `import()` to minimize startup time.

### 2. Testable Dependency Injection
`QueryDeps` lets tests swap API calls, compaction, UUID generation.

### 3. Disk Offloading
Large tool results stored to `~/.claude/.tool-results/` — model gets a preview + file path.

### 4. Cache-Aware Prompt Construction
System prompt split into static (globally cacheable) and dynamic (session-specific) sections with `SYSTEM_PROMPT_DYNAMIC_BOUNDARY`.

### 5. Memoization
`context.ts` memoizes git status, system context, and user context for the session duration.
