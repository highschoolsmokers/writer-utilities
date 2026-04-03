# GDoc to Scrivener

Converts a Google Doc outline into a Scrivener 3 (`.scriv`) project. Parses heading structure, Roman numeral sections, and research notes into a ready-to-use Scrivener binder with Manuscript folders, child text documents, and a Research section.

## How It Works

1. Fetches the Google Doc via the Docs API
2. Parses the document structure using heading levels (H1/H2) and Roman numeral patterns (I., II., III., etc.)
3. Separates content into manuscript sections and research documents
4. Generates a complete `.scriv` project with RTF content files, binder XML, and Scrivener settings

### Outline Conventions

- **H1/H2 headings with Roman numerals** (e.g. "I. The Beginning") become **Manuscript Folders**
- **Content under each heading** becomes **child Text documents**
- **Text before the first heading** becomes a standalone preamble document
- **Horizontal rules (`---`)** act as major section dividers
- A heading titled **"Research"** or **"Notes"** (case-insensitive) marks the start of research content
- Sections matching research keywords (throughlines, tonal rules, cut lists, etc.) also go into the **Research** folder

## Setup (One-Time)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use an existing one)
3. Enable the **Google Docs API**
4. Go to **Credentials** > **Create Credentials** > **OAuth 2.0 Client ID**
   - Application type: **Desktop app**
   - Download the JSON file
5. Save it as `~/.config/gdoc-to-scrivener/credentials.json`
6. Create a virtual environment and install dependencies:

```bash
python3 -m venv ~/code-data/gdoc-to-scrivener
~/code-data/gdoc-to-scrivener/bin/pip install -r requirements.txt
```

On first run, a browser window will open for OAuth consent. After that, the token is cached at `~/.config/gdoc-to-scrivener/token.json`.

## Usage

```bash
python gdoc_to_scrivener.py <google-doc-url-or-id> [options]
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `-n`, `--name` | Project name | Google Doc title |
| `-o`, `--output` | Output directory | `~/Documents/Writing/Scrivener` |
| `-a`, `--author` | Author name in Scrivener metadata | `W. S. Gong` |
| `--font` | RTF font family | `Palatino-Roman` |
| `--font-size` | Font size in points | `13` |
| `--dry-run` | Parse and display outline without creating files | — |
| `--open` | Open the project in Scrivener after creation (macOS) | — |

### Examples

```bash
# Basic: URL only (project name defaults to the doc title)
python gdoc_to_scrivener.py "https://docs.google.com/document/d/1h3k9GS.../edit"

# Custom project name and output directory
python gdoc_to_scrivener.py "https://docs.google.com/document/d/1h3k9GS.../edit" \
  --name "A Strange Day in July" \
  --output ~/Desktop

# Preview the parsed structure without writing anything
python gdoc_to_scrivener.py --dry-run "https://docs.google.com/document/d/1h3k9GS.../edit"

# Create and immediately open in Scrivener
python gdoc_to_scrivener.py "https://docs.google.com/document/d/1h3k9GS.../edit" --open

# Custom font (e.g. Times New Roman at 12pt)
python gdoc_to_scrivener.py "https://docs.google.com/document/d/1h3k9GS.../edit" \
  --font "Times-Roman" --font-size 12
```

## Output

Projects are created at:

```
<output-dir>/<project-name>.scriv/
```

If a project with the same name already exists, you'll be prompted before overwriting.

## Dependencies

- Python 3.11+
- `google-auth`
- `google-auth-oauthlib`
- `google-api-python-client`

Install via: `pip install -r requirements.txt`
