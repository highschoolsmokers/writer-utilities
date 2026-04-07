#!/usr/bin/env python3
"""
Short Story Workflow — Streamlit Dashboard
───────────────────────────────────────────
A point-and-click UI for the full pipeline:

  1. Notes → Google Doc Outline
  2. Notes → Bike Outline
  3. Bike → Scrivener Project
  4. Scrivener → Shunn Manuscript + Cover Letter

Launch:
    streamlit run dashboard.py
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

import streamlit as st

# ── Resolve script directory ──
SCRIPT_DIR = Path(__file__).resolve().parent

STEPS = ["Google Doc", "Bike Outline", "Scrivener", "Shunn"]


# ═══════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Story Workflow — W.S. Gong",
    page_icon="✒️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS — ws-gong site mirror ──
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;600;900&display=swap');

    /* ── RESET ── */
    *, *::before, *::after {
        border-radius: 0 !important;
    }

    /* ── GLOBAL ── */
    .stApp {
        background-color: #f2ede4;
        font-family: 'Geist', Arial, Helvetica, sans-serif;
        -webkit-font-smoothing: antialiased;
        color: #000;
    }

    /* ── LAYOUT — max-w-5xl mx-auto px-12 ── */
    .stMainBlockContainer {
        max-width: 64rem;
        margin: 0 auto;
        padding: 0 3rem 4rem 3rem;
    }
    [data-testid="stHorizontalBlock"] {
        gap: 1.5rem !important;
    }

    /* Hide sidebar toggle & Streamlit chrome */
    [data-testid="stSidebarCollapsedControl"],
    section[data-testid="stSidebar"],
    #MainMenu, footer, header[data-testid="stHeader"] {
        display: none !important;
    }

    /* ── NAV — 2-column grid matching Nav.tsx ── */
    .site-nav {
        display: grid;
        grid-template-columns: 1fr 2fr;
        gap: 3rem;
        align-items: end;
        padding: 2rem 0 1.5rem 0;
        border-bottom: 1px solid #000;
        margin-bottom: 2.5rem;
    }
    .site-masthead {
        font-family: 'Geist', Arial, Helvetica, sans-serif;
        font-size: 2.75rem;
        font-weight: 900;
        letter-spacing: -0.03em;
        line-height: 0.92;
        color: #000;
    }
    .site-nav-links {
        display: flex;
        gap: 2rem;
        align-items: baseline;
        justify-content: flex-end;
    }
    .site-nav-links a {
        font-family: 'Geist', Arial, Helvetica, sans-serif;
        font-size: 1rem;
        font-weight: 900;
        color: #000;
        text-decoration: none;
        letter-spacing: -0.01em;
        line-height: 1.2;
        white-space: nowrap;
        transition: opacity 0.3s ease-out;
    }
    .site-nav-links a:hover {
        opacity: 0.7;
    }
    .site-nav-links a.active {
        pointer-events: none;
    }

    /* ── TYPOGRAPHY ── */
    .step-header {
        font-family: 'Geist', Arial, Helvetica, sans-serif;
        font-size: 1.5rem;
        font-weight: 900;
        color: #000;
        letter-spacing: -0.02em;
        line-height: 1.15;
        margin-bottom: 0.5rem;
    }
    .step-sub {
        color: #737373;
        font-size: 0.75rem;
        line-height: 1.5;
        margin-bottom: 0;
    }

    h1, h2, h3, h4, .stMarkdown h4 {
        font-family: 'Geist', Arial, Helvetica, sans-serif !important;
        font-weight: 900 !important;
        color: #000 !important;
        letter-spacing: -0.01em;
    }

    /* Section labels */
    .stMarkdown h4 {
        font-size: 0.7rem !important;
        text-transform: uppercase;
        letter-spacing: 0.08em !important;
        margin-top: 1.5rem !important;
        padding-top: 0.75rem;
        border-top: 1px solid #000;
    }

    p, label, .stMarkdown {
        font-family: 'Geist', Arial, Helvetica, sans-serif;
        font-size: 0.875rem;
        line-height: 1.625;
    }

    /* Field labels */
    .stTextInput label p, .stFileUploader label p,
    .stSelectbox label p, .stRadio > label p {
        font-size: 0.7rem !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #737373 !important;
        font-weight: 600 !important;
    }

    /* ── FORM ELEMENTS — bottom-border inputs like contact form ── */
    .stTextInput [data-baseweb="input"],
    .stTextInput [data-baseweb="base-input"],
    .stTextInput input,
    .stSelectbox [data-baseweb="select"] > div,
    .stSelectbox [data-baseweb="input"] {
        border: none !important;
        box-shadow: none !important;
        background-color: transparent !important;
        outline: none !important;
    }
    .stTextInput [data-baseweb="input"] {
        border: none !important;
        border-bottom: 1px solid #525252 !important;
        background-color: transparent !important;
        padding: 0 !important;
    }
    .stTextInput input {
        font-family: 'Geist', Arial, Helvetica, sans-serif !important;
        font-size: 0.875rem !important;
        padding: 0.5rem 0 !important;
        color: #000 !important;
    }
    .stTextInput input::placeholder {
        color: #a3a3a3 !important;
    }
    .stTextInput [data-baseweb="input"]:focus-within {
        border-bottom-color: #000 !important;
        box-shadow: none !important;
    }

    .stSelectbox [data-baseweb="select"] {
        border: none !important;
        border-bottom: 1px solid #525252 !important;
        background-color: transparent !important;
    }
    .stSelectbox [data-baseweb="select"] > div {
        border: none !important;
    }

    /* File uploader — minimal, border-bottom style */
    .stFileUploader [data-testid="stFileUploaderDropzone"] {
        border: none !important;
        border-bottom: 1px dashed #a3a3a3 !important;
        background: transparent !important;
        padding-bottom: 0.75rem;
    }
    .stFileUploader [data-testid="stFileUploaderDropzone"] > div,
    .stFileUploader [data-testid="stFileUploaderDropzone"] section {
        border: none !important;
    }
    .stFileUploader button {
        border: none !important;
        background: transparent !important;
        font-family: 'Geist', Arial, Helvetica, sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
        color: #a3a3a3 !important;
        padding: 0 !important;
        transition: color 0.3s ease-out;
    }
    .stFileUploader button:hover {
        color: #000 !important;
    }

    /* ── BUTTONS — text link style like contact Send ── */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"] {
        font-family: 'Geist', Arial, Helvetica, sans-serif !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
        letter-spacing: -0.02em;
        background-color: transparent !important;
        color: #a3a3a3 !important;
        border: none !important;
        padding: 0 !important;
        width: auto !important;
        min-width: 0 !important;
        transition: color 0.3s ease-out;
        cursor: pointer;
        text-decoration: none;
    }
    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="stBaseButton-primary"]:hover {
        color: #000 !important;
        text-decoration: underline !important;
        background-color: transparent !important;
    }
    .stButton {
        text-align: left;
    }

    /* ── TABS ── */
    .stTabs [data-baseweb="tab-list"] {
        border-bottom: 1px solid #000;
        gap: 0;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Geist', Arial, Helvetica, sans-serif;
        font-weight: 900;
        font-size: 0.8rem;
        letter-spacing: -0.01em;
        padding: 0.6rem 1.5rem;
        color: #737373;
        border-bottom: 2px solid transparent;
        transition: opacity 0.3s ease-out;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #000 !important;
        border-bottom: 2px solid #000 !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        opacity: 0.7;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #000 !important;
    }

    /* ── RADIO — square toggles ── */
    /* Outer mark: black border, transparent fill */
    .stRadio [data-baseweb="radio"] > div:first-child {
        width: 14px !important;
        height: 14px !important;
        min-width: 14px !important;
        min-height: 14px !important;
        border: 2px solid #000 !important;
        border-radius: 0 !important;
        background-color: transparent !important;
        box-shadow: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    /* Inner mark: always present, small square */
    .stRadio [data-baseweb="radio"] > div:first-child > div {
        width: 6px !important;
        height: 6px !important;
        border-radius: 0 !important;
        background-color: #f2ede4 !important;
        transition: background-color 0.15s ease;
    }
    /* Selected: inner fills black */
    .stRadio [data-baseweb="radio"]:has(input:checked) > div:first-child {
        background-color: #000 !important;
    }
    .stRadio [data-baseweb="radio"]:has(input:checked) > div:first-child > div {
        background-color: #000 !important;
    }

    /* ── DIVIDERS ── */
    hr {
        border: none;
        border-top: 1px solid #000;
        margin: 1rem 0;
    }

    /* ── OUTPUT BOX ── */
    .output-box {
        background: transparent;
        border: 1px solid #000;
        padding: 1rem;
        font-family: 'Menlo', 'Consolas', monospace;
        font-size: 0.75rem;
        line-height: 1.6;
        white-space: pre-wrap;
        max-height: 400px;
        overflow-y: auto;
        color: #000;
        margin-top: 0.75rem;
    }

    /* ── ALERTS ── */
    .stAlert, [data-testid="stAlert"] {
        border: 1px solid #000 !important;
        background: transparent !important;
        font-family: 'Geist', Arial, Helvetica, sans-serif;
        font-size: 0.8rem;
    }

    /* ── LINKS ── */
    a {
        color: #000;
        font-weight: 600;
        text-decoration: none;
        transition: opacity 0.3s ease-out;
    }
    a:hover {
        opacity: 0.7;
    }

    /* ── MISC ── */
    [data-testid="stTooltipIcon"] svg {
        color: #a3a3a3;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
#  NAV — top bar, 2-column grid like Nav.tsx
# ═══════════════════════════════════════════════════════════════════════

# Read current step from query params
params = st.query_params
step = params.get("step", "Google Doc")
if step not in STEPS:
    step = "Google Doc"

# Build nav links
nav_links = ""
for s in STEPS:
    active = ' class="active"' if s == step else ""
    nav_links += f'<a href="?step={s}"{active}>{s}</a>\n'

nav_html = (
    '<div class="site-nav">'
    '<div class="site-masthead">Story<br>Workflow</div>'
    '<div class="site-nav-links">'
    + nav_links +
    '</div></div>'
)
st.markdown(nav_html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════

def run_script(cmd: list[str], label: str = "Running..."):
    """Run a subprocess, stream output, return (success, output)."""
    with st.spinner(label):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(SCRIPT_DIR),
            )
            output = result.stdout + result.stderr
            return result.returncode == 0, output.strip()
        except subprocess.TimeoutExpired:
            return False, "ERROR: Script timed out (120s limit)."
        except Exception as e:
            return False, f"ERROR: {e}"


def show_output(success: bool, output: str):
    """Display script output in a styled box."""
    if success:
        st.success("Done!")
    else:
        st.error("Something went wrong.")
    if output:
        st.markdown(
            f'<div class="output-box">{output}</div>',
            unsafe_allow_html=True,
        )


def save_uploaded_file(uploaded) -> str:
    """Save an uploaded file to a temp path and return the path."""
    suffix = Path(uploaded.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getvalue())
        return tmp.name


# ═══════════════════════════════════════════════════════════════════════
#  Grid helper — [1fr spacer, 2fr content] like contact form
# ═══════════════════════════════════════════════════════════════════════
GRID = [1, 2]


# ═══════════════════════════════════════════════════════════════════════
#  STEP 1 — Notes → Google Doc Outline
# ═══════════════════════════════════════════════════════════════════════

if step == "Google Doc":
    header_col, content = st.columns(GRID)
    with header_col:
        st.markdown('<div class="step-header">Notes → Google Doc Outline</div>', unsafe_allow_html=True)
        st.markdown('<div class="step-sub">Upload a notes file and create a structured outline in Google Docs.</div>', unsafe_allow_html=True)
    with content:
        source_type = st.radio("Source", ["Upload file", "Google Doc URL"], horizontal=True)

        source_path = None
        gdoc_url = None

        if source_type == "Upload file":
            uploaded = st.file_uploader(
                "Notes file",
                type=["txt", "docx", "pdf", "rtf"],
                help="Supported: .txt, .docx, .pdf, .rtf",
            )
            if uploaded:
                source_path = save_uploaded_file(uploaded)
        else:
            gdoc_url = st.text_input("Google Doc URL", placeholder="https://docs.google.com/document/d/...")

        st.markdown("#### Output Settings")
        col_a, col_b = st.columns(2)
        with col_a:
            title = st.text_input("Outline title", placeholder="My Story Outline")
        with col_b:
            folder = st.text_input("Drive folder (optional)", placeholder="Writing/Outlines")

        credentials = st.text_input(
            "Credentials JSON path (optional)",
            placeholder="~/.config/google/credentials.json",
            help="Path to your Google OAuth credentials file. Leave blank to use default.",
        )

    _spacer2, action_col = st.columns(GRID)
    with action_col:
        if st.button("Create Outline", type="primary"):
            cmd = [sys.executable, str(SCRIPT_DIR / "notes_to_gdoc_outline.py")]

            if source_type == "Upload file":
                if not source_path:
                    st.warning("Please upload a file first.")
                    st.stop()
                cmd += ["--file", source_path]
            else:
                if not gdoc_url:
                    st.warning("Please enter a Google Doc URL.")
                    st.stop()
                if "docs.google.com" in gdoc_url or "drive.google.com" in gdoc_url:
                    cmd += ["--doc-id", gdoc_url]
                else:
                    cmd += ["--doc", gdoc_url]

            if title:
                cmd += ["--title", title]
            if folder:
                cmd += ["--output-folder", folder]
            if credentials:
                cmd += ["--credentials", credentials]

            ok, out = run_script(cmd, "Creating Google Doc outline...")
            show_output(ok, out)


# ═══════════════════════════════════════════════════════════════════════
#  STEP 2 — Notes → Bike Outline
# ═══════════════════════════════════════════════════════════════════════

elif step == "Bike Outline":
    header_col, content = st.columns(GRID)
    with header_col:
        st.markdown('<div class="step-header">Notes → Bike Outline</div>', unsafe_allow_html=True)
        st.markdown('<div class="step-sub">Upload a notes file and export a .bike outline for Bike Outliner.</div>', unsafe_allow_html=True)
    with content:
        source_type = st.radio("Source", ["Upload file", "Google Doc URL"], horizontal=True, key="bike_source")

        source_path = None
        gdoc_url = None

        if source_type == "Upload file":
            uploaded = st.file_uploader(
                "Notes file",
                type=["txt", "docx", "pdf", "rtf"],
                help="Supported: .txt, .docx, .pdf, .rtf",
                key="bike_upload",
            )
            if uploaded:
                source_path = save_uploaded_file(uploaded)
        else:
            gdoc_url = st.text_input("Google Doc URL", placeholder="https://docs.google.com/document/d/...", key="bike_gdoc")

        st.markdown("#### Output Settings")
        col_a, col_b = st.columns(2)
        with col_a:
            output_name = st.text_input("Output filename (optional)", placeholder="outline.bike")
        with col_b:
            output_dir = st.text_input("Output directory", value=str(Path.home() / "Desktop"), key="bike_outdir")

    _spacer2, action_col = st.columns(GRID)
    with action_col:
        if st.button("Create .bike Outline", type="primary"):
            cmd = [sys.executable, str(SCRIPT_DIR / "notes_to_bike.py")]

            if source_type == "Upload file":
                if not source_path:
                    st.warning("Please upload a file first.")
                    st.stop()
                cmd += ["--file", source_path]
            else:
                if not gdoc_url:
                    st.warning("Please enter a Google Doc URL.")
                    st.stop()
                if "docs.google.com" in gdoc_url or "drive.google.com" in gdoc_url:
                    cmd += ["--doc-id", gdoc_url]
                else:
                    cmd += ["--doc", gdoc_url]

            if output_name:
                cmd += ["--output", output_name]
            if output_dir:
                cmd += ["--output-dir", output_dir]

            ok, out = run_script(cmd, "Creating .bike outline...")
            show_output(ok, out)


# ═══════════════════════════════════════════════════════════════════════
#  STEP 3 — Bike → Scrivener
# ═══════════════════════════════════════════════════════════════════════

elif step == "Scrivener":
    header_col, content = st.columns(GRID)
    with header_col:
        st.markdown('<div class="step-header">Bike → Scrivener Project</div>', unsafe_allow_html=True)
        st.markdown('<div class="step-sub">Convert a .bike outline into a Scrivener 3 project (.scriv).</div>', unsafe_allow_html=True)
    with content:
        tab_fwd, tab_rev = st.tabs(["Bike → Scrivener", "Scrivener → Bike"])

        with tab_fwd:
            uploaded = st.file_uploader(
                "Bike outline (.bike)",
                type=["bike"],
                help="Upload your .bike outline file",
                key="scriv_upload",
            )

            output_dir = st.text_input(
                "Output directory",
                value=str(Path.home() / "Documents" / "Writing"),
                key="scriv_outdir",
            )

            if st.button("Create Scrivener Project", type="primary"):
                if not uploaded:
                    st.warning("Please upload a .bike file first.")
                    st.stop()

                bike_path = save_uploaded_file(uploaded)
                cmd = [sys.executable, str(SCRIPT_DIR / "bike_to_scriv.py"), bike_path]

                if output_dir:
                    cmd += ["--output-dir", output_dir]

                ok, out = run_script(cmd, "Building Scrivener project...")
                show_output(ok, out)

                if ok:
                    for line in out.split("\n"):
                        if "Path:" in line:
                            scriv_out = line.split("Path:")[-1].strip()
                            st.markdown(
                                f"[Open {Path(scriv_out).name}](file://{scriv_out})"
                            )
                            break

        with tab_rev:
            scriv_path = st.text_input(
                "Path to .scriv project",
                placeholder="/path/to/My Story.scriv",
                key="rev_scriv_path",
            )

            if st.button("Export to .bike", type="primary", key="rev_btn"):
                if not scriv_path:
                    st.warning("Please enter the path to a .scriv project.")
                    st.stop()

                cmd = [
                    sys.executable, str(SCRIPT_DIR / "bike_to_scriv.py"),
                    "--reverse", scriv_path,
                ]

                ok, out = run_script(cmd, "Exporting .scriv → .bike...")
                show_output(ok, out)

                if ok:
                    for line in out.split("\n"):
                        if "Output:" in line:
                            bike_out = line.split("Output:")[-1].strip()
                            st.markdown(
                                f"[Open {Path(bike_out).name}](file://{bike_out})"
                            )
                            break


# ═══════════════════════════════════════════════════════════════════════
#  STEP 4 — Scrivener → Shunn Manuscript + Cover Letter
# ═══════════════════════════════════════════════════════════════════════

elif step == "Shunn":
    header_col, content = st.columns(GRID)
    with header_col:
        st.markdown('<div class="step-header">Scrivener → Shunn Manuscript</div>', unsafe_allow_html=True)
        st.markdown('<div class="step-sub">Format a compiled manuscript as Shunn short story format (.docx + .pdf) with a cover letter.</div>', unsafe_allow_html=True)
    with content:
        input_mode = st.radio("Input type", ["Upload compiled file", "Path to .scriv project"], horizontal=True)

        source_path = None
        if input_mode == "Upload compiled file":
            uploaded = st.file_uploader(
                "Compiled manuscript",
                type=["txt", "docx", "rtf"],
                help="Supported: .txt, .docx, .rtf (the compiled output from Scrivener)",
                key="shunn_upload",
            )
            if uploaded:
                source_path = save_uploaded_file(uploaded)
        else:
            source_path = st.text_input(
                "Path to .scriv project",
                placeholder="/path/to/My Story.scriv",
                key="shunn_scriv_path",
            )

        st.markdown("#### Manuscript Details")

        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Story title", placeholder="The Cardinal", key="shunn_title")
            author = st.text_input("Author name", value="W. S. Gong", key="shunn_author")
        with col2:
            email = st.text_input("Email", placeholder="writer@example.com", key="shunn_email")
            phone = st.text_input("Phone (optional)", placeholder="555-123-4567", key="shunn_phone")

        address = st.text_input(
            "Mailing address (optional)",
            placeholder="123 Main St, City, ST 12345",
            key="shunn_address",
        )

        st.markdown("#### Output")
        output_dir = st.text_input(
            "Output directory",
            value=str(Path.home() / "Documents" / "Writing" / "Stories"),
            help="Files will be placed in a subfolder named Title-MM-DD-YYYY",
            key="shunn_outdir",
        )

    _spacer2, action_col = st.columns(GRID)
    with action_col:
        if st.button("Format & Export", type="primary"):
            if not source_path:
                st.warning("Please provide an input file.")
                st.stop()

            cmd = [sys.executable, str(SCRIPT_DIR / "scriv_to_shunn.py"), source_path]

            if title:
                cmd += ["--title", title]
            if author:
                cmd += ["--author", author]
            if email:
                cmd += ["--email", email]
            if phone:
                cmd += ["--phone", phone]
            if address:
                cmd += ["--address", address]
            if output_dir:
                cmd += ["--output-dir", output_dir]

            ok, out = run_script(cmd, "Formatting Shunn manuscript + cover letter...")
            show_output(ok, out)

            if ok:
                st.markdown("#### Output Files")
                for line in out.split("\n"):
                    if "Directory:" in line:
                        final_dir = line.split("Directory:")[-1].strip()
                        try:
                            files = os.listdir(final_dir)
                            for f in sorted(files):
                                fpath = os.path.join(final_dir, f)
                                size_kb = os.path.getsize(fpath) / 1024
                                st.markdown(f"**{f}** ({size_kb:.1f} KB)")
                        except Exception:
                            pass
                        break
