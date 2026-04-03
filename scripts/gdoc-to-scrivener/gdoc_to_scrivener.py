#!/usr/bin/env python3
"""
Google Doc to Scrivener — Standalone Script

Reads a Google Doc outline and creates a Scrivener 3 (.scriv) project.

SETUP (one-time):
    1. Go to https://console.cloud.google.com/
    2. Create a project (or use an existing one)
    3. Enable the "Google Docs API"
    4. Go to Credentials → Create Credentials → OAuth 2.0 Client ID
       - Application type: Desktop app
       - Download the JSON file
    5. Save it as  ~/.config/gdoc-to-scrivener/credentials.json
    6. Install dependencies:
       pip install -r requirements.txt

USAGE:
    python gdoc_to_scrivener.py <google-doc-url-or-id> [options]
    python gdoc_to_scrivener.py --help
"""

import argparse
import os
import re
import subprocess
import sys
import json
import uuid
import textwrap
from pathlib import Path
from datetime import datetime

# ── Configuration Defaults ────────────────────────────────────────────────

DEFAULT_OUTPUT_DIR = os.path.expanduser("~/Documents/Writing/Scrivener")
DEFAULT_AUTHOR = "W. S. Gong"
DEFAULT_FONT = "Palatino-Roman"
DEFAULT_FONT_SIZE = 13  # points (RTF uses half-points, so 13pt = \fs26)
CONFIG_DIR = os.path.expanduser("~/.config/gdoc-to-scrivener")
CREDENTIALS_FILE = os.path.join(CONFIG_DIR, "credentials.json")
TOKEN_FILE = os.path.join(CONFIG_DIR, "token.json")

SCOPES = ["https://www.googleapis.com/auth/documents.readonly"]


# ── Google Auth ────────────────────────────────────────────────────────────

def get_google_creds():
    """Authenticate with Google and return credentials.

    On first run, opens a browser for OAuth consent. After that, uses the
    saved token.
    """
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"ERROR: No credentials found at {CREDENTIALS_FILE}")
                print("See the setup instructions at the top of this script.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return creds


def fetch_google_doc(doc_id):
    """Fetch a Google Doc's full content via the Docs API.

    Returns the document object with title, body, and structural elements.
    """
    from googleapiclient.discovery import build

    creds = get_google_creds()
    service = build("docs", "v1", credentials=creds)
    return service.documents().get(documentId=doc_id).execute()


# ── Document Parsing ───────────────────────────────────────────────────────

def extract_doc_id(url_or_id):
    """Extract the Google Doc ID from a URL or return the ID as-is.

    Validates that bare IDs contain only alphanumeric characters, hyphens,
    and underscores.
    """
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url_or_id)
    if match:
        return match.group(1)

    # Validate bare ID: must be alphanumeric, hyphens, underscores, and
    # at least 10 characters (Google Doc IDs are ~44 chars)
    if not re.fullmatch(r"[a-zA-Z0-9_-]{10,}", url_or_id):
        print(f"ERROR: '{url_or_id}' does not look like a Google Doc URL or ID.")
        print("Expected: https://docs.google.com/document/d/<document-id>/edit")
        print("Or a bare document ID (alphanumeric, 10+ characters).")
        sys.exit(2)

    return url_or_id


def parse_outline(doc):
    """Parse a Google Doc into manuscript sections and research docs.

    Reads the document's structural elements and uses heading levels and
    horizontal rules (---) to determine the hierarchy:

    - Text before the first heading or rule → preamble (standalone Text doc)
    - H1 / H2 with "I.", "II.", etc. or section-like titles → Manuscript Folders
    - Content under each heading → child Text documents
    - A heading titled "Research" or "Notes" (case-insensitive) marks the
      start of research content; everything after goes into the Research folder
    - Sections matching research keywords (throughline, tonal rule, etc.)
      also go into Research as a fallback
    - Horizontal rules (---) act as major dividers
    """
    body = doc.get("body", {})
    content = body.get("content", [])

    # Extract all paragraphs with their heading level and text
    paragraphs = []
    for elem in content:
        if "paragraph" in elem:
            para = elem["paragraph"]
            style = para.get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")
            text = ""
            for run in para.get("elements", []):
                if "textRun" in run:
                    text += run["textRun"].get("content", "")
            text = text.strip()
            if text:
                paragraphs.append({"style": style, "text": text})
            elif text == "" and style == "NORMAL_TEXT":
                pass
        elif "sectionBreak" in elem:
            paragraphs.append({"style": "SECTION_BREAK", "text": "---"})

    # Also detect "---" as text-based dividers
    processed = []
    for p in paragraphs:
        if p["text"].strip() == "---":
            processed.append({"style": "DIVIDER", "text": "---"})
        else:
            processed.append(p)

    # Identify manuscript sections vs research sections
    roman_pattern = re.compile(r"^(I{1,3}|IV|V|VI{0,3}|IX|X)\.\s+")

    manuscript_sections = []
    research_docs = []
    current_folder = None
    current_children = []
    in_research = False
    preamble_text = []
    found_first_section = False

    # Keyword fallback for research detection
    research_keywords = [
        "throughline", "transformation", "tonal rule", "cutting to",
        "cut entirely", "cut significantly", "trim but keep", "the math",
        "rule for every"
    ]

    for p in processed:
        text = p["text"]
        style = p["style"]

        # Dividers signal transitions
        if style == "DIVIDER":
            if current_folder:
                manuscript_sections.append({
                    "title": current_folder,
                    "type": "Folder",
                    "children": current_children[:],
                })
                current_folder = None
                current_children = []
            continue

        is_heading = style in ("HEADING_1", "HEADING_2", "HEADING_3")
        is_roman = bool(roman_pattern.match(text))

        # Primary research detection: explicit "Research" or "Notes" heading
        is_research_heading = (
            is_heading and text.strip().lower() in ("research", "notes")
        )

        # Fallback: keyword-based research detection
        is_research_keyword = (
            is_heading
            and any(kw in text.lower() for kw in research_keywords)
        )

        if (is_research_heading or is_research_keyword) and found_first_section:
            # Flush current folder
            if current_folder:
                manuscript_sections.append({
                    "title": current_folder,
                    "type": "Folder",
                    "children": current_children[:],
                })
                current_folder = None
                current_children = []
            in_research = True

        if in_research:
            if is_heading:
                research_docs.append({"title": text, "content": ""})
            elif research_docs:
                if research_docs[-1]["content"]:
                    research_docs[-1]["content"] += "\n" + text
                else:
                    research_docs[-1]["content"] = text
            continue

        if (is_heading and is_roman) or (is_heading and not found_first_section and style == "HEADING_1"):
            found_first_section = True

            if preamble_text and not any(s.get("title") == preamble_text[0] for s in manuscript_sections):
                if len(preamble_text) > 1:
                    manuscript_sections.append({
                        "title": preamble_text[0],
                        "type": "Text",
                        "content": "\n\n".join(preamble_text[1:]),
                    })
                elif preamble_text:
                    manuscript_sections.append({
                        "title": preamble_text[0],
                        "type": "Text",
                        "content": preamble_text[0],
                    })
                preamble_text = []

            if current_folder:
                manuscript_sections.append({
                    "title": current_folder,
                    "type": "Folder",
                    "children": current_children[:],
                })

            current_folder = text
            current_children = []

        elif found_first_section and current_folder:
            current_children.append((text, text))

        elif not found_first_section:
            if is_heading:
                if preamble_text:
                    manuscript_sections.append({
                        "title": preamble_text[0],
                        "type": "Text",
                        "content": "\n\n".join(preamble_text[1:]) if len(preamble_text) > 1 else preamble_text[0],
                    })
                    preamble_text = [text]
                else:
                    preamble_text.append(text)
            else:
                preamble_text.append(text)

    # Flush last folder
    if current_folder:
        manuscript_sections.append({
            "title": current_folder,
            "type": "Folder",
            "children": current_children[:],
        })

    # Flush any remaining preamble
    if preamble_text and not found_first_section:
        manuscript_sections.append({
            "title": preamble_text[0],
            "type": "Text",
            "content": "\n\n".join(preamble_text[1:]) if len(preamble_text) > 1 else preamble_text[0],
        })

    return manuscript_sections, research_docs


# ── Scrivener Builder ──────────────────────────────────────────────────────

def generate_uid():
    return str(uuid.uuid4()).upper()


def text_to_rtf(text, font_family=DEFAULT_FONT, font_size_pts=DEFAULT_FONT_SIZE):
    """Convert plain text to a minimal RTF document.

    Args:
        text: Plain text content.
        font_family: RTF font family name (e.g. "Palatino-Roman", "Times-Roman").
        font_size_pts: Font size in points. Converted to RTF half-points internally.
    """
    fs = font_size_pts * 2  # RTF \fs uses half-points
    text = text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
    text = text.replace("\n", " \\\n")
    return textwrap.dedent(f"""\
        {{\\rtf1\\ansi\\ansicpg1252\\cocoartf2709
        \\cocoatextscaling0\\cocoaplatform0{{\\fonttbl\\f0\\froman\\fcharset0 {font_family};}}
        {{\\colortbl;\\red255\\green255\\blue255;}}
        {{\\*\\expandedcolortbl;;}}
        \\pard\\tx360\\tx720\\tx1080\\tx1440\\tx1800\\tx2160\\tx2880\\tx3600\\tx4320\\fi360\\sl264\\slmult1\\pardirnatural\\partightenfactor0

        \\f0\\fs{fs} \\cf0 {text}}}""")


def build_scrivener_project(project_name, output_dir, manuscript_sections,
                             research_docs, author=DEFAULT_AUTHOR,
                             font_family=DEFAULT_FONT,
                             font_size_pts=DEFAULT_FONT_SIZE):
    """Build the complete .scriv project. Returns the path."""
    scriv_dir = os.path.join(output_dir, f"{project_name}.scriv")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S -0700")

    # Abort if project already exists
    if os.path.exists(scriv_dir):
        print(f"WARNING: {scriv_dir} already exists!")
        response = input("Overwrite? (y/N): ").strip().lower()
        if response != "y":
            print("Aborted.")
            sys.exit(0)
        import shutil
        shutil.rmtree(scriv_dir)

    os.makedirs(os.path.join(scriv_dir, "Files", "Data"), exist_ok=True)
    os.makedirs(os.path.join(scriv_dir, "Settings"), exist_ok=True)

    # Fixed UUIDs for standard folders
    draft_uuid = generate_uid()
    research_uuid = generate_uid()
    trash_uuid = generate_uid()
    notes_uuid = generate_uid()

    def make_data_dir(uid):
        d = os.path.join(scriv_dir, "Files", "Data", uid)
        os.makedirs(d, exist_ok=True)
        return d

    def write_content(uid, text):
        d = make_data_dir(uid)
        with open(os.path.join(d, "content.rtf"), "w") as f:
            f.write(text_to_rtf(text, font_family, font_size_pts))

    def indent_xml(xml, levels=1):
        indent = "    " * levels
        return '\n'.join(indent + line if line.strip() else line for line in xml.split('\n'))

    def binder_item(title, uid, btype="Text", children_xml=""):
        children_block = ""
        if children_xml:
            children_block = f"\n            <Children>\n{children_xml}            </Children>"
        return f"""        <BinderItem UUID="{uid}" Type="{btype}" Created="{now}" Modified="{now}">
            <Title>{title}</Title>
            <MetaData>
                <IncludeInCompile>Yes</IncludeInCompile>
            </MetaData>
            <TextSettings>
                <TextSelection>0,0</TextSelection>
            </TextSettings>{children_block}
        </BinderItem>
"""

    # Build Manuscript children
    ms_children = ""
    for section in manuscript_sections:
        if section["type"] == "Folder":
            child_xml = ""
            for child_title, child_content in section.get("children", []):
                cuid = generate_uid()
                write_content(cuid, child_content)
                child_xml += indent_xml(binder_item(child_title, cuid, "Text"), 2)
            fuid = generate_uid()
            make_data_dir(fuid)
            ms_children += indent_xml(binder_item(section["title"], fuid, "Folder", child_xml), 1)
        elif section["type"] == "Text":
            tuid = generate_uid()
            write_content(tuid, section.get("content", ""))
            ms_children += indent_xml(binder_item(section["title"], tuid, "Text"), 1)

    # Build Research children
    res_children = ""
    for doc in research_docs:
        duid = generate_uid()
        write_content(duid, doc["content"])
        res_children += indent_xml(binder_item(doc["title"], duid, "Text"), 2)

    for uid in [draft_uuid, research_uuid, trash_uuid, notes_uuid]:
        make_data_dir(uid)

    # Write .scrivx
    scrivx = f"""<?xml version="1.0" encoding="UTF-8"?>
<ScrivenerProject Identifier="{generate_uid()}" Version="2.0" Creator="SCRMAC-3.2.3-14869" Device="Gong" Author="{author}" Modified="{now}" ModID="{generate_uid()}">
    <Binder>
        <BinderItem UUID="{draft_uuid}" Type="DraftFolder" Created="{now}" Modified="{now}">
            <Title>Manuscript</Title>
            <Children>
{ms_children}            </Children>
        </BinderItem>
        <BinderItem UUID="{notes_uuid}" Type="Folder" Created="{now}" Modified="{now}">
            <Title>Notes</Title>
            <MetaData>
                <IncludeInCompile>Yes</IncludeInCompile>
                <IconFileName>Notes (Yellow Notepad)</IconFileName>
            </MetaData>
            <TextSettings>
                <TextSelection>0,0</TextSelection>
            </TextSettings>
        </BinderItem>
        <BinderItem UUID="{research_uuid}" Type="ResearchFolder" Created="{now}" Modified="{now}">
            <Title>Research</Title>
            <Children>
{res_children}            </Children>
        </BinderItem>
        <BinderItem UUID="{trash_uuid}" Type="TrashFolder" Created="{now}" Modified="{now}">
            <Title>Trash</Title>
        </BinderItem>
    </Binder>
    <Collections>
        <Collection Type="Binder" ID="{generate_uid()}" Color="1.0 1.0 1.0">
            <Title>Binder</Title>
        </Collection>
        <Collection Type="RecentSearch" ID="{generate_uid()}" Color="0.922173 0.818612 0.999627">
            <Title>Search Results</Title>
        </Collection>
    </Collections>
    <SectionTypes>
        <TypeDefinitions>
            <Type ID="{generate_uid()}">Scene</Type>
            <Type ID="{generate_uid()}">N/A</Type>
        </TypeDefinitions>
    </SectionTypes>
    <LabelSettings>
        <Title>Label</Title>
        <DefaultLabelID>-1</DefaultLabelID>
        <Labels>
            <Label ID="-1">No Label</Label>
            <Label ID="7" Color="0.993495 0.701207 0.732587">Red</Label>
            <Label ID="8" Color="0.995418 0.790946 0.652385">Orange</Label>
            <Label ID="9" Color="0.997722 0.89273 0.652569">Yellow</Label>
            <Label ID="10" Color="0.715855 0.948712 0.697692">Green</Label>
            <Label ID="11" Color="0.702319 0.888276 0.974252">Blue</Label>
            <Label ID="12" Color="0.957566 0.766747 0.999616">Purple</Label>
        </Labels>
    </LabelSettings>
    <StatusSettings>
        <Title>Status</Title>
        <DefaultStatusID>-1</DefaultStatusID>
        <StatusItems>
            <Status ID="-1">No Status</Status>
            <Status ID="1">To Do</Status>
            <Status ID="2">First Draft</Status>
            <Status ID="3">Revised Draft</Status>
            <Status ID="4">Final Draft</Status>
            <Status ID="5">Done</Status>
        </StatusItems>
    </StatusSettings>
    <PrintSettings PaperSize="611.999975,792.0" LeftMargin="72.0" RightMargin="72.0" TopMargin="90.0" BottomMargin="90.0" PaperType="na-letter" Orientation="Portrait" HorizontalPagination="Clip" VerticalPagination="Auto" ScaleFactor="1.0" HorizontallyCentered="Yes" VerticallyCentered="Yes" Collates="Yes" PagesAcross="1" PagesDown="1"/>
</ScrivenerProject>"""

    with open(os.path.join(scriv_dir, f"{project_name}.scrivx"), "w") as f:
        f.write(scrivx)

    # Supporting files
    with open(os.path.join(scriv_dir, "Files", "version.txt"), "w") as f:
        f.write("23")
    with open(os.path.join(scriv_dir, "Files", "search.indexes"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<SearchIndexes Version="2.0">\n</SearchIndexes>')
    with open(os.path.join(scriv_dir, "Files", "writing.history"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<WritingHistory/>')
    with open(os.path.join(scriv_dir, "Files", "styles.xml"), "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<Styles>
    <Style Name="Title" ID="{generate_uid()}" Type="Para+Char" FontChange="Size">
        <Format><![CDATA[{{\\rtf1\\ansi\\ansicpg1252\\cocoartf2709
\\cocoatextscaling0\\cocoaplatform0{{\\fonttbl\\f0\\froman\\fcharset0 {font_family};}}
{{\\colortbl;\\red255\\green255\\blue255;}}
{{\\*\\expandedcolortbl;;}}
\\pard\\tx560\\tx1120\\sl264\\slmult1\\sb260\\pardirnatural\\partightenfactor0

\\f0\\fs56 \\cf0 <$ScrKeepWithNext>Attributes}}]]></Format>
    </Style>
</Styles>""")

    with open(os.path.join(scriv_dir, "Settings", "ui-common.xml"), "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<UICommon>
    <SelectedEditor>Left</SelectedEditor>
    <LeftEditor>
        <SelectedUUIDs><UUID>{draft_uuid}</UUID></SelectedUUIDs>
        <ViewMode>Outline</ViewMode>
    </LeftEditor>
</UICommon>""")
    with open(os.path.join(scriv_dir, "Settings", "compile.xml"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<CompileSettings/>')
    with open(os.path.join(scriv_dir, "Settings", "favorites.xml"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<Favorites/>')
    with open(os.path.join(scriv_dir, "Settings", "recents.txt"), "w") as f:
        f.write("")

    # Count results
    data_base = os.path.join(scriv_dir, "Files", "Data")
    dirs = [d for d in os.listdir(data_base) if os.path.isdir(os.path.join(data_base, d))]
    rtfs = sum(1 for d in dirs if os.path.exists(os.path.join(data_base, d, "content.rtf")))

    return scriv_dir, len(dirs), rtfs


def print_outline(manuscript_sections, research_docs):
    """Print the parsed outline structure."""
    print(f"  Manuscript sections: {len(manuscript_sections)}")
    for s in manuscript_sections:
        if s["type"] == "Folder":
            print(f"    Folder: {s['title']} ({len(s.get('children', []))} items)")
        else:
            print(f"    Doc: {s['title']}")
    print(f"  Research docs: {len(research_docs)}")
    for r in research_docs:
        print(f"    Doc: {r['title']}")


# ── CLI ───────────────────────────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        description="Convert a Google Doc outline into a Scrivener 3 project.",
        epilog="On first run, a browser window opens for Google OAuth consent.",
    )
    parser.add_argument(
        "doc_url",
        help="Google Doc URL or document ID",
    )
    parser.add_argument(
        "-n", "--name",
        help="Project name (default: Google Doc title)",
    )
    parser.add_argument(
        "-o", "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "-a", "--author",
        default=DEFAULT_AUTHOR,
        help=f"Author name in Scrivener metadata (default: {DEFAULT_AUTHOR})",
    )
    parser.add_argument(
        "--font",
        default=DEFAULT_FONT,
        help=f"RTF font family (default: {DEFAULT_FONT})",
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=DEFAULT_FONT_SIZE,
        help=f"Font size in points (default: {DEFAULT_FONT_SIZE})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and display outline structure without creating files",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        dest="open_after",
        help="Open the .scriv project in Scrivener after creation (macOS)",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    doc_id = extract_doc_id(args.doc_url.strip())

    project_name = args.name

    # Fetch the doc
    print(f"Fetching Google Doc {doc_id}...")
    try:
        doc = fetch_google_doc(doc_id)
    except FileNotFoundError:
        print(f"ERROR: No Google credentials found at {CREDENTIALS_FILE}")
        print("See setup instructions at the top of this script.")
        sys.exit(3)
    except Exception as e:
        err = str(e).lower()
        if "invalid_grant" in err or "invalid_client" in err or "credentials" in err:
            print("ERROR: Google authentication failed.")
            print(f"Details: {e}")
            print(f"Try deleting {TOKEN_FILE} and running again.")
            sys.exit(3)
        elif "404" in err or "not found" in err:
            print("ERROR: Document not found. Check the URL and make sure you have access.")
            sys.exit(2)
        elif "403" in err or "permission" in err or "forbidden" in err:
            print("ERROR: You don't have permission to access this document.")
            print("Make sure the doc is shared with your Google account.")
            sys.exit(2)
        else:
            print("ERROR: Could not fetch document.")
            print(f"Details: {e}")
            sys.exit(1)

    if not project_name:
        project_name = doc.get("title", "Untitled Project")
    print(f"Project name: {project_name}")

    print("Parsing outline...")
    manuscript_sections, research_docs = parse_outline(doc)

    if not manuscript_sections:
        print("ERROR: Could not find any outline structure in this document.")
        print("Make sure the doc has headings (H1/H2) or Roman numeral sections.")
        sys.exit(1)

    print_outline(manuscript_sections, research_docs)

    if args.dry_run:
        print("\n--dry-run: no files written.")
        sys.exit(0)

    output_dir = os.path.expanduser(args.output)
    os.makedirs(output_dir, exist_ok=True)
    print(f"\nBuilding Scrivener project in {output_dir}...")

    scriv_dir, item_count, rtf_count = build_scrivener_project(
        project_name, output_dir, manuscript_sections, research_docs,
        author=args.author,
        font_family=args.font,
        font_size_pts=args.font_size,
    )

    print(f"\nDone! Created {scriv_dir}")
    print(f"  {item_count} binder items, {rtf_count} RTF documents")

    if args.open_after:
        print(f"Opening in Scrivener...")
        subprocess.run(["open", scriv_dir])
    else:
        print(f"\nOpen in Scrivener:  open \"{scriv_dir}\"")


if __name__ == "__main__":
    main()
