# Notes-to-GDoc Outline — Setup Guide

## Two ways to use this tool

### Option A: Inside Cowork (no setup needed)

If you're running this from a Cowork session with Google Drive connected, just ask:

> "Compile the notes in [doc name] into an outline in Google Docs"

The workflow will use your connected Google Drive MCP tools directly — no credentials, no installs.

### Option B: Standalone Python script

For running from your terminal outside of Cowork.

#### 1. Install dependencies

```bash
pip install -r requirements.txt
```

#### 2. Set up Google Cloud credentials

Only needed if your source is a Google Doc, or for creating the output doc (always required).

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use an existing one)
3. Enable **Google Docs API** and **Google Drive API**
4. Go to **Credentials → Create Credentials → OAuth 2.0 Client ID**
5. Choose "Desktop app" as the application type
6. Download the JSON file and save it as `credentials.json` next to the script

#### 3. Run the script

```bash
# From a Google Doc (by name)
python notes_to_gdoc_outline.py --doc "My Story Notes"

# From a Google Doc (by ID or URL)
python notes_to_gdoc_outline.py --doc-id "1abc...xyz"
python notes_to_gdoc_outline.py --doc-id "https://docs.google.com/document/d/1abc...xyz/edit"

# From a local Word doc
python notes_to_gdoc_outline.py --file story-notes.docx

# From a PDF
python notes_to_gdoc_outline.py --file research.pdf --output-folder "Outlines"

# From plain text or RTF
python notes_to_gdoc_outline.py --file brainstorm.txt --title "Memory Stories — Outline"
python notes_to_gdoc_outline.py --file draft-notes.rtf

# With custom credentials path
python notes_to_gdoc_outline.py --file notes.docx --credentials ~/path/to/credentials.json
```

On first run, a browser window will open for Google consent. After that, your token is cached in `token.json`.

## Supported input formats

| Format | Flag | How headings are detected |
|--------|------|--------------------------|
| Google Doc | `--doc` or `--doc-id` | Native heading styles (H1, H2, etc.) |
| Word (.docx) | `--file` | Word heading styles (Heading 1, 2, etc.) |
| PDF (.pdf) | `--file` | First line of each page if short and unpunctuated |
| Plain text (.txt, .md) | `--file` | ALL CAPS lines, underlined headings (===), short lines after blanks |
| RTF (.rtf) | `--file` | Same heuristics as plain text after RTF stripping |

## How it works

1. Reads the source file and parses it into sections (heading + body lines)
2. Compiles into a flat bullet-list outline:
   - Headings become top-level `•` bullets
   - Body text under headings becomes nested `◦` bullets
   - Long paragraphs (200+ chars) are split into sentence-level bullets
3. Creates a new Google Doc with the compiled outline
4. Moves it to your specified output folder (or Drive root if none given)

## Part of the short-story workflow

This is step 1 of the pipeline:

1. **notes_to_gdoc_outline.py** — compile notes → GDoc outline ← you are here
2. Import outline into Scrivener (via gdoc-to-scrivener skill)
3. Export finished story + auto-generate cover letter
