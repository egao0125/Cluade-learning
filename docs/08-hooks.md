# Hook System

## Overview

Claude Code has a comprehensive hook system that allows external shell commands to execute at key lifecycle points. Hooks are configured in settings and can approve, reject, or modify tool execution.

## Hook Types

| Hook | When | Can Modify |
|------|------|-----------|
| `setup` | Initial setup validation | No |
| `session_start` | Before first turn | No |
| `session_end` | On exit | No |
| `pre_tool_use` | Before tool runs | Yes — approve/reject/modify input |
| `post_tool_use` | After tool succeeds | No |
| `post_tool_use_failure` | After tool error | No |
| `permission_denied` | User denies permission | No |
| `pre_compact` | Before compaction | No |
| `post_compact` | After compaction | No |
| `stop` | When model outputs stop reason | No |
| `stop_failure` | When stop fails | No |
| `task_created` | Background task starts | No |
| `task_completed` | Background task ends | No |
| `config_changed` | Settings.json updates | No |
| `cwd_changed` | Directory changes | No |
| `file_changed` | Watched file updates | No |
| `instructions_loaded` | CLAUDE.md loaded | No |
| `subagent_start` | Subagent spawned | No |
| `subagent_stop` | Subagent finished | No |
| `teammate_idle` | Teammate becomes idle | No |
| `notification` | OS notification sent | No |

## Hook Configuration

In `~/.claude/settings.json` or `.claude/settings.json`:

```json
{
  "hooks": {
    "pre_tool_use": [
      {
        "command": "/path/to/my-hook.sh",
        "if": "Bash(git *)"
      }
    ],
    "post_tool_use": [
      {
        "command": "/path/to/logger.sh"
      }
    ]
  }
}
```

### Hook Input (via stdin)

Hooks receive JSON input via stdin:

```json
{
  "tool_name": "Bash",
  "tool_input": {
    "command": "git status"
  },
  "session_id": "abc123",
  "agent_id": null
}
```

### Hook Output (JSON)

Hooks return JSON output:

```json
{
  "decision": "approve",
  "reason": "Git commands are always safe"
}
```

Or to reject:
```json
{
  "decision": "reject",
  "reason": "This command is blocked by policy"
}
```

Or to modify input:
```json
{
  "decision": "approve",
  "updatedInput": {
    "command": "git status --short"
  }
}
```

## Hook Execution Flow

```
1. Check if trust dialog accepted → skip if not
2. Find matching hooks for event type
3. For pre_tool_use: check `if` condition against tool name + input
4. Spawn hook script in project root
5. Pass JSON input via stdin
6. Parse JSON output
7. Handle result:
   - approve → continue execution
   - reject → block with message
   - modify → update tool input
8. Log hook duration & errors
```

## The `if` Condition

Pattern matching for selective hook execution:

```json
{
  "if": "Bash(git *)"        // Bash tool, commands starting with "git "
  "if": "FileEdit"            // Any FileEdit tool invocation
  "if": "Bash(npm install *)" // Only npm install commands
}
```

The tool's `preparePermissionMatcher()` method handles pattern matching. For BashTool, this matches against the command prefix.

## Post-Sampling Hooks

After the model produces output (before tool execution):
```typescript
executePostSamplingHooks(assistantMessage)
```

These can inspect what the model wants to do before any tools run.

## Stop Hooks

When the model's stop reason is `end_turn`:
```typescript
handleStopHooks(messages, stopReason)
```

If a stop hook fails, `executeStopFailureHooks()` fires.

## User Prompt Submit Hook

Special hook that runs when the user submits a prompt:
```
<user-prompt-submit-hook>
```

Claude treats this feedback as coming from the user.

## Practical Hook Examples

### Auto-approve read-only commands
```json
{
  "hooks": {
    "pre_tool_use": [{
      "command": "echo '{\"decision\":\"approve\"}'",
      "if": "Bash(git log *)"
    }]
  }
}
```

### Log all tool usage
```json
{
  "hooks": {
    "post_tool_use": [{
      "command": "/path/to/log-tool-use.sh"
    }]
  }
}
```

### Block dangerous patterns
```json
{
  "hooks": {
    "pre_tool_use": [{
      "command": "/path/to/security-check.sh",
      "if": "Bash(curl *)"
    }]
  }
}
```
