# Claude Code - Deep Technical Analysis & Learning Guide

A comprehensive analysis of Claude Code's architecture, system prompts, engineering patterns, and community methods for maximizing effectiveness.

**Source**: Extracted from Claude Code source code analysis + community research (March 2026)

## Table of Contents

- [Architecture Overview](docs/01-architecture.md) - Entry points, boot sequence, core abstractions
- [System Prompt Engineering](docs/02-system-prompts.md) - How Claude Code constructs its system prompt
- [Tool System](docs/03-tools.md) - Tool protocol, 40+ built-in tools, MCP integration
- [Agent System](docs/04-agents.md) - Built-in agents, fork subagents, coordinator mode
- [Query Loop](docs/05-query-loop.md) - The agentic loop, streaming, compaction strategies
- [Permission & Security Model](docs/06-permissions.md) - Trust dialog, permission modes, auto-approve
- [Memory System](docs/07-memory.md) - Auto-memory, CLAUDE.md, context injection
- [Hook System](docs/08-hooks.md) - Lifecycle hooks, pre/post tool hooks
- [Community Methods](docs/09-community-methods.md) - Techniques from the community for using Claude Code effectively
- [Key Patterns & Lessons](docs/10-patterns.md) - Engineering patterns, optimization strategies
- [Full System Prompt Reference](docs/11-full-system-prompt-reference.md) - Reconstructed complete system prompt
- [Ecosystem Map](docs/12-ecosystem-map.md) - 30+ repos, tools, and resources mapped
- [Hidden Internals](docs/13-hidden-internals.md) - Unreleased features (BUDDY, KAIROS, ULTRAPLAN), codenames, multi-model architecture

## Quick Start

If you want to understand Claude Code deeply, start with:
1. **[System Prompts](docs/02-system-prompts.md)** - The most actionable section
2. **[Agent System](docs/04-agents.md)** - How subagents work
3. **[Community Methods](docs/09-community-methods.md)** - Practical tips

## License

Educational/research purposes only. Claude Code is a product of Anthropic.
