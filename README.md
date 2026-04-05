# Writer Utilities

A collection of scripts, AI agents, and small apps for writers.

## Agents (Claude Code Plugins)

Each agent is distributed as its own GitHub repo and installable as a Claude Code plugin.

```bash
# Add the marketplace to discover all plugins
/plugin marketplace add highschoolsmokers/writer-utilities-marketplace
```

| Plugin | Repo | Description |
|--------|------|-------------|
| `literary-research-agent` | [highschoolsmokers/literary-research-agent](https://github.com/highschoolsmokers/literary-research-agent) | Finds verified quotes from archives, builds citations, analyzes craft and theory |
| `historical-research-agent` | [highschoolsmokers/historical-research-agent](https://github.com/highschoolsmokers/historical-research-agent) | Investigates real people, cultures, places, events, and newspaper archives |
| `submission-watcher-agent` | [highschoolsmokers/submission-watcher-agent](https://github.com/highschoolsmokers/submission-watcher-agent) | Monitors magazine submission windows and emails you when they open |

Install any plugin:

```bash
/plugin install literary-research-agent
/plugin install historical-research-agent
/plugin install submission-watcher-agent
```

## Scripts

| Name | Description |
|------|-------------|
| [gdoc-to-scrivener](scripts/gdoc-to-scrivener/) | Converts a Google Doc outline into a Scrivener 3 project |

## Apps

| Name | Description |
|------|-------------|
| [submission-cli](apps/submission-cli/) | Format manuscripts to Shunn standard, generate cover letters, and queue for submission |

## Marketplace

The `marketplace.json` at the root of this repo is the plugin registry. Users add it once:

```bash
/plugin marketplace add highschoolsmokers/writer-utilities-marketplace
```

Then they can browse and install any plugin listed above.

## Getting Started

See [docs/getting-started.md](docs/getting-started.md) for setup prerequisites and conventions.

## Adding a New Utility

### Scripts & Apps
1. Create a directory under `scripts/` or `apps/`
2. Add a `README.md` inside it with: what it does, how to use it, and examples
3. Update the table above

### Agents
1. Create a new GitHub repo with the plugin structure (see existing agent repos for reference)
2. Add it to `marketplace.json` in this repo
3. Update the agents table above
