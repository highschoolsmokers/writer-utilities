#!/usr/bin/env python3
"""
notes_to_bike.py
────────────────
Reads notes from a single file — Google Doc, .docx, .pdf, .txt, or .rtf —
and exports them as a .bike file (Bike Outliner format).

The .bike format is a restricted subset of HTML: a nested <ul>/<li>/<p>
structure where each row has a unique id and an optional data-type attribute
(heading, note, task, ordered, unordered). Bike Outliner for macOS opens
these files natively, and they can also be viewed in any web browser.

Usage:
    # From a local file
    python notes_to_bike.py --file notes.txt
    python notes_to_bike.py --file story-notes.docx --output outline.bike
    python notes_to_bike.py --file research.pdf --title "My Story Outline"

    # From a Google Doc (requires OAuth credentials)
    python notes_to_bike.py --doc "My Story Notes"
    python notes_to_bike.py --doc-id "https://docs.google.com/document/d/1abc.../edit"

    # Specify output directory
    python notes_to_bike.py --file notes.txt --output-dir ~/Documents/Bike/

Requirements:
    pip install python-docx    # for .docx
    pip install PyPDF2         # for .pdf
    pip install striprtf       # for .rtf
    # Google API libs only needed for --doc / --doc-id:
    pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
"""

import argparse
import os
import re
import sys
import uuid
import html as html_mod
from datetime import datetime
from pathlib import Path

# Import the file readers from the companion script
try:
    from notes_to_gdoc_outline import (
        read_local_file,
        read_google_doc,
        find_doc_by_name,
        extract_doc_id_from_url,
        authenticate,
        HAS_GOOGLE_API,
    )
except ImportError:
    # If running from a different directory, try adjusting the path
    sys.path.insert(0, str(Path(__file__).parent))
    from notes_to_gdoc_outline import (
        read_local_file,
        read_google_doc,
        find_doc_by_name,
        extract_doc_id_from_url,
        authenticate,
        HAS_GOOGLE_API,
    )


# ─── Bike format helpers ─────────────────────────────────────────────

def _bike_id():
    """Generate a short unique ID for a Bike row (li element)."""
    # Bike uses short alphanumeric IDs. We'll use a truncated uuid.
    return uuid.uuid4().hex[:6]


def _escape(text):
    """HTML-escape text content for safe embedding in .bike XML."""
    return html_mod.escape(text, quote=True)


def _make_row(text, data_type=None, children=None):
    """
    Build an <li> element string for one Bike row.

    Args:
        text:      The text content of this row.
        data_type: Optional Bike row type: "heading", "note", "task",
                   "ordered", "unordered", or None (plain body row).
        children:  Optional list of child row strings (already formatted).

    Returns:
        An indented string of HTML for this row and its children.
    """
    row_id = _bike_id()
    type_attr = f' data-type="{data_type}"' if data_type else ""

    parts = [f'<li id="{row_id}"{type_attr}>']
    parts.append(f"<p>{_escape(text)}</p>")

    if children:
        parts.append("<ul>")
        for child in children:
            parts.append(child)
        parts.append("</ul>")

    parts.append("</li>")
    return "\n".join(parts)


def sections_to_bike_rows(sections):
    """
    Convert the standard sections structure into a list of Bike row strings.

    Headings become rows with data-type="heading".
    Body lines under a heading become child rows (plain type).
    Lines with no heading become top-level plain rows.
    """
    rows = []

    for section in sections:
        if section["heading"]:
            # Build child rows from body lines
            children = []
            for line in section["lines"]:
                # Split very long lines into sentences
                if len(line) > 200:
                    sentences = re.split(r'(?<=[.!?])\s+', line)
                    for sentence in sentences:
                        if sentence.strip():
                            children.append(_make_row(sentence.strip()))
                else:
                    children.append(_make_row(line))

            rows.append(_make_row(
                section["heading"],
                data_type="heading",
                children=children if children else None,
            ))
        else:
            # No heading — each line is a top-level row
            for line in section["lines"]:
                rows.append(_make_row(line))

    return rows


def build_bike_file(title, sections):
    """
    Build a complete .bike file string from a title and sections.

    Returns:
        A string containing valid .bike (XHTML) content.
    """
    rows = sections_to_bike_rows(sections)

    # Build the document
    root_id = _bike_id()
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<html>",
        "<head>",
        '<meta charset="utf-8"/>',
        f"<title>{_escape(title)}</title>",
        "</head>",
        "<body>",
        f'<ul id="{root_id}">',
    ]

    # Add all rows
    for row in rows:
        lines.append(row)

    lines.extend([
        "</ul>",
        "</body>",
        "</html>",
    ])

    return "\n".join(lines)


# ─── Main workflow ────────────────────────────────────────────────────

def run(doc_name=None, doc_id=None, local_file=None,
        output_path=None, output_dir=None, outline_title=None,
        credentials_path="credentials.json"):
    """
    Full pipeline: read source → compile → write .bike file.

    Source can be:
      - doc_name: search Google Drive by name
      - doc_id: Google Doc ID or URL
      - local_file: path to a .docx, .pdf, .txt, or .rtf file

    Returns:
        dict with output_path, title, section_count, row_count
    """
    source_count = sum(1 for x in [doc_name, doc_id, local_file] if x)
    if source_count == 0:
        print("ERROR: Provide one of --doc, --doc-id, or --file.")
        sys.exit(1)
    if source_count > 1:
        print("ERROR: Provide only one source (--doc, --doc-id, or --file).")
        sys.exit(1)

    # ── Read the source ──────────────────────────────────────────────
    if local_file:
        print(f"Reading local file: {local_file}")
        doc_content = read_local_file(local_file)
        source_label = os.path.basename(local_file)
    else:
        # Google Doc — need auth
        if not HAS_GOOGLE_API:
            print("ERROR: Google API libraries not installed.")
            print("Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
            sys.exit(1)

        from googleapiclient.discovery import build as build_service

        print("Authenticating with Google...")
        creds = authenticate(credentials_path)
        drive_service = build_service("drive", "v3", credentials=creds)
        docs_service = build_service("docs", "v1", credentials=creds)

        if doc_id:
            resolved_id = extract_doc_id_from_url(doc_id)
            if not resolved_id:
                print(f"ERROR: Could not parse doc ID from '{doc_id}'.")
                sys.exit(1)
            source_id = resolved_id
            print(f"Using doc ID: {source_id}")
        else:
            print(f"Searching for doc: '{doc_name}'...")
            result = find_doc_by_name(drive_service, doc_name)
            if not result:
                print(f"ERROR: No Google Doc named '{doc_name}' found.")
                sys.exit(1)
            source_id, found_name = result
            print(f"Found: '{found_name}' ({source_id})")

        print("Reading doc contents...")
        doc_content = read_google_doc(docs_service, source_id)
        source_label = doc_content["title"]

    section_count = len(doc_content["sections"])
    line_count = sum(len(s["lines"]) for s in doc_content["sections"])
    print(f"  ✓ '{doc_content['title']}' — {section_count} section(s), {line_count} line(s)")

    # ── Determine title ──────────────────────────────────────────────
    if not outline_title:
        outline_title = doc_content.get("title", "Untitled")

    # ── Build .bike content ──────────────────────────────────────────
    print("Building .bike outline...")
    bike_content = build_bike_file(outline_title, doc_content["sections"])

    # ── Determine output path ────────────────────────────────────────
    if output_path:
        out = Path(output_path)
    else:
        # Generate filename from title
        safe_name = re.sub(r'[^\w\s-]', '', outline_title).strip()
        safe_name = re.sub(r'\s+', '-', safe_name)
        filename = f"{safe_name}.bike"

        if output_dir:
            out = Path(output_dir) / filename
        elif local_file:
            out = Path(local_file).parent / filename
        else:
            out = Path.cwd() / filename

    # Ensure parent directory exists
    out.parent.mkdir(parents=True, exist_ok=True)

    # ── Write the file ───────────────────────────────────────────────
    with open(out, "w", encoding="utf-8") as f:
        f.write(bike_content)

    row_count = bike_content.count("<li ")

    print(f"\n{'─' * 50}")
    print(f"✓ Bike outline created successfully!")
    print(f"  Title:    {outline_title}")
    print(f"  Source:   {source_label}")
    print(f"  Sections: {section_count}")
    print(f"  Rows:     {row_count}")
    print(f"  Output:   {out}")
    print(f"{'─' * 50}")

    return {
        "output_path": str(out),
        "title": outline_title,
        "section_count": section_count,
        "row_count": row_count,
    }


# ─── CLI entry point ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Compile notes into a .bike outline (Bike Outliner format).",
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
  %(prog)s --file story-notes.txt
  %(prog)s --file notes.docx --output my-outline.bike
  %(prog)s --file notes.docx --output-dir ~/Documents/Bike/
  %(prog)s --doc "My Story Notes" --title "Memory Stories"
  %(prog)s --doc-id "https://docs.google.com/document/d/1abc.../edit"
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
        "--output", "-o",
        default=None,
        help="Output .bike file path (default: <title>.bike alongside the source)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for the output .bike file (default: same as source file)",
    )
    parser.add_argument(
        "--title", "-t",
        default=None,
        help="Title for the outline (default: source document title)",
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
        output_path=args.output,
        output_dir=args.output_dir,
        outline_title=args.title,
        credentials_path=args.credentials,
    )

    print(result["output_path"])


if __name__ == "__main__":
    main()
