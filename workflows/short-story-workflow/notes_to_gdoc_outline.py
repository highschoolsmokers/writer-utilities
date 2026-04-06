#!/usr/bin/env python3
"""
notes_to_gdoc_outline.py
─────────────────────────
Reads notes from a single file — Google Doc, .docx, .pdf, .txt, or .rtf —
and compiles them into a structured outline (flat bullet list) in a new
Google Doc, placed in a specified Drive folder.

Usage (standalone with OAuth):
    # From a Google Doc (by name or ID/URL)
    python notes_to_gdoc_outline.py --doc "My Story Notes"
    python notes_to_gdoc_outline.py --doc-id "1abc...xyz"

    # From a local file (.docx, .pdf, .txt, .rtf)
    python notes_to_gdoc_outline.py --file notes.docx
    python notes_to_gdoc_outline.py --file research.pdf --output-folder "Outlines"
    python notes_to_gdoc_outline.py --file brainstorm.txt --title "My Outline"

Usage (in Cowork / Claude Code with MCP):
    Called automatically by the agentic workflow — no CLI needed.

Requirements:
    pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
    pip install python-docx    # for .docx
    pip install PyPDF2         # for .pdf
    pip install striprtf       # for .rtf

Setup (for Google Docs source or output):
    1. Create a Google Cloud project at https://console.cloud.google.com
    2. Enable the Google Docs API and Google Drive API
    3. Create OAuth 2.0 credentials (Desktop app) and download as credentials.json
    4. Place credentials.json next to this script
    5. On first run, a browser window opens for consent. Token is cached in token.json.
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ─── Google API imports ───────────────────────────────────────────────
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    HAS_GOOGLE_API = True
except ImportError:
    HAS_GOOGLE_API = False

# If modifying these scopes, delete token.json and re-authorize.
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]


# ─── Authentication ───────────────────────────────────────────────────

def authenticate(credentials_path="credentials.json", token_path="token.json"):
    """Authenticate with Google APIs via OAuth 2.0 and return a Credentials object."""
    creds = None

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                print(f"ERROR: {credentials_path} not found.")
                print("Download OAuth credentials from Google Cloud Console.")
                print("See script docstring for setup instructions.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return creds


# ─── Drive helpers ────────────────────────────────────────────────────

def find_doc_by_name(drive_service, doc_name):
    """Search for a Google Doc by name. Returns (doc_id, doc_name) or None."""
    q = (
        f"name = '{doc_name}' "
        f"and mimeType = 'application/vnd.google-apps.document' "
        f"and trashed = false"
    )
    results = drive_service.files().list(q=q, fields="files(id, name)", pageSize=5).execute()
    files = results.get("files", [])
    return (files[0]["id"], files[0]["name"]) if files else None


def find_folder_by_name(drive_service, folder_name, parent_id=None):
    """Search for a Drive folder by name. Returns the folder ID or None."""
    q = (
        f"name = '{folder_name}' "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )
    if parent_id:
        q += f" and '{parent_id}' in parents"

    results = drive_service.files().list(q=q, fields="files(id, name)", pageSize=10).execute()
    files = results.get("files", [])
    return files[0]["id"] if files else None


def get_or_create_folder(drive_service, folder_name, parent_id=None):
    """Find a folder by name, or create it if it doesn't exist. Returns folder ID."""
    existing = find_folder_by_name(drive_service, folder_name, parent_id)
    if existing:
        return existing

    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    folder = drive_service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def extract_doc_id_from_url(url_or_id):
    """Extract a Google Doc ID from a URL, or return the string as-is if it's already an ID."""
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', url_or_id)
    if match:
        return match.group(1)
    if '/' not in url_or_id and len(url_or_id) > 10:
        return url_or_id
    return None


# ═══════════════════════════════════════════════════════════════════════
#  FILE READERS — each returns the same structure:
#    {"title": str, "sections": [{"heading": str|None, "lines": [str]}]}
# ═══════════════════════════════════════════════════════════════════════

def read_google_doc(docs_service, doc_id):
    """Read a Google Doc via the Docs API."""
    doc = docs_service.documents().get(documentId=doc_id).execute()
    title = doc.get("title", "Untitled")

    sections = []
    current_section = {"heading": None, "lines": []}

    for element in doc.get("body", {}).get("content", []):
        paragraph = element.get("paragraph")
        if not paragraph:
            continue

        text_parts = []
        for run in paragraph.get("elements", []):
            text_run = run.get("textRun")
            if text_run:
                text_parts.append(text_run.get("content", ""))
        line = "".join(text_parts).rstrip("\n")

        if not line.strip():
            continue

        style = paragraph.get("paragraphStyle", {})
        named_style = style.get("namedStyleType", "NORMAL_TEXT")

        if named_style.startswith("HEADING"):
            if current_section["heading"] or current_section["lines"]:
                sections.append(current_section)
            current_section = {"heading": line.strip(), "lines": []}
        else:
            current_section["lines"].append(line.strip())

    if current_section["heading"] or current_section["lines"]:
        sections.append(current_section)

    return {"title": title, "sections": sections}


def read_docx_file(filepath):
    """Read a .docx file using python-docx. Heading styles map to section headings."""
    try:
        from docx import Document
    except ImportError:
        print("ERROR: python-docx not installed. Run: pip install python-docx")
        sys.exit(1)

    doc = Document(filepath)
    title = Path(filepath).stem

    sections = []
    current_section = {"heading": None, "lines": []}

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # python-docx style names: 'Heading 1', 'Heading 2', etc.
        style_name = para.style.name if para.style else ""

        if style_name.startswith("Heading"):
            if current_section["heading"] or current_section["lines"]:
                sections.append(current_section)
            current_section = {"heading": text, "lines": []}
        else:
            current_section["lines"].append(text)

    if current_section["heading"] or current_section["lines"]:
        sections.append(current_section)

    return {"title": title, "sections": sections}


def read_pdf_file(filepath):
    """Read a .pdf file using PyPDF2. Each page's text is treated as a section."""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        print("ERROR: PyPDF2 not installed. Run: pip install PyPDF2")
        sys.exit(1)

    reader = PdfReader(filepath)
    title = Path(filepath).stem

    sections = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        if not lines:
            continue

        # Heuristic: if first line looks like a heading (short, no punctuation),
        # treat it as a section heading
        first_line = lines[0]
        is_heading = (
            len(first_line) < 80
            and not first_line.endswith((".", ",", ";", ":", "!"))
            and not any(c.isdigit() and c != first_line[0] for c in first_line[:3])
        )

        if is_heading and len(lines) > 1:
            sections.append({
                "heading": first_line,
                "lines": lines[1:],
            })
        else:
            sections.append({
                "heading": f"Page {i + 1}" if len(reader.pages) > 1 else None,
                "lines": lines,
            })

    return {"title": title, "sections": sections}


def read_txt_file(filepath):
    """
    Read a .txt file. Lines that look like headings (ALL CAPS, lines followed
    by === or ---, or short standalone lines after a blank line) become sections.
    """
    title = Path(filepath).stem

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        raw_lines = f.readlines()

    sections = []
    current_section = {"heading": None, "lines": []}
    prev_blank = True  # treat start of file as preceded by a blank line

    for i, raw in enumerate(raw_lines):
        line = raw.rstrip("\n").strip()

        # Blank line
        if not line:
            prev_blank = True
            continue

        # Check for underline-style headings (next line is === or ---)
        next_line = raw_lines[i + 1].strip() if i + 1 < len(raw_lines) else ""
        is_underlined = bool(re.match(r'^[=\-]{3,}$', next_line))

        # Heuristic for heading: ALL CAPS line, or short line after blank
        is_allcaps = line == line.upper() and len(line) > 2 and line.isalpha()
        is_short_after_blank = prev_blank and len(line) < 60 and not line.endswith((".", ",", ";"))

        if is_underlined or is_allcaps or (is_short_after_blank and len(line) < 40):
            if current_section["heading"] or current_section["lines"]:
                sections.append(current_section)
            current_section = {"heading": line, "lines": []}
        else:
            current_section["lines"].append(line)

        prev_blank = False

    if current_section["heading"] or current_section["lines"]:
        sections.append(current_section)

    return {"title": title, "sections": sections}


def read_rtf_file(filepath):
    """Read an .rtf file using striprtf, then parse like plain text."""
    try:
        from striprtf.striprtf import rtf_to_text
    except ImportError:
        print("ERROR: striprtf not installed. Run: pip install striprtf")
        sys.exit(1)

    title = Path(filepath).stem

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        rtf_content = f.read()

    plain_text = rtf_to_text(rtf_content)

    # Write to a temp approach: reuse the txt parser on the extracted text
    lines = plain_text.split("\n")

    sections = []
    current_section = {"heading": None, "lines": []}
    prev_blank = True

    for i, raw in enumerate(lines):
        line = raw.strip()

        if not line:
            prev_blank = True
            continue

        next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
        is_underlined = bool(re.match(r'^[=\-]{3,}$', next_line))
        is_allcaps = line == line.upper() and len(line) > 2 and line.replace(" ", "").isalpha()
        is_short_after_blank = prev_blank and len(line) < 40 and not line.endswith((".", ",", ";"))

        if is_underlined or is_allcaps or is_short_after_blank:
            if current_section["heading"] or current_section["lines"]:
                sections.append(current_section)
            current_section = {"heading": line, "lines": []}
        else:
            current_section["lines"].append(line)

        prev_blank = False

    if current_section["heading"] or current_section["lines"]:
        sections.append(current_section)

    return {"title": title, "sections": sections}


def read_local_file(filepath):
    """Dispatch to the right reader based on file extension."""
    ext = Path(filepath).suffix.lower()

    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)

    readers = {
        ".docx": read_docx_file,
        ".pdf": read_pdf_file,
        ".txt": read_txt_file,
        ".rtf": read_rtf_file,
        ".md": read_txt_file,   # markdown also works with the txt parser
    }

    reader = readers.get(ext)
    if not reader:
        supported = ", ".join(readers.keys())
        print(f"ERROR: Unsupported file type '{ext}'. Supported: {supported}")
        sys.exit(1)

    return reader(filepath)


# ─── Outline compilation ─────────────────────────────────────────────

def compile_outline(doc_content, outline_title=None):
    """
    Compile a single doc's notes into an outline string (flat bullet list).

    Headings become top-level bullets (•).
    Body text under headings becomes nested bullets (◦).
    Text with no heading becomes top-level bullets.
    Long paragraphs are split into sentences.

    Returns: (title, outline_text)
    """
    if not outline_title:
        source_title = doc_content.get("title", "Untitled")
        outline_title = f"Outline — {source_title}"

    lines = [f"{outline_title}\n"]

    for section in doc_content["sections"]:
        if section["heading"]:
            lines.append(f"• {section['heading']}")

            for body_line in section["lines"]:
                if len(body_line) > 200:
                    sentences = re.split(r'(?<=[.!?])\s+', body_line)
                    for sentence in sentences:
                        if sentence.strip():
                            lines.append(f"  ◦ {sentence.strip()}")
                else:
                    lines.append(f"  ◦ {body_line}")
        else:
            for body_line in section["lines"]:
                lines.append(f"• {body_line}")

    return outline_title, "\n".join(lines)


# ─── Doc creation ─────────────────────────────────────────────────────

def create_outline_doc(docs_service, drive_service, title, content, folder_id=None):
    """
    Create a new Google Doc with the outline content and optionally move it
    to a specific folder. Returns: (doc_id, doc_url)
    """
    doc = docs_service.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]

    requests = [
        {"insertText": {"location": {"index": 1}, "text": content}}
    ]
    docs_service.documents().batchUpdate(
        documentId=doc_id, body={"requests": requests}
    ).execute()

    if folder_id:
        file_info = drive_service.files().get(fileId=doc_id, fields="parents").execute()
        current_parents = ",".join(file_info.get("parents", []))
        drive_service.files().update(
            fileId=doc_id,
            addParents=folder_id,
            removeParents=current_parents,
            fields="id, parents",
        ).execute()

    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    return doc_id, doc_url


# ─── Main workflow ────────────────────────────────────────────────────

def run(doc_name=None, doc_id=None, local_file=None,
        output_folder_name=None, outline_title=None,
        credentials_path="credentials.json"):
    """
    Full pipeline: read source → compile outline → create Google Doc.

    Source can be:
      - doc_name: search Google Drive by name
      - doc_id: Google Doc ID or URL
      - local_file: path to a .docx, .pdf, .txt, or .rtf file

    Returns:
        dict with doc_id, doc_url, title, source
    """
    source_count = sum(1 for x in [doc_name, doc_id, local_file] if x)
    if source_count == 0:
        print("ERROR: Provide one of --doc, --doc-id, or --file.")
        sys.exit(1)
    if source_count > 1:
        print("ERROR: Provide only one source (--doc, --doc-id, or --file).")
        sys.exit(1)

    # ── Read the source ──────────────────────────────────────────────
    drive_service = None
    docs_service = None

    if local_file:
        # Local file — no Google auth needed for reading
        print(f"Reading local file: {local_file}")
        doc_content = read_local_file(local_file)
        source_label = os.path.basename(local_file)
    else:
        # Google Doc — need auth
        if not HAS_GOOGLE_API:
            print("ERROR: Google API libraries not installed.")
            print("Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
            sys.exit(1)

        print("Authenticating with Google...")
        creds = authenticate(credentials_path)
        drive_service = build("drive", "v3", credentials=creds)
        docs_service = build("docs", "v1", credentials=creds)

        if doc_id:
            resolved_id = extract_doc_id_from_url(doc_id)
            if not resolved_id:
                print(f"ERROR: Could not parse doc ID from '{doc_id}'.")
                sys.exit(1)
            source_id = resolved_id
            print(f"Using doc ID: {source_id}")
        elif doc_name and ("docs.google.com" in doc_name or "drive.google.com" in doc_name):
            # User passed a URL via --doc instead of --doc-id — handle it gracefully
            resolved_id = extract_doc_id_from_url(doc_name)
            if not resolved_id:
                print(f"ERROR: Could not parse doc ID from URL '{doc_name}'.")
                sys.exit(1)
            source_id = resolved_id
            print(f"Detected URL → doc ID: {source_id}")
        else:
            print(f"Searching for doc: '{doc_name}'...")
            result = find_doc_by_name(drive_service, doc_name)
            if not result:
                print(f"ERROR: No Google Doc named '{doc_name}' found.")
                sys.exit(1)
            source_id, found_name = result
            print(f"Found: '{found_name}' ({source_id})")

        print("Reading note contents...")
        doc_content = read_google_doc(docs_service, source_id)
        source_label = doc_content["title"]

    section_count = len(doc_content["sections"])
    line_count = sum(len(s["lines"]) for s in doc_content["sections"])
    print(f"  ✓ '{doc_content['title']}' — {section_count} section(s), {line_count} line(s)")

    # ── Compile outline ──────────────────────────────────────────────
    print("Compiling outline...")
    title, outline_text = compile_outline(doc_content, outline_title)

    # ── Create output Google Doc ─────────────────────────────────────
    # Need Google auth for output even if source was local
    if not docs_service:
        if not HAS_GOOGLE_API:
            print("ERROR: Google API libraries needed to create the output doc.")
            print("Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
            sys.exit(1)
        print("Authenticating with Google (for output)...")
        creds = authenticate(credentials_path)
        drive_service = build("drive", "v3", credentials=creds)
        docs_service = build("docs", "v1", credentials=creds)

    output_folder_id = None
    if output_folder_name:
        output_folder_id = get_or_create_folder(drive_service, output_folder_name)
        print(f"Output folder: '{output_folder_name}'")

    print("Creating outline document in Google Docs...")
    new_doc_id, doc_url = create_outline_doc(
        docs_service, drive_service, title, outline_text, output_folder_id
    )

    print(f"\n{'─' * 50}")
    print(f"✓ Outline created successfully!")
    print(f"  Title:    {title}")
    print(f"  Source:   {source_label}")
    print(f"  Sections: {section_count}")
    print(f"  URL:      {doc_url}")
    print(f"{'─' * 50}")

    return {
        "doc_id": new_doc_id,
        "doc_url": doc_url,
        "title": title,
        "source": source_label,
    }


# ─── Cowork / MCP helper ─────────────────────────────────────────────

def compile_outline_from_text(doc_content, outline_title=None):
    """
    Standalone function for use in Cowork/MCP workflows.
    Accepts the standard doc_content dict, returns (title, outline_text).
    """
    return compile_outline(doc_content, outline_title)


# ─── CLI entry point ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Compile notes into a structured outline in Google Docs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported input formats:
  Google Doc     --doc "Name" or --doc-id "ID/URL"
  Word           --file notes.docx
  PDF            --file research.pdf
  Plain text     --file brainstorm.txt
  RTF            --file draft.rtf
  Markdown       --file notes.md

Examples:
  %(prog)s --doc "My Story Notes"
  %(prog)s --doc-id "https://docs.google.com/document/d/1abc.../edit"
  %(prog)s --file ~/Documents/story-notes.docx --output-folder "Outlines"
  %(prog)s --file notes.txt --title "Memory Stories — Outline"
        """,
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--doc", "-d",
        default=None,
        help="Name of a Google Doc containing your notes (searches Drive)",
    )
    source.add_argument(
        "--doc-id",
        default=None,
        help="Google Doc ID or full URL",
    )
    source.add_argument(
        "--file", "-f",
        default=None,
        help="Path to a local file (.docx, .pdf, .txt, .rtf, .md)",
    )

    parser.add_argument(
        "--output-folder", "-o",
        default=None,
        help="Google Drive folder for the outline doc (created if needed)",
    )
    parser.add_argument(
        "--title", "-t",
        default=None,
        help="Title for the outline doc (default: 'Outline — <source title>')",
    )
    parser.add_argument(
        "--credentials", "-c",
        default="credentials.json",
        help="Path to Google OAuth credentials.json (default: ./credentials.json)",
    )

    args = parser.parse_args()

    result = run(
        doc_name=args.doc,
        doc_id=args.doc_id,
        local_file=args.file,
        output_folder_name=args.output_folder,
        outline_title=args.title,
        credentials_path=args.credentials,
    )

    print(result["doc_url"])


if __name__ == "__main__":
    main()
