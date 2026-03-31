# Hidden Internals & Unreleased Features

Discoveries from source analysis and community research that reveal what's coming and how Claude Code works under the hood.

---

## Multi-Model Architecture

Claude Code doesn't use one model for everything. Different models handle different tasks:

| Task | Model | Why |
|------|-------|-----|
| Core conversation loop | User-selected (Opus/Sonnet) | Quality matters most |
| Tool use summaries | Haiku | Speed + cost (30-char labels) |
| Session titles | Haiku | Speed (3-7 word titles) |
| Away summaries | Haiku | Speed (1-3 sentences) |
| Agent summaries | Haiku | Speed (1 sentence, present tense) |
| Explore agent (external) | Haiku | Speed for codebase search |
| Explore agent (Anthropic) | Inherits parent model | Quality for internal use |
| Memory selection | Sonnet | Balance (select ≤5 relevant files) |
| Conversation compaction | Sonnet | Balance (summarize while preserving key info) |
| Permission explanation | Main model | Quality (concurrent with permission prompt) |
| Auto-mode classifier | Separate LLM call | Safety (independent security evaluation) |
| ULTRAPLAN (unreleased) | Opus 4.6 remote | Max quality (up to 30 min) |

## The 30+ Prompt Components

Claude Code's system prompt isn't monolithic — it's assembled from 30+ separate components:

### Core Identity (4)
1. Main system prompt
2. Simple mode (testing only)
3. Default agent prompt
4. Cyber risk instruction

### Orchestration (2)
5. Coordinator system prompt
6. Teammate prompt addendum

### Specialized Agents (4+)
7. Verification agent
8. Explore agent
9. Agent creation architect
10. Statusline setup agent

### Security & Permissions (2)
11. Permission explainer
12. YOLO auto-mode classifier (2-stage)

### Tool Descriptions (1)
13. Consolidated tool prompts (31+ tool-specific prompts inside)

### Utilities (7)
14. Tool use summary generator
15. Session search
16. Memory selection
17. Auto-mode critique
18. Session title generator
19. Away summary
20. Agent summary

### Context Management (2)
21. Compact service (3 modes: Full, Partial Recent, Partial Older)
22. Session recaps

### Dynamic Sections (3)
23. Proactive/autonomous mode
24. Chrome browser automation
25. Memory instruction loader

### Bundled Skills (5+)
26. Simplify skill
27. Skillify (skill creation)
28. Stuck skill (diagnostics, ant-only)
29. Remember skill
30. Update config skill

## BUDDY: The Tamagotchi System

A complete virtual pet companion hidden in the source:

- **18 species** with 5 rarity tiers
- **1% shiny variant** chance
- **Deterministic gacha** using Mulberry32 PRNG
- **ASCII art sprites** for terminal display
- **AI-generated personality** descriptions ("souls")
- **Release window**: April 1-7, 2026 teaser → Full launch May 2026
- Feature-gated behind `BUDDY`

## KAIROS: The Always-On Agent

A persistent background agent that runs continuously:

- **Tick prompts** every ~3 seconds
- **15-second blocking budget** per tick
- **Append-only daily logs** for memory
- **Exclusive tools**: SendUserFile, PushNotification, SubscribePR
- **`terminalFocus` calibration**: More autonomous when user is away, more collaborative when watching
- Anti-narration: "Do not narrate each step. Never respond with only a status message."
- Feature-gated behind `KAIROS`

## ULTRAPLAN: Remote Planning

Offloads complex planning to a dedicated environment:

- Runs **Opus 4.6 in Cloud Container Runtime**
- Up to **30 minutes** of planning time
- **Browser-based approval UI** for results
- Feature-gated behind `ULTRAPLAN`

## autoDream: Memory Consolidation

A 4-phase memory engine:

1. **Orient** — Assess current memory state
2. **Gather** — Collect session insights
3. **Consolidate** — Merge and deduplicate
4. **Prune** — Keep under 200 lines / 25KB

**Triple-gate trigger**: 24-hour window + 5 sessions + consolidation lock

## The Auto-Approval Classifier

A 2-stage security system for `auto` permission mode:

### Stage 1: Fast Screening
- Quick pattern matching against allow/deny rules
- Read-only tools bypass entirely
- Known-safe patterns auto-approved

### Stage 2: Extended Thinking (if uncertain)
- Separate LLM call evaluates the tool use
- Has its own system prompt (`auto_mode_system_prompt.txt`)
- Different templates for external vs Anthropic users
- **Critical**: Excludes assistant text from transcripts to prevent prompt injection
- Returns LOW/MEDIUM/HIGH risk classification

## Compaction: 5 Tiers

Context management has 5 increasingly aggressive strategies:

```
1. Snip Compact     — Remove old messages (lightest)
2. Micro Compact    — In-place compression of tool results
3. Context Collapse  — Staged summarization of sections
4. Auto Compact     — Full LLM summarization (uses Sonnet)
5. Reactive Compact — Emergency recovery on prompt-too-long errors
```

The compact service has a critical design: **no-tools preamble** prevents tool execution during summarization. It requires `<analysis>` scratchpad blocks that get stripped from the output.

**Circuit breaker**: Stops after 3 consecutive failures.

## Protected Files

Claude Code protects certain files from modification:
- `.gitconfig`
- `.bashrc`
- `.zshrc`
- `.mcp.json`
- `.claude.json`

## API Endpoints

- `/api/claude_code_penguin_mode` — Fast mode endpoint
- `/api/claude_code/settings` — Remote settings (polled hourly)

## Telemetry Details

Two analytics sinks:
1. **Anthropic** (first-party, OpenTelemetry)
2. **Datadog** (third-party)

Every event includes:
- Environment fingerprinting
- Process metrics
- Repo hashing

6+ remote killswitches for: permissions, fast mode, voice mode, analytics.

**GrowthBook feature flags** can change any user's behavior server-side without local consent.

## 108 Missing/Gated Modules

Modules found in source but never published (DCE'd from external builds):
- Daemon supervisor
- Proactive notifications
- Context collapse engine
- Remote skill loader
- KAIROS mode
- Workflow execution
- Memory telemetry
- Session transcripts
- Multi-agent coordinator
- 20+ feature-gated tools

## The Prompt Cache Split

The `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` marker (`__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__`) is the key to Claude Code's cost efficiency:

```
[STATIC PREFIX — ~70% of prompt — cached globally across ALL users]
  Identity
  System rules
  Coding philosophy
  Actions guidance
  Tool usage
  Tone/style
  Output efficiency
____SYSTEM_PROMPT_DYNAMIC_BOUNDARY____
[DYNAMIC SUFFIX — ~30% — session-specific]
  Agent availability
  Memory prompt
  Environment info
  Language preference
  MCP instructions
  Scratchpad
```

Moving the agent list from inline (in tool descriptions) to attachment messages saved **10.2% of fleet cache_creation tokens** — because the agent list changes when MCP servers connect/disconnect, which would bust the static cache.

## Section Caching Pattern

```typescript
// Computed once per session, survives turns:
systemPromptSection('memory', () => loadMemoryPrompt())

// Recomputed every turn (DANGEROUS — busts prompt cache):
DANGEROUS_uncachedSystemPromptSection('mcp_instructions', () => getMcpInstructions())
```

`/clear` and `/compact` reset the cached sections.
