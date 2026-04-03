#!/usr/bin/env python3
"""
Build a Scrivener 3 (macOS) .scriv project from structured outline data.

This script creates all the files and directories that make up a valid .scriv
project: the .scrivx XML binder, RTF content files for each document, styles,
settings, and metadata.

Uses Times New Roman 13pt as the default font.

Usage:
    Import and call build() with your outline data, or run directly after
    editing the __main__ block with your data.

Scrivener 3 .scriv structure:
    ProjectName.scriv/
    ├── ProjectName.scrivx          # XML binder (the project's spine)
    ├── Files/
    │   ├── Data/
    │   │   └── <UUID>/
    │   │       └── content.rtf     # One per document
    │   ├── version.txt             # Always "23" for Scrivener 3
    │   ├── styles.xml
    │   ├── search.indexes
    │   └── writing.history
    └── Settings/
        ├── ui-common.xml
        ├── compile.xml
        ├── favorites.xml
        └── recents.txt
"""

import os
import uuid
import textwrap
from datetime import datetime


def generate_uuid():
    """Generate an uppercase UUID string for Scrivener items."""
    return str(uuid.uuid4()).upper()


def text_to_rtf(text):
    """Wrap plain text in minimal RTF suitable for Scrivener 3.

    Uses Times New Roman 13pt (fs26 in RTF half-points).
    """
    # Escape RTF special characters
    text = text.replace("\\", "\\\\")
    text = text.replace("{", "\\{")
    text = text.replace("}", "\\}")
    # Convert newlines to RTF line breaks
    text = text.replace("\n", " \\\n")

    return textwrap.dedent(f"""\
        {{\\rtf1\\ansi\\ansicpg1252\\cocoartf2709
        \\cocoatextscaling0\\cocoaplatform0{{\\fonttbl\\f0\\froman\\fcharset0 TimesNewRomanPSMT;}}
        {{\\colortbl;\\red255\\green255\\blue255;}}
        {{\\*\\expandedcolortbl;;}}
        \\pard\\tx360\\tx720\\tx1080\\tx1440\\tx1800\\tx2160\\tx2880\\tx3600\\tx4320\\fi360\\sl264\\slmult1\\pardirnatural\\partightenfactor0

        \\f0\\fs26 \\cf0 {text}}}""")


def _make_data_dir(scriv_dir, item_uuid):
    """Create the Files/Data/<UUID>/ directory for a binder item."""
    d = os.path.join(scriv_dir, "Files", "Data", item_uuid)
    os.makedirs(d, exist_ok=True)
    return d


def _write_content(scriv_dir, item_uuid, text):
    """Write an RTF content file for a binder item."""
    d = _make_data_dir(scriv_dir, item_uuid)
    with open(os.path.join(d, "content.rtf"), "w") as f:
        f.write(text_to_rtf(text))


def _indent_xml(xml, levels=1):
    """Add indentation levels to an XML block."""
    indent = "    " * levels
    lines = xml.split('\n')
    return '\n'.join(indent + line if line.strip() else line for line in lines)


def _binder_item_xml(title, item_uuid, item_type="Text", children_xml="",
                      include_compile="Yes", now=""):
    """Generate a <BinderItem> XML element.

    Args:
        title: Display name in the Binder
        item_uuid: Unique identifier
        item_type: "Text", "Folder", "DraftFolder", "ResearchFolder", "TrashFolder"
        children_xml: Nested XML for child items
        include_compile: Whether to include in Compile output
        now: Timestamp string
    """
    children_block = ""
    if children_xml:
        children_block = f"\n            <Children>\n{children_xml}            </Children>"

    icon = ""
    if item_type == "Folder" and title == "Notes":
        icon = "\n                <IconFileName>Notes (Yellow Notepad)</IconFileName>"

    return f"""        <BinderItem UUID="{item_uuid}" Type="{item_type}" Created="{now}" Modified="{now}">
            <Title>{title}</Title>
            <MetaData>
                <IncludeInCompile>{include_compile}</IncludeInCompile>{icon}
            </MetaData>
            <TextSettings>
                <TextSelection>0,0</TextSelection>
            </TextSettings>{children_block}
        </BinderItem>
"""


def build(project_name, output_dir, manuscript_sections, research_docs=None,
          author="W. S. Gong"):
    """Build a complete Scrivener 3 .scriv project.

    Args:
        project_name: Name of the project (becomes the .scriv folder name)
        output_dir: Parent directory where the .scriv folder will be created
        manuscript_sections: List of dicts defining the Manuscript structure.
            Each dict has:
                "title": str - display name
                "type": "Folder" or "Text"
                "content": str - (for Text type) the document content
                "children": list of (title, content) tuples - (for Folder type)
        research_docs: Optional list of dicts with "title" and "content" keys
        author: Author name for project metadata

    Returns:
        str: Path to the created .scriv directory
    """
    research_docs = research_docs or []

    scriv_dir = os.path.join(output_dir, f"{project_name}.scriv")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S -0700")

    # Create directory structure
    os.makedirs(os.path.join(scriv_dir, "Files", "Data"), exist_ok=True)
    os.makedirs(os.path.join(scriv_dir, "Settings"), exist_ok=True)

    # Fixed UUIDs for standard folders
    project_uuid = generate_uuid()
    draft_uuid = generate_uuid()
    research_uuid = generate_uuid()
    trash_uuid = generate_uuid()
    notes_uuid = generate_uuid()
    scene_type_uuid = generate_uuid()
    na_type_uuid = generate_uuid()

    # Build Manuscript children XML
    manuscript_children = ""
    for section in manuscript_sections:
        if section["type"] == "Folder":
            child_xml = ""
            for child_title, child_content in section.get("children", []):
                child_uuid = generate_uuid()
                _write_content(scriv_dir, child_uuid, child_content)
                child_xml += _indent_xml(
                    _binder_item_xml(child_title, child_uuid, "Text", now=now), 2
                )

            folder_uuid = generate_uuid()
            _make_data_dir(scriv_dir, folder_uuid)
            manuscript_children += _indent_xml(
                _binder_item_xml(section["title"], folder_uuid, "Folder",
                                children_xml=child_xml, now=now), 1
            )
        elif section["type"] == "Text":
            text_uuid = generate_uuid()
            _write_content(scriv_dir, text_uuid, section["content"])
            manuscript_children += _indent_xml(
                _binder_item_xml(section["title"], text_uuid, "Text", now=now), 1
            )

    # Build Research children XML
    research_children = ""
    for doc in research_docs:
        doc_uuid = generate_uuid()
        _write_content(scriv_dir, doc_uuid, doc["content"])
        research_children += _indent_xml(
            _binder_item_xml(doc["title"], doc_uuid, "Text", now=now), 2
        )

    # Create data dirs for standard folders
    _make_data_dir(scriv_dir, draft_uuid)
    _make_data_dir(scriv_dir, research_uuid)
    _make_data_dir(scriv_dir, trash_uuid)
    _make_data_dir(scriv_dir, notes_uuid)

    # ── Write the .scrivx binder file ──
    scrivx = f"""<?xml version="1.0" encoding="UTF-8"?>
<ScrivenerProject Identifier="{project_uuid}" Version="2.0" Creator="SCRMAC-3.2.3-14869" Device="Gong" Author="{author}" Modified="{now}" ModID="{generate_uuid()}">
    <Binder>
        <BinderItem UUID="{draft_uuid}" Type="DraftFolder" Created="{now}" Modified="{now}">
            <Title>Manuscript</Title>
            <Children>
{manuscript_children}            </Children>
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
{research_children}            </Children>
        </BinderItem>
        <BinderItem UUID="{trash_uuid}" Type="TrashFolder" Created="{now}" Modified="{now}">
            <Title>Trash</Title>
        </BinderItem>
    </Binder>
    <Collections>
        <Collection Type="Binder" ID="{generate_uuid()}" Color="1.0 1.0 1.0">
            <Title>Binder</Title>
        </Collection>
        <Collection Type="RecentSearch" ID="{generate_uuid()}" Color="0.922173 0.818612 0.999627">
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

    # ── Write supporting files ──

    # version.txt
    with open(os.path.join(scriv_dir, "Files", "version.txt"), "w") as f:
        f.write("23")

    # search.indexes
    with open(os.path.join(scriv_dir, "Files", "search.indexes"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<SearchIndexes Version="2.0">\n</SearchIndexes>')

    # writing.history
    with open(os.path.join(scriv_dir, "Files", "writing.history"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<WritingHistory/>')

    # styles.xml (Times New Roman-based)
    with open(os.path.join(scriv_dir, "Files", "styles.xml"), "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<Styles>
    <Style Name="Title" ID="{generate_uuid()}" Type="Para+Char" FontChange="Size">
        <Format><![CDATA[{{\\rtf1\\ansi\\ansicpg1252\\cocoartf2709
\\cocoatextscaling0\\cocoaplatform0{{\\fonttbl\\f0\\froman\\fcharset0 TimesNewRomanPSMT;}}
{{\\colortbl;\\red255\\green255\\blue255;}}
{{\\*\\expandedcolortbl;;}}
\\pard\\tx560\\tx1120\\tx1680\\tx2240\\tx2800\\tx3360\\tx3920\\tx4480\\tx5040\\tx5600\\tx6160\\tx6720\\sl264\\slmult1\\sb260\\pardirnatural\\partightenfactor0

\\f0\\fs56 \\cf0 <$ScrKeepWithNext>Attributes}}]]></Format>
    </Style>
    <Style Name="Heading 1" ID="{generate_uuid()}" Type="Para+Char" FontChange="Size" Shortcut="4">
        <Format><![CDATA[{{\\rtf1\\ansi\\ansicpg1252\\cocoartf2709
\\cocoatextscaling0\\cocoaplatform0{{\\fonttbl\\f0\\fswiss\\fcharset0 Helvetica;\\f1\\froman\\fcharset0 TimesNewRomanPS-BoldMT;}}
{{\\colortbl;\\red255\\green255\\blue255;}}
{{\\*\\expandedcolortbl;;}}
\\pard\\tx560\\tx1120\\tx1680\\tx2240\\tx2800\\tx3360\\tx3920\\tx4480\\tx5040\\tx5600\\tx6160\\tx6720\\sl264\\slmult1\\sb260\\pardirnatural\\partightenfactor0

\\f0\\fs24 \\cf0 <$ScrKeepWithNext><$Scr_H::1>
\\f1\\b\\fs36 Attributes
\\f0\\b0\\fs24 <!$Scr_H::1>}}]]></Format>
    </Style>
    <Style Name="Heading 2" ID="{generate_uuid()}" Type="Para+Char" FontChange="Size" Shortcut="5">
        <Format><![CDATA[{{\\rtf1\\ansi\\ansicpg1252\\cocoartf2709
\\cocoatextscaling0\\cocoaplatform0{{\\fonttbl\\f0\\fswiss\\fcharset0 Helvetica;\\f1\\froman\\fcharset0 TimesNewRomanPS-BoldMT;}}
{{\\colortbl;\\red255\\green255\\blue255;}}
{{\\*\\expandedcolortbl;;}}
\\pard\\tx560\\tx1120\\tx1680\\tx2240\\tx2800\\tx3360\\tx3920\\tx4480\\tx5040\\tx5600\\tx6160\\tx6720\\sl264\\slmult1\\sb260\\pardirnatural\\partightenfactor0

\\f0\\fs24 \\cf0 <$ScrKeepWithNext><$Scr_H::2>
\\f1\\b\\fs26 Attributes
\\f0\\b0\\fs24 <!$Scr_H::2>}}]]></Format>
    </Style>
</Styles>""")

    # Settings files
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

    # Count what was created
    data_dir = os.path.join(scriv_dir, "Files", "Data")
    data_dirs = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
    rtf_count = sum(1 for d in data_dirs if os.path.exists(os.path.join(data_dir, d, "content.rtf")))

    print(f"Created: {scriv_dir}")
    print(f"  Binder items: {len(data_dirs)}")
    print(f"  RTF documents: {rtf_count}")

    return scriv_dir


if __name__ == "__main__":
    # Example usage — replace with your own data
    build(
        project_name="Example Project",
        output_dir="/tmp",
        manuscript_sections=[
            {"title": "Opening", "type": "Folder", "children": [
                ("Scene 1", "First scene notes here"),
                ("Scene 2", "Second scene notes here"),
            ]},
        ],
        research_docs=[
            {"title": "Character Notes", "content": "Notes about characters"},
        ],
    )
