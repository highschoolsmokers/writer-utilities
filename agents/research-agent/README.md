# Research Agent

A historical research agent for writers. Helps you investigate real people, cultures, places, and events — and organize your findings into structured reference documents.

## What It Does

- **Historical research** — Investigates periods, people, places, cultures, and events, surfacing the vivid, story-relevant details writers actually need
- **Newspaper & media lookups** — Searches digitized newspaper archives to find contemporary coverage of events in specific places and periods
- **Fact-checking** — Flags anachronisms, common misconceptions, and gaps between documented history and your narrative
- **Research organization** — Maintains structured Markdown reference files using templates

## Setup

### As a Claude Code custom agent

```bash
# From your project root, start a session with the research agent
claude --agent agents/research-agent/agent.md
```

Or add it to your `.claude/agents/` directory for persistent access:

```bash
cp agents/research-agent/agent.md ~/.claude/agents/research-agent.md
```

Then invoke it with:

```bash
claude --agent research-agent
```

### As a system prompt

The `agent.md` file can also be used as a system prompt with any Claude API integration. Copy its contents into your system prompt field.

## Templates

The `templates/` directory contains starter templates for research entries:

| Template | Use For |
|----------|---------|
| `research-index.md` | Top-level index for all research on a project |
| `person.md` | A real historical figure |
| `location.md` | A city, region, or place in a specific era |
| `culture.md` | A culture or society at a specific point in time |
| `event.md` | A historical event |
| `timeline.md` | Chronology with concurrent world events |
| `research-brief.md` | General research on a topic, with newspaper coverage |

### Using templates

Point the agent at a template when starting a new entry:

```
"I need a person entry for Frederick Douglass during his time in Rochester.
Use the person template."
```

The agent will copy the template, fill in what it can from research, and flag what needs your input.

## Example Usage

### Research a historical period

```
"I'm writing a story set in 12th-century Kyoto. Research daily life for a
low-ranking court noble — what they ate, wore, how they spent their days,
and what social pressures they faced."
```

### Look up newspaper coverage

```
"Find newspaper coverage of the 1900 Galveston hurricane — what were papers
in Houston and New Orleans reporting in the days before and after? I want
to know how the story unfolded in real time."
```

### Research a real person

```
"Research Ada Lovelace's relationship with Charles Babbage. What do we
actually know from letters and contemporary accounts vs. what's been
romanticized later?"
```

### Fact-check a draft

```
"Read my chapter set in 1920s Harlem (./drafts/chapter-3.md) and flag
anything that's anachronistic — wrong slang, objects that didn't exist
yet, events out of order, that kind of thing."
```

### Research a location in a specific era

```
"What did San Francisco's Barbary Coast look like in 1875? I need the
sights, sounds, smells — what a character walking through would experience."
```

## Tips

- **Start with your project.** Tell the agent what you're writing, the period, and what you need
- **Point it at your files.** The agent works best when it can read your existing notes, outlines, and drafts
- **Ask for newspapers.** Contemporary media coverage gives you period-accurate language and reveals how people experienced events in real time
- **Track what's real vs. invented.** The templates include sections for separating documented fact from your fictional choices
