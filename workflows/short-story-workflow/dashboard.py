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


# ═══════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Short Story Workflow",
    page_icon="✒️",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──
st.markdown("""
<style>
    /* Softer background */
    .stApp { background-color: #fafaf8; }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #f0efe8;
    }
    section[data-testid="stSidebar"] .stRadio label {
        font-size: 1.05rem;
    }

    /* Step headers */
    .step-header {
        font-family: 'Georgia', serif;
        font-size: 1.6rem;
        color: #2c2c2c;
        margin-bottom: 0.2rem;
    }
    .step-sub {
        color: #777;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }

    /* Output box */
    .output-box {
        background: #f7f7f0;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        font-family: 'Menlo', 'Consolas', monospace;
        font-size: 0.85rem;
        white-space: pre-wrap;
        max-height: 400px;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
#  SIDEBAR — STEP SELECTOR
# ═══════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## ✒️ Story Workflow")
    st.markdown("---")

    step = st.radio(
        "Pipeline Step",
        [
            "1 · Notes → Google Doc",
            "2 · Notes → Bike Outline",
            "3 · Bike → Scrivener",
            "4 · Scrivener → Shunn",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown(
        "<small style='color:#999'>Scripts live in:<br>"
        f"<code>{SCRIPT_DIR}</code></small>",
        unsafe_allow_html=True,
    )


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
#  STEP 1 — Notes → Google Doc Outline
# ═══════════════════════════════════════════════════════════════════════

if step.startswith("1"):
    st.markdown('<div class="step-header">Notes → Google Doc Outline</div>', unsafe_allow_html=True)
    st.markdown('<div class="step-sub">Upload a notes file and create a structured outline in Google Docs.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
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

    if st.button("Create Outline", type="primary", use_container_width=True):
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

elif step.startswith("2"):
    st.markdown('<div class="step-header">Notes → Bike Outline</div>', unsafe_allow_html=True)
    st.markdown('<div class="step-sub">Upload a notes file and export a .bike outline for Bike Outliner.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
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

    if st.button("Create .bike Outline", type="primary", use_container_width=True):
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

elif step.startswith("3"):
    st.markdown('<div class="step-header">Bike → Scrivener Project</div>', unsafe_allow_html=True)
    st.markdown('<div class="step-sub">Convert a .bike outline into a Scrivener 3 project (.scriv).</div>', unsafe_allow_html=True)

    tab_fwd, tab_rev = st.tabs(["Bike → Scrivener", "Scrivener → Bike (reverse)"])

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

        if st.button("Create Scrivener Project", type="primary", use_container_width=True):
            if not uploaded:
                st.warning("Please upload a .bike file first.")
                st.stop()

            bike_path = save_uploaded_file(uploaded)
            cmd = [sys.executable, str(SCRIPT_DIR / "bike_to_scriv.py"), bike_path]

            if output_dir:
                cmd += ["--output-dir", output_dir]

            ok, out = run_script(cmd, "Building Scrivener project...")
            show_output(ok, out)

    with tab_rev:
        scriv_path = st.text_input(
            "Path to .scriv project",
            placeholder="/path/to/My Story.scriv",
            key="rev_scriv_path",
        )

        if st.button("Export to .bike", type="primary", use_container_width=True, key="rev_btn"):
            if not scriv_path:
                st.warning("Please enter the path to a .scriv project.")
                st.stop()

            cmd = [
                sys.executable, str(SCRIPT_DIR / "bike_to_scriv.py"),
                "--reverse", scriv_path,
            ]

            ok, out = run_script(cmd, "Exporting .scriv → .bike...")
            show_output(ok, out)


# ═══════════════════════════════════════════════════════════════════════
#  STEP 4 — Scrivener → Shunn Manuscript + Cover Letter
# ═══════════════════════════════════════════════════════════════════════

elif step.startswith("4"):
    st.markdown('<div class="step-header">Scrivener → Shunn Manuscript</div>', unsafe_allow_html=True)
    st.markdown('<div class="step-sub">Format a compiled manuscript as Shunn short story format (.docx + .pdf) with a cover letter.</div>', unsafe_allow_html=True)

    # Source input
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

    if st.button("Format & Export", type="primary", use_container_width=True):
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
            # Show what was created
            st.markdown("#### Output Files")
            # Parse the output directory from script output
            for line in out.split("\n"):
                if "Directory:" in line:
                    final_dir = line.split("Directory:")[-1].strip()
                    try:
                        files = os.listdir(final_dir)
                        for f in sorted(files):
                            fpath = os.path.join(final_dir, f)
                            size_kb = os.path.getsize(fpath) / 1024
                            icon = "📄" if f.endswith(".docx") else "📕" if f.endswith(".pdf") else "📎"
                            st.markdown(f"{icon} **{f}** ({size_kb:.1f} KB)")
                    except Exception:
                        pass
                    break
