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

---

## Detailed Repo Analysis

*Research conducted 2026-03-31 via web fetching of GitHub repos and community resources.*

### 1. Leonxlnx/claude-code-system-prompts

**URL**: https://github.com/Leonxlnx/claude-code-system-prompts

An educational documentation project that catalogs 30+ system prompts, agent directives, and security classifiers extracted from Claude Code's publicly leaked source. Organized into clear categories:

- **Core Identity** (4 prompts): Main system prompt, simple mode, default agent prompt, security boundaries
- **Orchestration** (2 prompts): Multi-worker coordinator, team communication protocols
- **Specialized Agents** (4 prompts): Verification testing, code exploration, agent creation, status line configuration
- **Security & Permissions** (2 prompts): Permission explanations, 2-stage auto-approval classifier
- **Tool Descriptions** (1 consolidated): 30+ tool definitions
- **Utilities** (7 prompts): Memory selection, session search, summarization, title generation
- **Context Management** (2 prompts): Conversation compaction, session recaps
- **Dynamic Sections** (3 prompts): Proactive mode, browser automation, memory loading
- **Bundled Skills** (5 prompts): Code simplification, skill creation, diagnostics, configuration management

**Key architectural insight**: The system prompt is not static but dynamically assembled from modular builders. A critical `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` marker splits content into a cacheable prefix (global sections identical across sessions, leveraging prompt caching) and a dynamic suffix (session-specific context regenerated per conversation).

**Auto-approval system**: Uses a 2-stage classifier with fast initial screening, then extended thinking if uncertain.

**Memory hierarchy**: Memory files load in priority order from enterprise-managed to project-local, supporting `@include` directives (max depth 5) and conditional path injection via frontmatter.

The project is purely documentation (no version history or implementation guides) and explicitly states it is educational/research-only.

### 2. nirholas/claude-code

**URL**: https://github.com/nirholas/claude-code

Preserves the full source code of Claude Code CLI that was leaked on 2026-03-31 via a `.map` file in the npm package. The leak exposed approximately 512,000+ lines of TypeScript across ~1,900 files.

**Major subsystems discovered in the source**:
- **Tools** (~40 implementations): File operations, search utilities, execution engines, agent spawning
- **Commands** (~50 slash commands): User-facing operations like `/commit`, `/review`, `/mcp`, `/config`
- **Components**: ~140 React + Ink terminal UI components
- **Services**: API integration, OAuth, MCP connections, analytics via GrowthBook, plugin loading
- **Bridge System**: Bidirectional IDE integration for VS Code and JetBrains

**Technical details from source analysis**:
- `QueryEngine.ts` (~46K lines) drives the entire LLM interaction loop -- streaming, tool invocation, thinking mode, token counting, retries
- Built on Bun runtime, TypeScript (strict), React with Ink for terminal UI, Commander.js for CLI parsing, Zod for schemas
- Feature flags via `bun:bundle` enable dead-code elimination (voice mode, proactive triggering, bridge mode)
- Startup optimization parallelizes config loads before heavy module evaluation
- Swarm system enables multi-agent orchestration through `AgentTool` and team management utilities

**MCP Explorer Server**: Includes an installable npm package `claude-code-explorer-mcp` with tools like `list_tools`, `get_tool_source`, `search_source`, and `list_directory` for exploring the source via any MCP-compatible client.

### 3. instructkr/claude-code

**URL**: https://github.com/instructkr/claude-code

Contrary to the earlier description in this document, this repo is actually a **Python-based reimplementation project** focused on porting Claude Code functionality, not a Korean-language guide. The repository explicitly disclaims affiliation with Anthropic and is educational in scope.

**Structure**:
- `src/` -- Active Python porting workspace with `port_manifest.py`, `models.py`, `commands.py`, `tools.py`, `query_engine.py`, `main.py`
- `tests/` -- Verification suite
- `assets/omx/` -- Workflow documentation screenshots

**Key commands**: `python3 -m src.main summary` (porting progress), `python3 -m src.main manifest` (workspace structure).

The project documents use of **oh-my-codex** (an AI-assisted orchestration tool) with `$team` mode for collaborative review and `$ralph` mode for persistent execution. The port is incomplete -- "not yet a complete one-to-one replacement."

**Note**: No Korean-language tips or CLAUDE.md examples were found despite earlier characterization.

---

## Additional Community Resources

### High-Impact Repos

#### shanraisshan/claude-code-best-practice (15,000+ stars, GitHub Trending)
**URL**: https://github.com/shanraisshan/claude-code-best-practice

The most popular community best-practices repo. Documents 87 practical tips organized around eight extensibility mechanisms: subagents, commands, skills, workflows, hooks, MCP servers, settings, and memory. Catalogs nine development workflows from practitioners (Affaan M, Garry Tan, GitHub Spec Kit team).

Key patterns documented:
- **Command -> Agent -> Skill architecture**: Demonstrates orchestration patterns combining all three
- **87 tips** including: "always start with plan mode," "challenge Claude to prove solutions work before submitting PRs," "after mediocre fixes, request Claude to implement the elegant solution knowing everything now"
- **Nine workflow catalogs**: Research -> Plan -> Execute -> Review -> Ship; TDD-first; spec-driven; parallel sprint execution with role-based personas
- **CLAUDE.md guidance**: Target under 200 lines per file
- **Hot features**: Auto Mode (background safety classifier), Channels (push events from Telegram/Discord), Agent Teams, Scheduled Tasks, Remote Control

#### FlorianBruniaux/claude-code-ultimate-guide (23K+ lines of docs)
**URL**: https://github.com/FlorianBruniaux/claude-code-ultimate-guide

The most comprehensive single guide, featuring 225 production templates, 41 Mermaid architecture diagrams, and a 271-question knowledge assessment quiz.

Unique contributions:
- **Threat intelligence database**: 655 catalogued malicious skill patterns, 24 CVE-mapped vulnerabilities with mitigation strategies, MCP rug-pull attack chain analysis
- **Methodology frameworks**: TDD, SDD (Spec-Driven Development), BDD, and "Get Shit Done" approaches with decision frameworks for choosing between agents, skills, and commands
- **Trinity Pattern**: Multi-agent production-scale pattern with real-world metrics (50% faster execution, 2x speed on large codebases)
- **Security coverage**: Unicode injection patterns, hidden instruction detection, auto-execute vulnerability analysis

#### ykdojo/claude-code-tips (45 tips)
**URL**: https://github.com/ykdojo/claude-code-tips

Practical tips numbered 0-45 with code examples. Most impactful unique contributions:
- **Proactive context management**: Writing handoff documents before starting fresh conversations
- **Voice input integration**: Using local voice transcription (MacWhisper) for faster communication
- **Write-test cycle with tmux**: Creating testable tasks using tmux for Claude to work autonomously
- **Gemini CLI as fallback**: Workaround for sites Claude cannot fetch by delegating to Gemini through terminal
- **Conversation search**: `grep -l -i "keyword" ~/.claude/projects/-Users-*/*.jsonl`
- **System prompt optimization**: Cutting the system prompt in half for focused sessions

#### hesreallyhim/awesome-claude-code
**URL**: https://github.com/hesreallyhim/awesome-claude-code

The primary curated "awesome list" for Claude Code. Categories include Agent Skills (15+), Workflows & Knowledge Guides (20+), Tooling (20+), Orchestrators (10+), Status Lines, Slash-Commands, CLAUDE.md Files, Alternative Clients, and Official Documentation.

Standout entries:
- **Ruflo**: Multi-agent swarm orchestration with self-learning
- **claude-devtools**: Desktop app for session observability and analytics
- **AgentSys**: Production-grade workflow automation
- **Trail of Bits security auditing skills**
- **K-Dense scientific research toolkit**
- **Ralph Wiggum technique** implementations for autonomous development loops

#### rohitg00/awesome-claude-code-toolkit
**URL**: https://github.com/rohitg00/awesome-claude-code-toolkit

Claims to be "the most comprehensive toolkit" with 135 agents, 35 curated skills (+400,000 via SkillKit), 42 commands, 176+ plugins, 20 hooks, 15 rules, 7 templates, 13 MCP configs, 26 companion apps, and 51 ecosystem entries.

Most-starred plugins within the toolkit:
- **everything-claude-code** (78,600+ stars): Performance optimization across multiple AI platforms
- **wshobson/agents** (31,300+ stars): 112 specialized agents and 146 skills
- **vibe-kanban** (23,200+ stars): Kanban orchestration supporting 10+ coding agents
- **gstack** (15,000+ stars): Garry Tan's opinionated setup with CEO/manager/QA agents
- **pro-workflow** (1,400+ stars): Self-correcting memory and parallel worktrees

#### Additional Notable Repos
- **rosmur/claudecode-best-practices** (https://rosmur.github.io/claudecode-best-practices/): Aggregated best practices from multiple sources covering CLAUDE.md sizing (100-200 lines max, under 2,000 tokens), multi-Claude verification pipeline, and dev docs three-file pattern
- **ThamJiaHe/claude-prompt-engineering-guide**: Weekly-updated guide covering Opus 4.6, Sonnet 4.6, Haiku 4.5 with 100+ curated skills, 24 hook events, and companion tool "claude-kopitiam" (loads 7 rule files into `~/.claude/rules/`)
- **wesammustafa/Claude-Code-Everything-You-Need-to-Know**: All-in-one guide covering BMAD method, MCP servers, hooks, workflows, and automation
- **zebbern/claude-code-guide**: Beginner-to-power-user guide covering setup, commands, workflows, agents, skills, and security practices for hooks
- **luongnv89/claude-howto**: Visual, example-driven guide with copy-paste templates from basic concepts to advanced agents
- **awattar/claude-code-best-practices**: Distilled patterns for terminal-based coding with prompt design and safe automation focus
- **travisvn/awesome-claude-skills**: Curated list of Claude Skills, resources, and tools
- **BehiSecc/awesome-claude-skills**: Curated skills list including Trail of Bits security skills and OWASP-security skill
- **ComposioHQ/awesome-claude-plugins**: Production-ready plugins extending Claude Code with custom commands, agents, hooks, and MCP servers
- **jqueryscript/awesome-claude-code**: Alternative awesome list focusing on tools, IDE integrations, and frameworks
- **webfuse-com/awesome-claude**: Broader Anthropic Claude resource list including MCP servers
- **anthropics/prompt-eng-interactive-tutorial**: Official Anthropic interactive prompt engineering tutorial

### Key Blog Posts and Articles

#### Anthropic Official: Best Practices for Claude Code
**URL**: https://code.claude.com/docs/en/best-practices

The official guide emphasizes that **context window management is the single most important constraint**. Key official recommendations:
1. **Give Claude a way to verify its work** -- "the single highest-leverage thing you can do"
2. **Explore first, then plan, then code** -- four-phase workflow: Explore -> Plan -> Implement -> Commit
3. **Keep CLAUDE.md concise** -- "For each line, ask: Would removing this cause Claude to make mistakes? If not, cut it"
4. **Course-correct early** -- after two failed corrections, `/clear` and start fresh
5. **Use subagents for investigation** -- delegate research to separate context windows
6. **Fan out for scale** -- loop `claude -p` for large migrations with `--allowedTools` scoping
7. **Writer/Reviewer pattern** -- use separate sessions for writing and reviewing code
8. **Let Claude interview you** -- use AskUserQuestion tool for spec generation

CLAUDE.md include/exclude guidance from official docs:

| Include | Exclude |
|---------|---------|
| Bash commands Claude cannot guess | Anything Claude can figure out by reading code |
| Code style rules differing from defaults | Standard language conventions Claude already knows |
| Testing instructions and preferred test runners | Detailed API documentation (link instead) |
| Repository etiquette (branch naming, PR conventions) | Information that changes frequently |
| Architectural decisions specific to your project | Long explanations or tutorials |
| Developer environment quirks | File-by-file descriptions of the codebase |
| Common gotchas or non-obvious behaviors | Self-evident practices like "write clean code" |

#### HumanLayer: Writing a Good CLAUDE.md
**URL**: https://www.humanlayer.dev/blog/writing-a-good-claude-md

Core insight: frontier thinking LLMs can follow approximately 150-200 instructions with reasonable consistency. Claude Code's system prompt already contains about 50, leaving limited budget for your CLAUDE.md. Key recommendations:
- **Under 300 lines** (HumanLayer's own CLAUDE.md is under 60 lines)
- **Never auto-generate with /init** -- these files are too high-leverage for automation
- **Progressive disclosure**: point Claude toward separate documentation files rather than embedding everything
- **Never send an LLM to do a linter's job** -- use deterministic tools for code style
- **Focus on universally applicable instructions** -- reserve task-specific content for separate files

#### Arize: Prompt Learning for CLAUDE.md Optimization
**URL**: https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/

Used meta-prompting (Prompt Learning) to optimize CLAUDE.md through performance feedback on SWE Bench Lite. Results: **+5.19% accuracy** on cross-repo tasks, **+10.87% accuracy** on single-repo (Django) optimization. Key takeaway: repository-specific optimization is far more effective than general improvement. The actual optimized prompts were not published, but the methodology validates that CLAUDE.md tuning has measurable impact.

#### Rosmur: Aggregated Best Practices
**URL**: https://rosmur.github.io/claudecode-best-practices/

Synthesized from multiple community sources. Notable unique contributions:

**Two competing subagent philosophies**:
1. Specialized subagents (custom code-reviewer, build-error-resolver, etc.)
2. Clone pattern (spawn agent clones via Task(); agent manages orchestration dynamically)
Consensus: Clone pattern preserves context better; use specialized subagents only for narrow tasks.

**Multi-Claude verification pipeline**:
- Claude A writes code -> Claude B (fresh context) reviews -> Claude C edits based on feedback
- Advanced: o3 (planning) -> Sonnet (validation) -> Sonnet (execution) -> Sonnet (verification) -> o3 (final check)

**Dev docs three-file pattern**:
```
task-name-plan.md      # The accepted plan
task-name-context.md   # Key files, decisions
task-name-tasks.md     # Checklist of work
```

**Context management numbers**: Clear at 60k tokens or 30% threshold. Baseline under 20k tokens. MCP tools under 20k tokens total or they "cripple Claude."

**Auto-activation for skills**: Use hooks to inject skill reminders before Claude reads messages -- manual reminders are ignored approximately 90% of the time.

**Token cost warning**: Auto-formatting hooks cost approximately 160k tokens in 3 rounds. Avoid unless the benefit is clear.

### Community Patterns Worth Noting

#### The Interview-then-Execute Pattern (from Anthropic official docs)
```
I want to build [brief description]. Interview me in detail using the
AskUserQuestion tool. Ask about technical implementation, UI/UX, edge
cases, concerns, and tradeoffs. Don't ask obvious questions, dig into
the hard parts I might not have considered. Keep interviewing until
we've covered everything, then write a complete spec to SPEC.md.
```
Then start a fresh session to execute the spec with clean context.

#### The Writer/Reviewer Pattern (from Anthropic official docs)
Run two Claude sessions in parallel:
- Session A (Writer): Implements the feature
- Session B (Reviewer): Reviews from fresh context without implementation bias
- Session A: Addresses review feedback

#### The Ralph Wiggum Technique (multiple community implementations)
Autonomous development loops where Claude operates continuously on tasks with persistent execution, self-correcting based on test results. Multiple implementations exist in the awesome-claude-code ecosystem.

#### The Spec-Driven Development Workflow (from community)
1. Start with minimal prompt, ask Claude to interview you
2. Generate comprehensive spec to SPEC.md
3. Start fresh session with clean context
4. Execute spec in gated phases with tests at each phase boundary
5. Each phase: plan -> implement -> test -> commit

#### CLAUDE.md Anti-Patterns (community consensus)
- Embedding entire files via @-references (bloats every session)
- "Never use X" without providing alternatives (agent gets stuck)
- Writing comprehensive manuals (overwhelms instruction budget)
- Auto-generating with `/init` without heavy curation
- Including code style rules that a linter can enforce
- Adding task-specific instructions that apply to only one task
- Appending narrow failure-specific rules without generalizing

### Ecosystem and Tooling Landscape (March 2026)

The Claude Code ecosystem has grown rapidly. Key categories:

| Category | Notable Examples | Count |
|----------|-----------------|-------|
| Awesome Lists | hesreallyhim/awesome-claude-code, rohitg00/awesome-claude-code-toolkit, jqueryscript/awesome-claude-code | 3+ |
| Skills Collections | BehiSecc/awesome-claude-skills, travisvn/awesome-claude-skills, ComposioHQ/awesome-claude-skills | 3+ |
| Best Practice Guides | shanraisshan (15K stars), FlorianBruniaux (23K lines), rosmur, awattar | 5+ |
| Plugin Ecosystems | ComposioHQ/awesome-claude-plugins, rohitg00 toolkit (176+ plugins) | 2+ |
| Tip Collections | ykdojo (45 tips), shanraisshan (87 tips), builder.io (50 tips) | 3+ |
| Security Resources | FlorianBruniaux (655 malicious patterns), Trail of Bits skills, OWASP skill | 3+ |
| Prompt Engineering | ThamJiaHe guide, anthropics/prompt-eng-interactive-tutorial, Arize research | 3+ |
| Source Analysis | nirholas/claude-code, Leonxlnx/claude-code-system-prompts | 2 |

### Summary of Community Consensus (March 2026)

After reviewing all sources, the community largely agrees on these principles:

1. **CLAUDE.md is the highest-leverage configuration point** -- but must be kept concise (100-300 lines max). Quality over quantity.
2. **Context window management is the primary constraint** -- clear aggressively, use subagents for research, track token usage.
3. **Plan before implementing** -- the explore -> plan -> implement -> verify workflow is near-universal.
4. **Verification is non-negotiable** -- provide tests, screenshots, or scripts. "The single highest-leverage thing you can do."
5. **Fresh context beats accumulated context** -- start new sessions for new tasks; write handoff documents for continuity.
6. **Use deterministic tools for deterministic tasks** -- linters for style, hooks for mandatory actions, not CLAUDE.md instructions.
7. **Progressive disclosure for knowledge** -- keep CLAUDE.md lean; use skills, slash commands, and separate docs for domain knowledge.
8. **Subagents for context isolation** -- research, review, and verification should not pollute the main conversation.
9. **Multiple Claude sessions for quality** -- writer/reviewer pattern, parallel worktrees, and separate implementation/verification agents.
10. **Security awareness is growing** -- the community is increasingly documenting attack vectors (prompt injection via skills, MCP rug-pulls, Unicode injection) alongside defensive patterns.
