# Key Engineering Patterns & Lessons

## Architectural Patterns in Claude Code

### 1. Section Registry Pattern (`systemPromptSections.ts`)

System prompt sections are registered, not concatenated:
```typescript
systemPromptSection('session_guidance', () => getSessionSpecificGuidanceSection())
systemPromptSection('memory', () => loadMemoryPrompt())
```

Benefits:
- Sections are independently cacheable
- Can be toggled by feature gates
- `DANGEROUS_uncachedSystemPromptSection()` marks sections that change between turns

### 2. Build-Time Dead Code Elimination

```typescript
import { feature } from 'bun:bundle'

const module = feature('KAIROS') ? require('./kairos.js') : null
```

This isn't just a runtime check — Bun eliminates the entire code path at build time if the feature is disabled. The external build has significantly less code than the internal (ant) build.

### 3. Streaming Tool Executor

Tools don't run one at a time. `StreamingToolExecutor`:
1. Partitions tool calls by `isConcurrencySafe()`
2. Runs safe tools in parallel
3. Runs unsafe tools sequentially
4. Handles progress events, cancellation, and errors for each

### 4. Content Replacement (Disk Offload)

When tool results exceed `maxResultSizeChars`:
```
Full result → hash → write to ~/.claude/.tool-results/<hash>.txt
Model sees → preview + file path reference
```

Content-addressed storage means identical results are deduplicated.

### 5. Two-Tier State Management

- **Global State** (`bootstrap/state.ts`): Session-wide constants, initialized once
- **App State** (Zustand store): Dynamic REPL state, React-subscribed

Why two? Global state is synchronous and accessed from deep call stacks where React context isn't available.

### 6. Auto-Classifier for Permissions

The `yoloClassifier.ts` evaluates tool safety:
- Takes the tool name, input, and context
- Returns approve/deny/ask
- Uses the auto-mode classifier transcript (tool's `toAutoClassifierInput()`)
- Has denial tracking to prevent infinite deny loops

### 7. Prompt Cache Optimization

The system prompt is split at `SYSTEM_PROMPT_DYNAMIC_BOUNDARY`:
```
Static content (70%) → scope: 'global' → cached across all users
Dynamic content (30%) → scope: 'session' → per-user cache
```

Moving the agent list to attachment messages saved 10.2% of fleet cache_creation tokens.

## Observed Internal Patterns

### Model-Launch Markers
```typescript
// @[MODEL LAUNCH]: Update the latest frontier model.
const FRONTIER_MODEL_NAME = 'Claude Opus 4.6'

// @[MODEL LAUNCH]: Update comment writing for Capybara
```

Internal comments mark what needs updating for each new model release.

### USER_TYPE Gating
```typescript
if (process.env.USER_TYPE === 'ant') {
  // Anthropic-employee-only behavior
}
```

Ant-internal builds get:
- Extra system prompt sections (output communication style)
- Comment writing guidance tuned for current model
- False-claims mitigation instructions
- Verification agent
- `/issue` and `/share` slash commands
- Undercover mode (strips model names from prompts)

### GrowthBook Feature Flags
```typescript
getFeatureValue_CACHED_MAY_BE_STALE('tengu_tool_pear', false)
```

A/B tests are controlled via GrowthBook (experimentation platform):
- `tengu_amber_stoat` — Explore/Plan agents enabled
- `tengu_hive_evidence` — Verification agent
- `tengu_agent_list_attach` — Agent list in attachments
- `tengu_tool_pear` — Strict tool mode

### Ablation Baseline
```typescript
if (feature('ABLATION_BASELINE') && process.env.CLAUDE_CODE_ABLATION_BASELINE) {
  // Disable: thinking, compact, auto-memory, background tasks
  // For measuring baseline impact
}
```

### Undercover Mode
```typescript
if (isUndercover()) {
  // Strip ALL model names/IDs from system prompt
  // Prevents internal model names from leaking
}
```

## Performance Optimization Lessons

### 1. Startup Time
- Every import is dynamic (`await import()`)
- Fast paths exit before loading heavy modules
- Profile checkpoints throughout (`profileCheckpoint()`)
- Feature gates eliminate code at build time

### 2. Memory Management
- Task output → disk (not memory)
- Large tool results → disk with content-addressed dedup
- LRU file cache (`FileStateCache`) for read operations
- MEMORY.md capped at 200 lines / 25KB

### 3. API Efficiency
- Prompt caching with static/dynamic split
- Micro-compaction strips non-essential blocks between turns
- Auto-compaction before hitting token limit
- Message normalization removes local-only fields

### 4. UI Performance
- Custom Ink fork with yoga layout engine
- Lazy component loading
- Animation frame hook for smooth rendering
- Virtual message list for scrollback

## Key Numeric Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| MAX_STATUS_CHARS | 2000 | Git status truncation |
| MAX_ENTRYPOINT_LINES | 200 | MEMORY.md line cap |
| MAX_ENTRYPOINT_BYTES | 25000 | MEMORY.md byte cap |
| EXPLORE_AGENT_MIN_QUERIES | 3 | Min queries before using Explore agent |
| ESCALATED_MAX_TOKENS | (dynamic) | Bumped when output exceeds 200K |

## Lessons from Claude Code's Design

### 1. Defaults Should Be Safe
Tools default to `isReadOnly: false`, `isConcurrencySafe: false`, `isDestructive: false`. Security-relevant tools must explicitly override.

### 2. Cache Everything, But Track Staleness
Memoized functions with explicit cache clearing when assumptions change (`setSystemPromptInjection()` clears context caches).

### 3. Make Things Testable
`QueryDeps` pattern — every external dependency is injectable. Tests never hit real APIs.

### 4. Measure Before Optimizing
Profile checkpoints throughout boot sequence. Feature flags with A/B testing for every behavioral change.

### 5. Fail Loudly, Not Silently
`logAntError`, `logForDiagnosticsNoPII`, `logForDebugging` — different log levels for different audiences. Never swallow errors.

### 6. Separation of Concerns for Context
System prompt (static) vs. user context (CLAUDE.md) vs. system context (git) vs. attachments (dynamic). Each has a different update frequency and caching strategy.
