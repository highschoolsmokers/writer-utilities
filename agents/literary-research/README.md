# Literary Research Agent

A literary research agent for writers. Finds real published works, extracts verified quotes with proper citations, and builds structured reference material around themes, authors, and craft techniques.

## What It Does

- **Source discovery** — Finds novels, stories, poems, essays, and criticism relevant to your topic, theme, or craft question
- **Quotation research** — Extracts real quotes from published texts with precise citations and confidence markers
- **Thematic analysis** — Traces how different authors handle the same theme, with side-by-side passages
- **Craft study** — Analyzes how published writers execute specific techniques, grounded in actual passages
- **Theory study** — Researches literary and critical theory (especially postmodern and poststructuralist), maps intellectual genealogies, and connects theoretical concepts to actual fiction and poetry
- **Bibliography building** — Maintains annotated, prioritized reading lists organized by your project's needs

## What It Won't Do

- Fabricate quotes or invent sources
- Present paraphrases as exact quotations
- Cite works that don't exist

Every quote is tagged with a confidence level (`[verified]`, `[high confidence]`, `[paraphrase]`, `[unverified]`) so you always know what you're working with.

## Setup

### As a Claude Code custom agent

```bash
# From your project root
claude --agent agents/literary-research/agent.md
```

Or add it to your `.claude/agents/` directory:

```bash
cp agents/literary-research/agent.md ~/.claude/agents/literary-research.md
```

Then invoke with:

```bash
claude --agent literary-research
```

### As a system prompt

The `agent.md` file can be used as a system prompt with any Claude API integration.

## Templates

The `templates/` directory contains starter templates for research entries:

| Template | Use For |
|----------|---------|
| `research-index.md` | Top-level index for all literary research on a project |
| `theme-study.md` | How a theme is handled across multiple works |
| `author-study.md` | Deep dive into one author's craft and relevant works |
| `quotes-collection.md` | Running collection of quotes organized by topic |
| `craft-study.md` | How a specific technique works, with examples from published fiction |
| `theory-study.md` | A theoretical concept, thinker, or school — with quotes, genealogy, and literary connections |
| `annotated-bibliography.md` | Prioritized reading list with annotations |

### Using templates

Point the agent at a template when starting research:

```
"I want to study how published authors handle unreliable narrators.
Use the craft-study template."
```

The agent will research the topic, find real passages, verify what it can, and fill in the template.

## Example Usage

### Research a theme across literature

```
"I'm writing about grief after the death of a parent. Find me the best
passages in published fiction and poetry that handle this — I want to see
how different writers approach it. Real quotes only."
```

### Study an author's craft

```
"I want to learn from how Marilynne Robinson uses landscape and place
in her prose. Pull key passages from Housekeeping and Gilead, and find
what she's said about it in essays or interviews."
```

### Build a quotes collection

```
"I'm working on a novel about immigration. Start a quotes collection
of the best passages about displacement, belonging, and language from
published literature. Organize by subtopic."
```

### Analyze a craft technique

```
"How do published short story writers handle time compression — covering
years in a few paragraphs? Show me examples from Alice Munro, Edward P.
Jones, and anyone else who does this well."
```

### Build a bibliography

```
"I'm writing a novel set during the Partition of India. Build me an
annotated bibliography — fiction, poetry, memoir, and criticism — with
reading priorities. What should I read first?"
```

### Study a theoretical concept

```
"I want to understand Derrida's concept of hauntology and how it shows
up in contemporary fiction. Give me the key passages from Specters of Marx,
then show me novels and poetry that engage with it. Use the theory-study template."
```

### Explore postmodern narrative strategies

```
"Research how postmodern and poststructuralist ideas about the instability
of meaning actually show up in fiction — Barth, Pynchon, Markson, Danielewski.
What are they doing on the page and what theory is behind it?"
```

### Trace literary connections

```
"My story deals with memory and photography. What's the literary tradition
here? Start with Barthes and Sontag but go wider — fiction, poetry,
anything that connects these two subjects."
```

## Tips

- **Tell the agent what you're writing.** Context about your project helps it find the most relevant sources.
- **Ask for real quotes.** The agent is built to find and cite actual passages, not summarize.
- **Check confidence levels.** `[verified]` means confirmed; `[high confidence]` means likely accurate; `[paraphrase]` means the idea is right but the wording may not be exact.
- **Request specific templates.** If you want a theme study vs. a quotes collection, say so.
- **Name authors you admire.** The agent can find connections between writers you already love and ones you haven't discovered yet.
- **Ask about translations.** When researching works from other languages, the agent will note translators and recommend specific translations.
