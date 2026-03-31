# The Query Loop — Claude Code's Core Engine

## Overview

The query loop in `query.ts` is the heart of Claude Code. It implements the agentic loop:
**prompt → stream response → execute tools → add results → repeat**

## Query Flow

```
User submits message
    ↓
handlePromptSubmit()
    ↓
Build system prompt (prompts.ts → getSystemPrompt())
    ↓
Inject system context (git status, cache breaker)
    ↓
Inject user context (CLAUDE.md, current date, memory)
    ↓
Normalize messages for API
    ↓
query() {
  for (turn = 0; turn < maxTurns; turn++) {

    // 1. Check if compaction needed
    if (nearTokenLimit) autoCompact()

    // 2. Prefetch relevant memories & skills
    startRelevantMemoryPrefetch()

    // 3. Stream from Anthropic API
    for await (event of streamMessages()) {
      // Accumulate text blocks
      // Accumulate tool_use blocks
      // Handle thinking blocks
      yield StreamEvents to UI
    }

    // 4. Post-sampling hooks
    executePostSamplingHooks()

    // 5. Run tools (concurrent when safe)
    results = StreamingToolExecutor.run(toolUses)

    // 6. Apply tool result budget (disk offload if too large)
    applyToolResultBudget(results)

    // 7. Add tool results as user messages
    messages.push(createUserMessage({
      content: toolResults.map(r => ({
        type: 'tool_result',
        tool_use_id: r.id,
        content: r.result
      }))
    }))

    // 8. Check stop reason
    if (stopReason === 'end_turn') → handleStopHooks() → break
    if (stopReason === 'tool_use') → continue
    if (stopReason === 'max_tokens') → extend or break
  }
}
```

## Key Mechanisms

### Token Budget Management

```typescript
const budgetTracker = createBudgetTracker(taskBudget)

// Each turn:
checkTokenBudget(budgetTracker, currentUsage)
// If over budget → stop
// If near budget → signal model to wrap up
```

When `max_tokens` is hit, Claude Code:
1. Checks if output was >200K tokens (escalated mode)
2. If so, bumps `ESCALATED_MAX_TOKENS` for next turn
3. Adds a "continue" message and loops

### Compaction Strategies

4 strategies, from lightest to heaviest:

#### 1. Micro-Compact (`microCompact.ts`)
- Strips non-essential blocks from old messages
- Removes thinking blocks, tool use summaries
- Lightweight, always-on

#### 2. Auto-Compact (`autoCompact.ts`)
- Triggered when approaching token limit
- Summarizes conversation history
- Preserves recent messages + compaction boundary

#### 3. Snip Compact (`snipCompact.ts`, feature-gated)
- More aggressive history trimming
- Snips old message ranges

#### 4. Full Compact (`compact.ts`)
- Full conversation compaction
- Creates a summary, replaces all old messages
- Preserves file state and key context

#### 5. Reactive Compact (`reactiveCompact.ts`, feature-gated)
- Proactive compaction before hitting limits

### Message Normalization

Before sending to API:
```typescript
normalizeMessagesForAPI(messages)
// - Strips local-only fields (uuid, toolUseResult, etc.)
// - Removes system local messages
// - Handles content replacement (disk-offloaded results)
// - Strips signature blocks
// - Filters duplicate memory attachments
```

### Error Recovery

```typescript
// Prompt too long → compact and retry
if (isPromptTooLongMessage(error)) {
  autoCompact()
  continue
}

// Retryable API errors → exponential backoff
if (isRetryable(error)) {
  await withRetry(() => streamMessages())
}

// Fallback triggered → try different model
if (error instanceof FallbackTriggeredError) {
  // Handle model fallback
}
```

### Tool Result Storage

Large results get stored to disk:
```typescript
// If result > maxResultSizeChars:
const path = generateToolResultPath(contentHash)
writeFile(path, fullResult)

// Model sees:
buildLargeToolResultMessage(path, sizeBytes)
// → "Result stored at /path (45KB). Preview: ..."
```

Content hash ensures deduplication — same result doesn't create multiple files.

### Streaming Tool Execution

```typescript
class StreamingToolExecutor {
  // Groups tools by concurrency safety
  // Runs concurrent-safe tools in parallel
  // Runs non-concurrent tools sequentially
  // Emits progress events
  // Handles cancellation via AbortController
}
```

## QueryEngine (SDK/Headless Mode)

`QueryEngine.ts` wraps the query loop for non-interactive use:

```typescript
const engine = new QueryEngine(config)
for await (const event of engine.submitMessage("Build a todo app")) {
  if (event.type === 'text') console.log(event.text)
  if (event.type === 'tool_use') console.log(event.name)
}
```

Features:
- Owns conversation state (messages, file cache, usage)
- `submitMessage()` runs one complete agentic turn
- Handles snip compaction, file history, task budgeting
- Can resume from chat archive (`loadChatArchive()`)

## Query Dependencies (Testable)

```typescript
type QueryDeps = {
  callModel: typeof queryModelWithStreaming
  microcompact: typeof microcompactMessages
  autocompact: typeof autoCompactIfNeeded
  uuid: () => string
}

// Production:
const deps = productionDeps

// Tests:
const deps = {
  callModel: mockStream,
  microcompact: noOp,
  autocompact: noOp,
  uuid: () => 'test-uuid',
}
```
