# Permission & Security Model

## Permission Modes

Three modes control how tool execution is approved:

### 1. `default` Mode
- Each tool call shows a permission dialog
- User approves or denies individually
- Safest mode, most interactive

### 2. `auto` Mode
- A classifier pre-approves likely-safe tool calls
- Uses `yoloClassifier.ts` to evaluate safety
- Falls back to prompting if classifier is uncertain
- Has denial tracking — if too many denials, falls back to manual prompting
- Dangerous patterns still blocked

### 3. `bypass` Mode
- Skips all permission checks
- Requires explicit opt-in
- NOT available on remote/CCR environments
- Used for trusted automation

## Permission Context

```typescript
type ToolPermissionContext = {
  mode: PermissionMode  // 'default' | 'auto' | 'bypass'
  additionalWorkingDirectories: Map<string, AdditionalWorkingDirectory>
  alwaysAllowRules: ToolPermissionRulesBySource   // Auto-approve patterns
  alwaysDenyRules: ToolPermissionRulesBySource     // Block patterns
  alwaysAskRules: ToolPermissionRulesBySource      // Always prompt
  isBypassPermissionsModeAvailable: boolean
  isAutoModeAvailable?: boolean
  strippedDangerousRules?: ToolPermissionRulesBySource
  shouldAvoidPermissionPrompts?: boolean  // Background agents
  awaitAutomatedChecksBeforeDialog?: boolean  // Coordinator workers
  prePlanMode?: PermissionMode  // Restore after plan mode
}
```

## Permission Rules

Configured in settings or CLAUDE.md:

```json
{
  "alwaysAllowRules": {
    "BashTool": [
      { "prefix": ["npm test", "git status", "ls"] }
    ]
  },
  "alwaysDenyRules": {
    "BashTool": [
      { "prefix": ["rm -rf /", "dd if=/dev/zero", "curl | sh"] }
    ]
  }
}
```

### Rule Matching
- **Tool-level**: All invocations of a tool
- **Prefix pattern**: Match command prefix (`git clone *`)
- **Wildcard**: `npm *` matches any npm command

## Permission Check Flow

```
Tool invoked
    ↓
1. validateInput() — tool-specific schema validation
    ↓
2. pre_tool_use hooks — external hooks can:
    - approve (skip remaining checks)
    - reject (block with message)
    - modify (change tool input)
    ↓
3. checkPermissions() — tool-specific logic
    ↓
4. Match against alwaysDenyRules → block
    ↓
5. Match against alwaysAllowRules → allow
    ↓
6. Match against alwaysAskRules → prompt
    ↓
7. If auto mode: run classifier → allow/deny/ask
    ↓
8. If default mode: show permission dialog
    ↓
9. User approves/denies
    ↓
10. If denied: permission_denied hook fires
```

## The Trust Dialog

First-run experience:
1. User launches Claude Code for the first time
2. Trust dialog appears — ToS acceptance required
3. Until accepted, NO tools execute
4. Hooks skip if trust not accepted

## Denial Tracking

```typescript
type DenialTrackingState = {
  denialCount: number
  // When denials exceed threshold, fall back to prompting
}
```

In auto mode, if the classifier keeps denying and the model keeps retrying, the system falls back to manual prompting to prevent infinite loops.

## Plan Mode

When plan mode is active:
- Permission mode is stored in `prePlanMode`
- Mode switches to read-only (no write tools available)
- On exit, original mode is restored

## Background Agent Permissions

Background agents (subagents, teammates) with `shouldAvoidPermissionPrompts: true`:
- Permission prompts are auto-denied
- They can only use tools that are always-allowed
- Prevents blocking on UI prompts that no one can answer

## File System Safety

- Working directory is tracked and enforced
- Additional working directories must be explicitly configured
- Scratchpad directory is per-session and sandboxed
- Worktrees provide full git isolation

## Security Instruction (Owned by Safeguards Team)

The `CYBER_RISK_INSTRUCTION` in `cyberRiskInstruction.ts`:
- Owned by Safeguards team (David Forsythe, Kyla Guru)
- DO NOT MODIFY without team review
- Defines boundary between defensive security help and harmful activities
- Allows: CTF, pentesting, defensive security, educational
- Refuses: DoS, mass targeting, supply chain, detection evasion
