# Getting Started

## Prerequisites

- **Node.js 20+** (for JS/TS scripts and apps)
- **Python 3.11+** (for Python scripts and agents)
- Other dependencies are listed in each utility's own README

## Conventions

### Directory structure

Every utility lives in its own directory under one of three top-level folders:

- `scripts/` — standalone scripts (bash, python, node, etc.)
- `agents/` — AI agents (prompts, configs, tool definitions)
- `apps/` — small standalone applications (desktop or server)

### Each utility must include

- A `README.md` explaining what it does, how to run it, and at least one usage example
- Any dependencies declared locally (e.g. `package.json`, `requirements.txt`)

### Naming

Use lowercase kebab-case for directory names: `my-cool-script`, `email-summarizer`, etc.
