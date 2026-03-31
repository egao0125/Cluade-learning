# Tool System

## Tool Protocol

Every tool is built using `buildTool()` which fills in defaults:

```typescript
buildTool({
  name: 'Read',
  inputSchema: z.object({ file_path: z.string(), ... }),
  call(args, context, canUseTool, parentMessage, onProgress) { ... },
  description(input, options) { ... },
  prompt(options) { ... },
  checkPermissions(input, ctx) { ... },
  isReadOnly(input) { return true },
  isConcurrencySafe(input) { return true },
  maxResultSizeChars: Infinity, // Never persist to disk
  // ... rendering methods
})
```

### Defaults (fail-closed):
- `isEnabled` → `true`
- `isConcurrencySafe` → `false` (assume NOT safe)
- `isReadOnly` → `false` (assume writes)
- `isDestructive` → `false`
- `checkPermissions` → `{ behavior: 'allow' }` (defer to general system)

## All Built-in Tools

### File Operations
| Tool | Purpose | Read-only | Concurrent |
|------|---------|-----------|------------|
| FileReadTool | Read files (text, images, PDFs, notebooks) | Yes | Yes |
| FileEditTool | String replacement edits | No | No |
| FileWriteTool | Create/overwrite files | No | No |
| GlobTool | File pattern matching | Yes | Yes |
| GrepTool | Content search (ripgrep) | Yes | Yes |
| NotebookEditTool | Jupyter notebook cell editing | No | No |

### Execution
| Tool | Purpose | Read-only | Concurrent |
|------|---------|-----------|------------|
| BashTool | Shell command execution | Depends | Depends |
| PowerShellTool | Windows PowerShell | Depends | Depends |
| REPLTool | Interactive REPL sessions | No | No |

### Agent & Task
| Tool | Purpose |
|------|---------|
| AgentTool | Spawn subagents (built-in or custom) |
| SendMessageTool | Continue/message existing agents |
| TaskCreateTool | Create background tasks |
| TaskGetTool | Get task status |
| TaskListTool | List all tasks |
| TaskOutputTool | Read task output |
| TaskStopTool | Kill a task |
| TaskUpdateTool | Update task status |
| TodoWriteTool | Legacy task management |

### Planning & Workflow
| Tool | Purpose |
|------|---------|
| EnterPlanModeTool | Switch to plan mode (read-only) |
| ExitPlanModeTool | Exit plan mode |
| EnterWorktreeTool | Create git worktree |
| ExitWorktreeTool | Leave worktree |
| SleepTool | Wait (for polling, etc.) |

### External
| Tool | Purpose |
|------|---------|
| WebFetchTool | HTTP fetch (URLs) |
| WebSearchTool | Web search |
| MCPTool | MCP server tool calls |
| ListMcpResourcesTool | List MCP resources |
| ReadMcpResourceTool | Read MCP resource |

### Meta
| Tool | Purpose |
|------|---------|
| ToolSearchTool | Discover deferred tools |
| SkillTool | Execute skills (/commit, /review-pr) |
| AskUserQuestionTool | Ask user for input |
| ConfigTool | Read/write settings |
| RemoteTriggerTool | Trigger remote agents |
| ScheduleCronTool | Schedule cron jobs |

## Tool Deferred Loading (ToolSearch)

Not all tools are loaded into the prompt immediately. Tools with `shouldDefer: true` are sent to the API with `defer_loading: true` — the model sees only the name. To use them, the model must first call `ToolSearch` to fetch their full schema.

Tools with `alwaysLoad: true` are never deferred.

This reduces the initial prompt size significantly — important for latency and cost.

## Streaming Tool Execution

```typescript
// StreamingToolExecutor runs tools concurrently
const executor = new StreamingToolExecutor(tools, context)
const results = await executor.run(toolUseBlocks)
```

Tools run in parallel if `isConcurrencySafe(input)` returns true.

Non-concurrent tools run sequentially with context modification:
```typescript
contextModifier?: (context: ToolUseContext) => ToolUseContext
```

## Tool Result Budget

Large tool results are automatically stored to disk:
```
~/.claude/.tool-results/<contentHash>.txt
```

The model receives a preview:
```
<result-too-large>
Result stored at: /path/to/result.txt
Size: 45.2KB
Preview: (first 200 chars)
</result-too-large>
```

Tools can set `maxResultSizeChars`:
- `Infinity` for FileRead (self-bounds via its own limits)
- Default threshold for most tools

## Permission Lifecycle

```
1. Tool called by model
2. validateInput() — schema + context validation
3. Hook: pre_tool_use — external hooks can approve/reject/modify
4. checkPermissions() — tool-specific permission logic
5. General permission system — mode + rules + auto-classify
6. If not auto-approved → user prompt
7. Tool executes
8. Hook: post_tool_use — external hooks see result
```

## MCP Tool Integration

MCP tools are registered alongside built-in tools:
```typescript
// Naming: mcp__<serverName>__<toolName>
// Or with CLAUDE_AGENT_SDK_MCP_NO_PREFIX: just <toolName>
```

MCP tools have `isMcp: true` and `mcpInfo: { serverName, toolName }`.

They support:
- `alwaysLoad` via `_meta['anthropic/alwaysLoad']`
- Elicitation flow for auth (error code -32042)
- Channel permissions (per-server approval)

## Tool Summary Generation

After tool execution, summaries can be generated:
```typescript
generateToolUseSummary(toolUse, result) → "Read src/foo.ts (250 lines)"
```

These appear in the UI as collapsed views and are used for micro-compaction.
