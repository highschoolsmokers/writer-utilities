#!/usr/bin/env python3
"""
bike_to_scriv.py
────────────────
Convert a .bike outline (Bike Outliner) into a Scrivener 3 (.scriv) project.

Features:
  - Heading rows → Scrivener Folders; their children → nested Text documents
  - Note rows (data-type="note") → routed to Scrivener's Research folder
  - All body rows → RTF content in the document body (ready to draft over)
  - All manuscript documents set to "To Do" status for progress tracking
  - Binder tree printed to console for verification before opening
  - Reverse export: .scriv → .bike for round-tripping

Usage:
    # .bike → .scriv
    python bike_to_scriv.py outline.bike
    python bike_to_scriv.py outline.bike --output-dir ~/Documents/Scrivener/
    python bike_to_scriv.py outline.bike --author "Billy Gong"

    # .scriv → .bike (reverse)
    python bike_to_scriv.py --reverse "My Project.scriv"
    python bike_to_scriv.py --reverse "My Project.scriv" --output outline.bike

No external dependencies required — uses only Python standard library.
"""

import argparse
import os
import re
import sys
import uuid
import textwrap
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import html as html_mod


# ═══════════════════════════════════════════════════════════════════════
#  BIKE PARSER
# ═══════════════════════════════════════════════════════════════════════

class BikeRow:
    """Represents a single row (li element) in a .bike outline."""

    def __init__(self, text, data_type=None, row_id=None, children=None):
        self.text = text
        self.data_type = data_type  # "heading", "note", "task", "ordered", etc.
        self.row_id = row_id or ""
        self.children = children or []

    def __repr__(self):
        child_count = f" ({len(self.children)} children)" if self.children else ""
        dtype = f" [{self.data_type}]" if self.data_type else ""
        return f"BikeRow({self.text!r}{dtype}{child_count})"


def parse_bike_file(filepath):
    """
    Parse a .bike file and return (title, rows).

    Args:
        filepath: Path to the .bike file.

    Returns:
        (title, rows) where title is a string and rows is a list of BikeRow.
    """
    tree = ET.parse(filepath)
    root = tree.getroot()

    # Extract title from <title> or filename
    title_el = root.find(".//title")
    if title_el is not None and title_el.text:
        title = title_el.text.strip()
    else:
        title = Path(filepath).stem

    # Find the root <ul> in <body>
    body = root.find("body")
    if body is None:
        print("ERROR: No <body> element found in .bike file.")
        sys.exit(1)

    root_ul = body.find("ul")
    if root_ul is None:
        print("ERROR: No <ul> element found in <body>.")
        sys.exit(1)

    rows = _parse_ul(root_ul)
    return title, rows


def _parse_ul(ul_element):
    """Recursively parse a <ul> element into a list of BikeRow objects."""
    rows = []
    for li in ul_element.findall("li"):
        row_id = li.get("id", "")
        data_type = li.get("data-type", None)

        # Extract text from <p> element
        p = li.find("p")
        text = _get_element_text(p) if p is not None else ""

        # Recursively parse children
        child_ul = li.find("ul")
        children = _parse_ul(child_ul) if child_ul is not None else []

        rows.append(BikeRow(
            text=text,
            data_type=data_type,
            row_id=row_id,
            children=children,
        ))

    return rows


def _get_element_text(element):
    """Get all text content from an element, including tail text from children."""
    parts = []
    if element.text:
        parts.append(element.text)
    for child in element:
        if child.text:
            parts.append(child.text)
        if child.tail:
            parts.append(child.tail)
    return "".join(parts).strip()


# ═══════════════════════════════════════════════════════════════════════
#  SCRIVENER BUILDER
# ═══════════════════════════════════════════════════════════════════════

def _generate_uuid():
    """Generate an uppercase UUID string for Scrivener items."""
    return str(uuid.uuid4()).upper()


def _text_to_rtf(text):
    """Wrap plain text in minimal RTF (Times New Roman 13pt) for Scrivener 3."""
    text = text.replace("\\", "\\\\")
    text = text.replace("{", "\\{")
    text = text.replace("}", "\\}")
    text = text.replace("\n", " \\\n")

    return textwrap.dedent(f"""\
        {{\\rtf1\\ansi\\ansicpg1252\\cocoartf2709
        \\cocoatextscaling0\\cocoaplatform0{{\\fonttbl\\f0\\froman\\fcharset0 TimesNewRomanPSMT;}}
        {{\\colortbl;\\red255\\green255\\blue255;}}
        {{\\*\\expandedcolortbl;;}}
        \\pard\\tx360\\tx720\\tx1080\\tx1440\\tx1800\\tx2160\\tx2880\\tx3600\\tx4320\\fi360\\sl264\\slmult1\\pardirnatural\\partightenfactor0

        \\f0\\fs26 \\cf0 {text}}}""")


def _make_data_dir(scriv_dir, item_uuid):
    """Create the Files/Data/<UUID>/ directory."""
    d = os.path.join(scriv_dir, "Files", "Data", item_uuid)
    os.makedirs(d, exist_ok=True)
    return d


def _write_content(scriv_dir, item_uuid, text):
    """Write an RTF content file for a binder item."""
    d = _make_data_dir(scriv_dir, item_uuid)
    with open(os.path.join(d, "content.rtf"), "w") as f:
        f.write(_text_to_rtf(text))


def _binder_item_xml(title, item_uuid, item_type="Text", children_xml="",
                     include_compile="Yes", status_id=None, synopsis=None,
                     now=""):
    """Generate a <BinderItem> XML element."""
    children_block = ""
    if children_xml:
        children_block = f"\n            <Children>\n{children_xml}            </Children>"

    icon = ""
    if item_type == "Folder" and title == "Notes":
        icon = "\n                <IconFileName>Notes (Yellow Notepad)</IconFileName>"

    status_block = ""
    if status_id is not None:
        status_block = f"\n                <StatusID>{status_id}</StatusID>"

    # Escape XML special characters in title
    safe_title = (title.replace("&", "&amp;")
                       .replace("<", "&lt;")
                       .replace(">", "&gt;")
                       .replace('"', "&quot;"))

    return f"""        <BinderItem UUID="{item_uuid}" Type="{item_type}" Created="{now}" Modified="{now}">
            <Title>{safe_title}</Title>
            <MetaData>
                <IncludeInCompile>{include_compile}</IncludeInCompile>{icon}{status_block}
            </MetaData>
            <TextSettings>
                <TextSelection>0,0</TextSelection>
            </TextSettings>{children_block}
        </BinderItem>
"""


def _has_heading_children(row):
    """Check if any direct children are headings (structural grouping)."""
    return any(child.data_type == "heading" for child in row.children)


def _gather_child_text(row):
    """Collect all child text into body content for a Text document."""
    lines = []
    for child in row.children:
        if child.text:
            lines.append(child.text)
        for grandchild in child.children:
            if grandchild.text:
                lines.append(grandchild.text)
    return "\n".join(lines)


def _bike_row_to_content(row):
    """
    Build the text content for a Scrivener document from a BikeRow.

    For heading rows, gathers child text into a summary.
    For plain rows, uses the row text directly.
    """
    lines = [row.text] if row.text else []

    # If this row has children, include their text as indented notes
    for child in row.children:
        if child.text:
            lines.append(f"  - {child.text}")
        for grandchild in child.children:
            if grandchild.text:
                lines.append(f"    - {grandchild.text}")

    return "\n".join(lines)


def _build_manuscript_items(rows, scriv_dir, now, depth=0):
    """
    Recursively convert BikeRows into Scrivener binder XML + RTF files.

    Returns:
        (manuscript_xml, research_xml, stats)
        where stats is a dict with counts.
    """
    manuscript_xml = ""
    research_xml = ""
    stats = {"folders": 0, "texts": 0, "research": 0}

    for row in rows:
        # Route note-type rows to Research
        if row.data_type == "note":
            doc_uuid = _generate_uuid()
            content = _bike_row_to_content(row)
            _write_content(scriv_dir, doc_uuid, content)
            research_xml += f"                {_binder_item_xml(row.text, doc_uuid, 'Text', now=now, include_compile='No')}"
            stats["research"] += 1
            continue

        # Heading rows with children that are themselves headings → Folders
        if row.data_type == "heading" and row.children and _has_heading_children(row):
            folder_uuid = _generate_uuid()
            _make_data_dir(scriv_dir, folder_uuid)

            # Recursively build children
            child_ms_xml, child_res_xml, child_stats = _build_manuscript_items(
                row.children, scriv_dir, now, depth + 1
            )

            if row.text:
                _write_content(scriv_dir, folder_uuid, row.text)

            manuscript_xml += _binder_item_xml(
                row.text or "Untitled",
                folder_uuid,
                "Folder",
                children_xml=child_ms_xml,
                status_id="1",  # "To Do"
                now=now,
            )
            research_xml += child_res_xml
            stats["folders"] += 1
            stats["folders"] += child_stats["folders"]
            stats["texts"] += child_stats["texts"]
            stats["research"] += child_stats["research"]

        # Heading rows with only leaf children → Text documents
        # (title = heading text, body = gathered child text)
        elif row.data_type == "heading" and row.children and not _has_heading_children(row):
            text_uuid = _generate_uuid()
            content = _gather_child_text(row)
            _write_content(scriv_dir, text_uuid, content)
            manuscript_xml += _binder_item_xml(
                row.text or "Untitled",
                text_uuid,
                "Text",
                status_id="1",
                now=now,
            )
            stats["texts"] += 1

        # Heading rows without children → Text documents
        elif row.data_type == "heading" and not row.children:
            text_uuid = _generate_uuid()
            content = row.text or ""
            _write_content(scriv_dir, text_uuid, content)
            manuscript_xml += _binder_item_xml(
                row.text or "Untitled",
                text_uuid,
                "Text",
                status_id="1",
                now=now,
            )
            stats["texts"] += 1

        # Plain rows (body, task, ordered, unordered, etc.) → Text documents
        else:
            text_uuid = _generate_uuid()

            # If it has children with headings, make it a folder
            if row.children and _has_heading_children(row):
                content = _bike_row_to_content(row)
                _write_content(scriv_dir, text_uuid, content)
                child_ms_xml, child_res_xml, child_stats = _build_manuscript_items(
                    row.children, scriv_dir, now, depth + 1
                )
                manuscript_xml += _binder_item_xml(
                    row.text or "Untitled",
                    text_uuid,
                    "Folder",
                    children_xml=child_ms_xml,
                    status_id="1",
                    now=now,
                )
                research_xml += child_res_xml
                stats["folders"] += 1
                stats["folders"] += child_stats["folders"]
                stats["texts"] += child_stats["texts"]
                stats["research"] += child_stats["research"]
            # Leaf children → flatten into a single Text document
            elif row.children:
                content = _gather_child_text(row)
                _write_content(scriv_dir, text_uuid, content)
                manuscript_xml += _binder_item_xml(
                    row.text or "Untitled",
                    text_uuid,
                    "Text",
                    status_id="1",
                    now=now,
                )
                stats["texts"] += 1
            else:
                content = row.text or ""
                _write_content(scriv_dir, text_uuid, content)
                manuscript_xml += _binder_item_xml(
                    row.text or "Untitled",
                    text_uuid,
                    "Text",
                    status_id="1",
                    now=now,
                )
                stats["texts"] += 1

    return manuscript_xml, research_xml, stats


def build_scriv_from_bike(bike_path, output_dir=None, author="W. S. Gong"):
    """
    Full pipeline: parse .bike → build .scriv project.

    Args:
        bike_path:  Path to the .bike file.
        output_dir: Directory for the .scriv project (default: alongside .bike file).
        author:     Author name for Scrivener metadata.

    Returns:
        dict with scriv_path, title, stats.
    """
    # Parse
    title, rows = parse_bike_file(bike_path)
    project_name = title or Path(bike_path).stem

    if not output_dir:
        output_dir = str(Path(bike_path).parent)

    scriv_dir = os.path.join(output_dir, f"{project_name}.scriv")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S -0700")

    # Create directory structure
    os.makedirs(os.path.join(scriv_dir, "Files", "Data"), exist_ok=True)
    os.makedirs(os.path.join(scriv_dir, "Settings"), exist_ok=True)

    # Fixed UUIDs for standard folders
    project_uuid = _generate_uuid()
    draft_uuid = _generate_uuid()
    research_uuid = _generate_uuid()
    trash_uuid = _generate_uuid()
    notes_uuid = _generate_uuid()
    scene_type_uuid = _generate_uuid()
    na_type_uuid = _generate_uuid()

    # Build manuscript and research items from bike rows
    manuscript_xml, research_xml, stats = _build_manuscript_items(rows, scriv_dir, now)

    # Create data dirs for standard folders
    _make_data_dir(scriv_dir, draft_uuid)
    _make_data_dir(scriv_dir, research_uuid)
    _make_data_dir(scriv_dir, trash_uuid)
    _make_data_dir(scriv_dir, notes_uuid)

    # ── Write the .scrivx binder file ──
    safe_author = (author.replace("&", "&amp;")
                         .replace("<", "&lt;")
                         .replace(">", "&gt;")
                         .replace('"', "&quot;"))

    scrivx = f"""<?xml version="1.0" encoding="UTF-8"?>
<ScrivenerProject Identifier="{project_uuid}" Version="2.0" Creator="SCRMAC-3.2.3-14869" Device="Gong" Author="{safe_author}" Modified="{now}" ModID="{_generate_uuid()}">
    <Binder>
        <BinderItem UUID="{draft_uuid}" Type="DraftFolder" Created="{now}" Modified="{now}">
            <Title>Manuscript</Title>
            <Children>
{manuscript_xml}            </Children>
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
{research_xml}            </Children>
        </BinderItem>
        <BinderItem UUID="{trash_uuid}" Type="TrashFolder" Created="{now}" Modified="{now}">
            <Title>Trash</Title>
        </BinderItem>
    </Binder>
    <Collections>
        <Collection Type="Binder" ID="{_generate_uuid()}" Color="1.0 1.0 1.0">
            <Title>Binder</Title>
        </Collection>
        <Collection Type="RecentSearch" ID="{_generate_uuid()}" Color="0.922173 0.818612 0.999627">
            <Title>Search Results</Title>
        </Collection>
    </Collections>
    <SectionTypes>
        <TypeDefinitions>
            <Type ID="{scene_type_uuid}">Scene</Type>
            <Type ID="{na_type_uuid}">N/A</Type>
        </TypeDefinitions>
        <LevelTypes>
            <Folders>
                <Type>{na_type_uuid}</Type>
            </Folders>
            <Containers>
                <Type>{na_type_uuid}</Type>
            </Containers>
            <Files>
                <Type>{na_type_uuid}</Type>
                <Type>{scene_type_uuid}</Type>
            </Files>
        </LevelTypes>
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
    <ProjectTargets Notify="No">
        <DraftTarget Type="Words" CountIncludedOnly="Yes" CurrentCompileGroupOnly="Yes" Deadline="2026-12-31 00:00:00 -0700" IgnoreDeadline="Yes">0</DraftTarget>
        <SessionTarget Type="Words" CountDraftOnly="Yes" AllowNegatives="No" NextResetDate="{now}" ResetType="Time" ResetTime="00:00" DeterminedFromDeadline="No" WritingDays="" CanWriteOnDeadlineDate="No">0</SessionTarget>
        <PreviousSession Words="0" Characters="0" Date="{now}"/>
    </ProjectTargets>
    <RecentWritingHistory Date="{now}">
        <DraftWordCount>0</DraftWordCount>
        <DraftCharCount>0</DraftCharCount>
        <OtherWordCount>0</OtherWordCount>
        <OtherCharCount>0</OtherCharCount>
    </RecentWritingHistory>
    <BookmarksFolderUUID>{notes_uuid}</BookmarksFolderUUID>
    <PrintSettings PaperSize="611.999975,792.0" LeftMargin="72.0" RightMargin="72.0" TopMargin="90.0" BottomMargin="90.0" PaperType="na-letter" Orientation="Portrait" HorizontalPagination="Clip" VerticalPagination="Auto" ScaleFactor="1.0" HorizontallyCentered="Yes" VerticallyCentered="Yes" Collates="Yes" PagesAcross="1" PagesDown="1"/>
</ScrivenerProject>"""

    scrivx_path = os.path.join(scriv_dir, f"{project_name}.scrivx")
    with open(scrivx_path, "w") as f:
        f.write(scrivx)

    # ── Supporting files ──
    with open(os.path.join(scriv_dir, "Files", "version.txt"), "w") as f:
        f.write("23")

    with open(os.path.join(scriv_dir, "Files", "search.indexes"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<SearchIndexes Version="2.0">\n</SearchIndexes>')

    with open(os.path.join(scriv_dir, "Files", "writing.history"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<WritingHistory/>')

    with open(os.path.join(scriv_dir, "Files", "styles.xml"), "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<Styles>
    <Style Name="Title" ID="{_generate_uuid()}" Type="Para+Char" FontChange="Size">
        <Format><![CDATA[{{\\rtf1\\ansi\\ansicpg1252\\cocoartf2709
\\cocoatextscaling0\\cocoaplatform0{{\\fonttbl\\f0\\froman\\fcharset0 TimesNewRomanPSMT;}}
{{\\colortbl;\\red255\\green255\\blue255;}}
{{\\*\\expandedcolortbl;;}}
\\pard\\sl264\\slmult1\\sb260\\pardirnatural\\partightenfactor0

\\f0\\fs56 \\cf0 <$ScrKeepWithNext>Attributes}}]]></Format>
    </Style>
    <Style Name="Heading 1" ID="{_generate_uuid()}" Type="Para+Char" FontChange="Size" Shortcut="4">
        <Format><![CDATA[{{\\rtf1\\ansi\\ansicpg1252\\cocoartf2709
\\cocoatextscaling0\\cocoaplatform0{{\\fonttbl\\f0\\fswiss\\fcharset0 Helvetica;\\f1\\froman\\fcharset0 TimesNewRomanPS-BoldMT;}}
{{\\colortbl;\\red255\\green255\\blue255;}}
{{\\*\\expandedcolortbl;;}}
\\pard\\sl264\\slmult1\\sb260\\pardirnatural\\partightenfactor0

\\f0\\fs24 \\cf0 <$ScrKeepWithNext><$Scr_H::1>
\\f1\\b\\fs36 Attributes
\\f0\\b0\\fs24 <!$Scr_H::1>}}]]></Format>
    </Style>
</Styles>""")

    with open(os.path.join(scriv_dir, "Settings", "ui-common.xml"), "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<UICommon>
    <SelectedEditor>Left</SelectedEditor>
    <LeftEditor>
        <SelectedUUIDs>
            <UUID>{draft_uuid}</UUID>
        </SelectedUUIDs>
        <ViewMode>Outline</ViewMode>
    </LeftEditor>
</UICommon>""")

    with open(os.path.join(scriv_dir, "Settings", "compile.xml"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<CompileSettings/>')

    with open(os.path.join(scriv_dir, "Settings", "favorites.xml"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<Favorites/>')

    with open(os.path.join(scriv_dir, "Settings", "recents.txt"), "w") as f:
        f.write("")

    return {
        "scriv_path": scriv_dir,
        "title": project_name,
        "stats": stats,
    }


# ═══════════════════════════════════════════════════════════════════════
#  BINDER TREE PREVIEW
# ═══════════════════════════════════════════════════════════════════════

def print_binder_tree(scriv_path):
    """Parse the .scrivx file and print the Binder tree to console."""
    project_name = Path(scriv_path).stem.replace(".scriv", "")
    scrivx_files = list(Path(scriv_path).glob("*.scrivx"))
    if not scrivx_files:
        print("  (no .scrivx file found)")
        return

    tree = ET.parse(scrivx_files[0])
    root = tree.getroot()
    binder = root.find("Binder")
    if binder is None:
        print("  (no Binder found in .scrivx)")
        return

    def _print_item(item, prefix="", is_last=True):
        connector = "└── " if is_last else "├── "
        title = item.findtext("Title", "Untitled")
        item_type = item.get("Type", "Text")

        # Choose icon
        if item_type in ("DraftFolder", "Folder"):
            icon = "📁"
        elif item_type == "ResearchFolder":
            icon = "🔬"
        elif item_type == "TrashFolder":
            icon = "🗑️ "
        else:
            icon = "📄"

        # Check status
        status_id = item.findtext("MetaData/StatusID", "")
        status_label = ""
        if status_id == "1":
            status_label = " [To Do]"

        print(f"{prefix}{connector}{icon} {title}{status_label}")

        children = item.find("Children")
        if children is not None:
            child_items = children.findall("BinderItem")
            for i, child in enumerate(child_items):
                child_is_last = (i == len(child_items) - 1)
                extension = "    " if is_last else "│   "
                _print_item(child, prefix + extension, child_is_last)

    items = binder.findall("BinderItem")
    print(f"\n📚 {project_name}")
    for i, item in enumerate(items):
        _print_item(item, "  ", i == len(items) - 1)
    print()


# ═══════════════════════════════════════════════════════════════════════
#  REVERSE: .SCRIV → .BIKE
# ═══════════════════════════════════════════════════════════════════════

def _bike_id():
    """Generate a short unique ID for a Bike row."""
    return uuid.uuid4().hex[:6]


def _escape_html(text):
    """HTML-escape text for .bike output."""
    return html_mod.escape(text, quote=True)


def _rtf_to_plain(rtf_path):
    """Extract plain text from an RTF file (minimal parser for Scrivener RTF)."""
    try:
        with open(rtf_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except FileNotFoundError:
        return ""

    # Strip RTF control words and groups
    # Remove header (everything up to the last \f0\fsNN \cfN)
    body_match = re.search(r'\\f0\\fs\d+\s*\\cf0\s*(.*)', content, re.DOTALL)
    if body_match:
        text = body_match.group(1)
    else:
        text = content

    # Remove closing brace
    text = re.sub(r'\}+\s*$', '', text)
    # Remove RTF commands
    text = re.sub(r'\\[a-zA-Z]+\d*\s?', '', text)
    # Remove escaped braces
    text = text.replace('\\{', '{').replace('\\}', '}').replace('\\\\', '\\')
    # Convert RTF line breaks
    text = text.replace('\\\n', '\n')
    # Clean up
    text = re.sub(r'\n{3,}', '\n\n', text).strip()

    return text


def _scriv_item_to_bike_rows(item, scriv_dir):
    """Recursively convert a Scrivener BinderItem into BikeRow(s)."""
    title = item.findtext("Title", "Untitled")
    item_type = item.get("Type", "Text")
    item_uuid = item.get("UUID", "")

    # Skip standard structural folders (Research, Trash, Notes) — only process children
    if item_type in ("TrashFolder",):
        return []

    # Determine Bike data-type
    if item_type in ("DraftFolder", "Folder"):
        data_type = "heading"
    elif item_type == "ResearchFolder":
        data_type = "note"
    else:
        data_type = None

    # Try to read content
    rtf_path = os.path.join(scriv_dir, "Files", "Data", item_uuid, "content.rtf")
    content = _rtf_to_plain(rtf_path)

    # Build children
    children_rows = []
    children_el = item.find("Children")
    if children_el is not None:
        for child_item in children_el.findall("BinderItem"):
            children_rows.extend(_scriv_item_to_bike_rows(child_item, scriv_dir))

    # For structural folders (Manuscript, Research), just return their children
    if item_type in ("DraftFolder", "ResearchFolder"):
        return children_rows

    row = BikeRow(
        text=title,
        data_type=data_type,
        row_id=_bike_id(),
        children=children_rows,
    )
    return [row]


def _rows_to_bike_xml(rows):
    """Convert a list of BikeRow objects into .bike XML string."""
    parts = []
    for row in rows:
        type_attr = f' data-type="{row.data_type}"' if row.data_type else ""
        parts.append(f'<li id="{_bike_id()}"{type_attr}>')
        parts.append(f"<p>{_escape_html(row.text)}</p>")

        if row.children:
            parts.append("<ul>")
            parts.append(_rows_to_bike_xml(row.children))
            parts.append("</ul>")

        parts.append("</li>")

    return "\n".join(parts)


def scriv_to_bike(scriv_path, output_path=None):
    """
    Convert a .scriv project back to a .bike file.

    Args:
        scriv_path:  Path to the .scriv directory.
        output_path: Output .bike file path (default: alongside .scriv).

    Returns:
        dict with output_path and title.
    """
    scriv_dir = str(scriv_path)

    # Find .scrivx file
    scrivx_files = list(Path(scriv_dir).glob("*.scrivx"))
    if not scrivx_files:
        print(f"ERROR: No .scrivx file found in {scriv_dir}")
        sys.exit(1)

    tree = ET.parse(scrivx_files[0])
    root = tree.getroot()
    title = scrivx_files[0].stem

    binder = root.find("Binder")
    if binder is None:
        print("ERROR: No Binder element in .scrivx")
        sys.exit(1)

    # Convert all top-level binder items
    all_rows = []
    for item in binder.findall("BinderItem"):
        all_rows.extend(_scriv_item_to_bike_rows(item, scriv_dir))

    # Build .bike file
    root_id = _bike_id()
    bike_xml = _rows_to_bike_xml(all_rows)

    bike_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<html>
<head>
<meta charset="utf-8"/>
<title>{_escape_html(title)}</title>
</head>
<body>
<ul id="{root_id}">
{bike_xml}
</ul>
</body>
</html>"""

    # Determine output path
    if not output_path:
        output_path = str(Path(scriv_dir).parent / f"{title}.bike")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(bike_content)

    print(f"\n{'─' * 50}")
    print(f"✓ Bike outline exported!")
    print(f"  Title:  {title}")
    print(f"  Rows:   {bike_content.count('<li ')}")
    print(f"  Output: {output_path}")
    print(f"{'─' * 50}")

    return {"output_path": output_path, "title": title}


# ═══════════════════════════════════════════════════════════════════════
#  MAIN WORKFLOW
# ═══════════════════════════════════════════════════════════════════════

def run_bike_to_scriv(bike_path, output_dir=None, author="W. S. Gong"):
    """Full pipeline: .bike → .scriv with binder tree preview."""

    print(f"Parsing: {bike_path}")
    title, rows = parse_bike_file(bike_path)
    row_count = sum(1 for _ in _flatten_rows(rows))
    print(f"  ✓ '{title}' — {len(rows)} top-level row(s), {row_count} total")

    print("Building Scrivener project...")
    result = build_scriv_from_bike(bike_path, output_dir, author)

    stats = result["stats"]
    print(f"\n{'─' * 50}")
    print(f"✓ Scrivener project created!")
    print(f"  Title:    {result['title']}")
    print(f"  Folders:  {stats['folders']}")
    print(f"  Texts:    {stats['texts']}  (all set to 'To Do')")
    print(f"  Research: {stats['research']}")
    print(f"  Path:     {result['scriv_path']}")
    print(f"{'─' * 50}")

    # Binder tree preview
    print_binder_tree(result["scriv_path"])

    return result


def _flatten_rows(rows):
    """Yield all rows recursively for counting."""
    for row in rows:
        yield row
        yield from _flatten_rows(row.children)


# ═══════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Convert between Bike (.bike) and Scrivener (.scriv) formats.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Bike → Scrivener
  %(prog)s outline.bike
  %(prog)s outline.bike --output-dir ~/Documents/Scrivener/
  %(prog)s outline.bike --author "Billy Gong"

  # Scrivener → Bike (reverse)
  %(prog)s --reverse "My Project.scriv"
  %(prog)s --reverse "My Project.scriv" --output outline.bike
        """,
    )

    parser.add_argument(
        "input",
        help="Path to .bike file (or .scriv directory with --reverse)",
    )
    parser.add_argument(
        "--reverse", "-r",
        action="store_true",
        help="Reverse mode: convert .scriv → .bike",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output path (.scriv dir or .bike file, depending on direction)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for the .scriv project (default: alongside input)",
    )
    parser.add_argument(
        "--author", "-a",
        default="W. S. Gong",
        help="Author name for Scrivener metadata (default: W. S. Gong)",
    )

    args = parser.parse_args()

    if args.reverse:
        scriv_to_bike(args.input, args.output)
    else:
        if not args.input.endswith(".bike"):
            print(f"WARNING: Input file doesn't have .bike extension: {args.input}")

        run_bike_to_scriv(
            args.input,
            output_dir=args.output_dir or (str(Path(args.output).parent) if args.output else None),
            author=args.author,
        )


if __name__ == "__main__":
    main()
