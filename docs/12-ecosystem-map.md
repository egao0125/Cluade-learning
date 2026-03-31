# Claude Code Ecosystem Map (March 2026)

A comprehensive map of 30+ repos, tools, and resources around Claude Code.

---

## Tier 1: System Prompt Extraction & Tracking

| Repo | Stars | Description |
|------|-------|-------------|
| [Piebald-AI/claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts) | 7,200+ | Most comprehensive, continuously-updated. 137 versions tracked. 110+ conditionally-loaded prompt strings |
| [badlogic/cchistory](https://github.com/badlogic/cchistory) | — | Extracts and diffs system prompts across ALL versions. [Live site](https://cchistory.mariozechner.at/) with Monaco editor |
| [Leonxlnx/claude-code-system-prompts](https://github.com/Leonxlnx/claude-code-system-prompts) | — | 30 categorized prompt files with source location mapping |
| [x1xhlol/system-prompts-and-models-of-ai-tools](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools) | 134,000+ | Prompts from 30+ AI tools (Claude, Cursor, Devin, Windsurf, etc.) for cross-comparison |
| [matthew-lim-matthew-lim/claude-code-system-prompt](https://github.com/matthew-lim-matthew-lim/claude-code-system-prompt) | — | Early viral extraction (Reddit r/agi) |
| [asgeirtj/system_prompts_leaks](https://github.com/asgeirtj/system_prompts_leaks) | — | Multi-tool collection including Claude Code v2.1.50 |

## Tier 2: Source Code Archives & Analysis

| Repo | Stars | Description |
|------|-------|-------------|
| [nirholas/claude-code](https://github.com/nirholas/claude-code) | — | Full source + MCP explorer server + 16 build-out prompts |
| [Kuberwastaken/claude-code](https://github.com/Kuberwastaken/claude-code) | 1,100+ | Source backup with detailed internal feature analysis (BUDDY, KAIROS, ULTRAPLAN) |
| [sanbuphy/claude-code-source-code](https://github.com/sanbuphy/claude-code-source-code) | — | v2.1.88 source with 5 bilingual (EN/ZH) deep analysis reports |
| [instructkr/claude-code](https://github.com/instructkr/claude-code) | — | Python reimplementation project + legal/ethical essay |
| [chatgptprojects/claude-code](https://github.com/chatgptprojects/claude-code) | — | Another organized source archive |

## Tier 3: Awesome Lists & Curated Collections

| Repo | Stars | Description |
|------|-------|-------------|
| [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | 34,900+ | THE premier curated list — skills, workflows, tooling, hooks, commands |
| [jqueryscript/awesome-claude-code](https://github.com/jqueryscript/awesome-claude-code) | — | Star-rated list, 55K+ official repo stars tracked |
| [rohitg00/awesome-claude-code-toolkit](https://github.com/rohitg00/awesome-claude-code-toolkit) | — | 176+ plugins, 135 agents, 35 skills, 42 commands |
| [webfuse-com/awesome-claude](https://github.com/webfuse-com/awesome-claude) | — | Broader Claude ecosystem (SDKs, cloud access, educational) |
| [travisvn/awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills) | — | 100+ skills across 15 categories |
| [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) | — | 78 SaaS integrations (HubSpot, Jira, Slack, etc.) |

## Tier 4: Frameworks & Optimization

| Repo | Stars | Description |
|------|-------|-------------|
| [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code) | 50,000+ | 30 agents, 136+ skills, 60+ commands, SQLite state store |
| [FlorianBruniaux/claude-code-ultimate-guide](https://github.com/FlorianBruniaux/claude-code-ultimate-guide) | — | 23K+ lines docs, 225 templates, 655 malicious skill patterns catalogued |
| [shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice) | 15,000+ | 87 tips, 9 workflow catalogs, 8 framework comparisons |
| [NeoLabHQ/context-engineering-kit](https://github.com/NeoLabHQ/context-engineering-kit) | — | SDD/MAKER/Reflexion patterns. Cited by Peking University |
| [shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) | — | Build a nano agent harness from scratch in 12 sessions |
| [nadimtuhin/claude-token-optimizer](https://github.com/nadimtuhin/claude-token-optimizer) | — | 90% token savings via tiered loading (11K→1.3K tokens) |

## Tier 5: Specialized Tools

| Repo | Stars | Description |
|------|-------|-------------|
| [Piebald-AI/tweakcc](https://github.com/Piebald-AI/tweakcc) | — | Patch Claude Code's system prompts. Unlock unreleased features, 50% faster startup |
| [bl-ue/tweakcc-system-prompts](https://github.com/bl-ue/tweakcc-system-prompts) | — | 48KB smaller prompts, 30% faster, same accuracy |
| [alirezarezvani/ClaudeForge](https://github.com/alirezarezvani/ClaudeForge) | — | CLAUDE.md generator with 0-100 quality scoring |
| [199-biotechnologies/claude-deep-research-skill](https://github.com/199-biotechnologies/claude-deep-research-skill) | — | 8-phase research pipeline, multi-persona red teaming |
| [jhlee0409/claude-code-history-viewer](https://github.com/jhlee0409/claude-code-history-viewer) | — | Desktop app for browsing histories across 7 AI coding tools |
| [barkain/claude-code-workflow-orchestration](https://github.com/barkain/claude-code-workflow-orchestration) | — | Hook-based agent delegation framework |
| [wshobson/agents](https://github.com/wshobson/agents) | — | 112 agents, 146 skills, 79 tools in 72 plugins |
| [Comfy-Org/comfy-claude-prompt-library](https://github.com/Comfy-Org/comfy-claude-prompt-library) | — | 70+ commands from ComfyUI team |

---

## Internal Codenames Discovered

| Codename | Meaning |
|----------|---------|
| **Tengu** | Claude Code project name |
| **Penguin Mode** | Fast/low-latency execution mode |
| **KAIROS** | Always-on persistent background agent |
| **ULTRAPLAN** | Remote planning offloaded to Opus 4.6 (up to 30 min) |
| **BUDDY** | Tamagotchi virtual pet system (18 species, 5 rarity tiers) |
| **autoDream** | 4-phase memory consolidation engine |
| **Fennec** | Opus 4.6 internal name |
| **Numbat** | Upcoming model |
| **Capybara** | Previous model generation |

## Unreleased Features (Feature-Gated)

Found in source via `feature()` from `bun:bundle`:

| Feature | Description |
|---------|-------------|
| `KAIROS` | Always-on agent with tick prompts every ~3 seconds |
| `ULTRAPLAN` | Remote planning via Cloud Container Runtime |
| `BUDDY` | Virtual pet companion (gated for April 1-7 teaser, May 2026 launch) |
| `VOICE_MODE` | Voice input via STT streaming |
| `COORDINATOR_MODE` | Multi-agent orchestration |
| `DAEMON` / `BRIDGE_MODE` | Background daemon + IDE bridge |
| `WORKFLOW_SCRIPTS` | Workflow execution engine |
| `REACTIVE_COMPACT` | Proactive context compaction |
| `CONTEXT_COLLAPSE` | Staged context summarization |
| `HISTORY_SNIP` | History trimming |
| `EXPERIMENTAL_SKILL_SEARCH` | Skill discovery via ToolSearch |
| `VERIFICATION_AGENT` | Adversarial verification |
| `TOKEN_BUDGET` | Token budget mode ("+500k") |
| `ABLATION_BASELINE` | A/B testing baseline |

## Key Insight: Undercover Mode

Anthropic employees (`USER_TYPE === 'ant'`) auto-enter undercover mode in public repos:
- Strips AI attribution from commits
- Hides internal codenames
- "Do not blow your cover"
- No force-OFF switch
