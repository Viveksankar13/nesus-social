#!/usr/bin/env python3
"""
build_pdf.py — Nexus Social System Documentation PDF Builder
============================================================

Builds docs/pdf/SYSTEM_DOCUMENTATION.pdf from all markdown files in docs/.

Usage:
    cd docs/pdf
    python build_pdf.py [--sample]

    --sample    Build a sample/proof-of-concept PDF only (used in Stage 0)

Requirements:
    pip install markdown weasyprint Pygments
    npm install -g @mermaid-js/mermaid-cli   (for mermaid rendering)

Fallback:
    If WeasyPrint fails (missing system libraries), falls back to
    Playwright/Chromium print-to-PDF. Install with:
        pip install playwright && playwright install chromium
"""

import argparse
import datetime
import os
import shutil
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent.resolve()
DOCS_DIR = SCRIPT_DIR.parent
ROOT_DIR = DOCS_DIR.parent
DIAGRAMS_DIR = DOCS_DIR / "diagrams"
OUTPUT_PDF = SCRIPT_DIR / "SYSTEM_DOCUMENTATION.pdf"
STYLE_CSS = SCRIPT_DIR / "style.css"

# ---------------------------------------------------------------------------
# Markdown source order (chapters)
# ---------------------------------------------------------------------------
CHAPTER_ORDER = [
    # Stage docs
    ("stages/STAGE_00.md", "Stage 0: Planning & Scaffold"),
    ("stages/STAGE_01.md", "Stage 1: Database Layer"),
    ("stages/STAGE_02.md", "Stage 2: Authentication Backend"),
    ("stages/STAGE_03.md", "Stage 3: Core Social Backend"),
    ("stages/STAGE_04.md", "Stage 4: Notifications & Real-time"),
    ("stages/STAGE_05.md", "Stage 5: Admin Backend"),
    ("stages/STAGE_06.md", "Stage 6: Gemini AI Service"),
    ("stages/STAGE_07.md", "Stage 7: Frontend Foundation"),
    ("stages/STAGE_08.md", "Stage 8: User App UI"),
    ("stages/STAGE_09.md", "Stage 9: Admin Console UI"),
    ("stages/STAGE_10.md", "Stage 10: Hardening"),
    ("stages/STAGE_11.md", "Stage 11: Deployment"),
    ("stages/STAGE_12.md", "Stage 12: Documentation & Submission"),
    # Reference docs
    ("ER_DIAGRAM.md", "Database ER Diagram"),
    ("AI_INTEGRATION.md", "AI Integration Details"),
    ("API.md", "API Reference"),
    ("DEPLOYMENT.md", "Deployment Guide"),
    # Hyper-Local Skill Swap Economy (Chapters 17–24)
    ("chapters/CHAPTER_17_SKILL_SWAP_OVERVIEW.md", "Chapter 17: Skill Swap Product Overview"),
    ("chapters/CHAPTER_18_HYPER_LOCAL_DESIGN.md", "Chapter 18: Hyper-Local Design & Location Privacy"),
    ("chapters/CHAPTER_19_MATCHING_ENGINE.md", "Chapter 19: Matching Engine & Recommendation Architecture"),
    ("chapters/CHAPTER_20_SWAP_LIFECYCLE.md", "Chapter 20: Swap Lifecycle & Scheduling Engine"),
    ("chapters/CHAPTER_21_TRUST_REPUTATION_SAFETY.md", "Chapter 21: Trust, Reputation & Safety Systems"),
    ("chapters/CHAPTER_22_AI_FEATURES_PROMPTS.md", "Chapter 22: Skill Swap AI Features & Prompt Engineering"),
    ("chapters/CHAPTER_23_ADMIN_TOOLS_ANALYTICS.md", "Chapter 23: Skill Swap Admin Console & Analytics"),
    ("chapters/CHAPTER_24_API_REFERENCE_DEPLOYMENT.md", "Chapter 24: Skill Swap API Reference & Data Architecture"),
    # Skill Swap Stage Verification Documents
    ("stages/SWAP_STAGE_1.md", "Skill Swap Stage S1: Taxonomy & Profiles"),
    ("stages/SWAP_STAGE_2.md", "Skill Swap Stage S2: Listings & Discovery"),
    ("stages/SWAP_STAGE_3.md", "Skill Swap Stage S3: Swaps & Sessions"),
    ("stages/SWAP_STAGE_4.md", "Skill Swap Stage S4: Safety, Admin & AI Helpers"),
    ("stages/SWAP_STAGE_5.md", "Skill Swap Stage S5: Hardening, Deploy & Documentation"),
]

# ---------------------------------------------------------------------------
# Helper: render Mermaid diagrams to PNG
# ---------------------------------------------------------------------------
def render_mermaid_diagrams() -> None:
    """Convert all .mmd files in docs/diagrams/ to PNG using mmdc."""
    mmdc = shutil.which("mmdc")
    if not mmdc:
        print("⚠  mmdc not found — skipping Mermaid rendering (install: npm i -g @mermaid-js/mermaid-cli)")
        return

    for mmd_file in DIAGRAMS_DIR.glob("*.mmd"):
        png_file = mmd_file.with_suffix(".png")
        print(f"   Rendering {mmd_file.name} → {png_file.name}")
        result = subprocess.run(
            [mmdc, "-i", str(mmd_file), "-o", str(png_file), "-b", "white", "-w", "1200"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"   ⚠  mmdc error: {result.stderr}")


# ---------------------------------------------------------------------------
# Helper: convert Markdown to HTML
# ---------------------------------------------------------------------------
def md_to_html(md_text: str, docs_base: Path) -> str:
    """Convert Markdown text to HTML string."""
    try:
        import markdown
        from markdown.extensions.codehilite import CodeHiliteExtension
        from markdown.extensions.fenced_code import FencedCodeExtension
        from markdown.extensions.tables import TableExtension
        from markdown.extensions.toc import TocExtension

        extensions = [
            FencedCodeExtension(),
            CodeHiliteExtension(linenums=False, css_class="highlight"),
            TableExtension(),
            TocExtension(title="Contents", toc_depth=3),
            "markdown.extensions.attr_list",
            "markdown.extensions.def_list",
            "markdown.extensions.admonition",
        ]
        md = markdown.Markdown(extensions=extensions)
        return md.convert(md_text)
    except ImportError:
        print("❌ 'markdown' package not installed. Run: pip install markdown Pygments")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Build sample PDF (Stage 0 proof-of-concept)
# ---------------------------------------------------------------------------
def build_sample_pdf() -> Path:
    """Build a minimal sample PDF to prove the toolchain works."""
    sample_md = """
# Nexus Social — System Documentation

## Stage 0: Proof of Concept

This is a sample PDF generated in **Stage 0** to verify the PDF build toolchain.

### Toolchain Verified

| Component | Status |
|-----------|--------|
| Python Markdown | ✅ Working |
| WeasyPrint / Playwright | ✅ Working |
| PDF output | ✅ Verified |

### Code Sample

```python
def hello_nexus():
    \"\"\"Greet the Nexus Social platform.\"\"\"
    return "Welcome to Nexus Social!"
```

### What's Next

Full system documentation will be compiled here at Stage 12, including:

- Architecture diagrams
- API reference tables
- Security deep-dive
- Deployment runbook
- Stage-by-stage implementation log

---

*Generated: {date}*
""".format(date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M UTC"))

    out = SCRIPT_DIR / "SAMPLE_STAGE0.pdf"
    html_body = md_to_html(sample_md, DOCS_DIR)
    _render_pdf(html_body, out, title="Nexus Social – Stage 0 Sample")
    return out


# ---------------------------------------------------------------------------
# Build full PDF
# ---------------------------------------------------------------------------
def build_full_pdf() -> Path:
    """Compile all stage docs and reference docs into one PDF."""
    render_mermaid_diagrams()

    html_parts: list[str] = []

    # Cover page
    now = datetime.datetime.now()
    html_parts.append(f"""
<div class="cover">
  <div class="cover-logo">🌐</div>
  <h1>Nexus Social</h1>
  <div class="subtitle">AI-Powered Social Media Platform<br>System Documentation</div>
  <div class="meta">
    Generated: {now.strftime("%B %d, %Y")} &nbsp;|&nbsp;
    Version: 1.0 &nbsp;|&nbsp;
    Stack: Next.js 14 · FastAPI · PostgreSQL · Gemini AI
  </div>
</div>
""")

    # Chapters
    for rel_path, title in CHAPTER_ORDER:
        md_file = DOCS_DIR / rel_path
        if not md_file.exists():
            html_parts.append(f"<h1>{title}</h1><p><em>Not yet written.</em></p>")
            continue
        md_text = md_file.read_text(encoding="utf-8")
        html_body = md_to_html(md_text, DOCS_DIR)
        html_parts.append(html_body)

    full_html = "\n".join(html_parts)
    _render_pdf(full_html, OUTPUT_PDF, title="Nexus Social – System Documentation")
    return OUTPUT_PDF


# ---------------------------------------------------------------------------
# PDF rendering: WeasyPrint with Playwright fallback
# ---------------------------------------------------------------------------
def _render_pdf(html_body: str, output_path: Path, title: str) -> None:
    """Write HTML to PDF, trying WeasyPrint first, then Playwright."""
    css_text = STYLE_CSS.read_text(encoding="utf-8") if STYLE_CSS.exists() else ""

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>{css_text}</style>
</head>
<body>
{html_body}
</body>
</html>"""

    # Try WeasyPrint
    try:
        import weasyprint  # type: ignore[import]
        print(f"   📄 Rendering PDF with WeasyPrint → {output_path.name}")
        weasyprint.HTML(string=full_html, base_url=str(SCRIPT_DIR)).write_pdf(
            str(output_path)
        )
        print(f"   ✅ PDF written: {output_path}")
        return
    except ImportError:
        print("   ⚠  WeasyPrint not installed, trying Playwright fallback…")
    except Exception as exc:
        print(f"   ⚠  WeasyPrint failed ({exc}), trying Playwright fallback…")

    # Playwright fallback
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import]

        tmp_html = output_path.with_suffix(".tmp.html")
        tmp_html.write_text(full_html, encoding="utf-8")
        print(f"   📄 Rendering PDF with Playwright → {output_path.name}")
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(tmp_html.as_uri())
            page.pdf(path=str(output_path), format="A4", print_background=True)
            browser.close()
        tmp_html.unlink()
        print(f"   ✅ PDF written: {output_path}")
        return
    except ImportError:
        print("   ⚠  Playwright not installed, trying system Headless Chromium/Edge fallback…")
    except Exception as exc:
        print(f"   ⚠  Playwright also failed ({exc}), trying system Headless Chromium/Edge fallback…")

    # Headless Edge / Chrome fallback (always available on Windows)
    browser_candidates = [
        Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
        Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
        Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
    ]
    browser_exe = next((b for b in browser_candidates if b.exists()), None)
    if not browser_exe:
        browser_exe_str = shutil.which("msedge") or shutil.which("chrome") or shutil.which("chromium")
        if browser_exe_str:
            browser_exe = Path(browser_exe_str)

    if browser_exe and browser_exe.exists():
        if output_path.exists():
            output_path.unlink()
        tmp_html = output_path.with_suffix(".tmp.html")
        tmp_html.write_text(full_html, encoding="utf-8")
        print(f"   📄 Rendering PDF with Headless Browser ({browser_exe.name}) → {output_path.name}")
        cmd = [
            str(browser_exe),
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--no-pdf-header-footer",
            f"--print-to-pdf={output_path}",
            str(tmp_html),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if tmp_html.exists():
            tmp_html.unlink()
        if output_path.exists() and output_path.stat().st_size > 0:
            print(f"   ✅ PDF written: {output_path}")
            return
        else:
            print(f"   ⚠  Headless browser run failed: {res.stderr}")

    print("❌ Neither WeasyPrint, Playwright, nor Headless Chromium could generate the PDF.")
    print("   Please install one of:")
    print("     pip install weasyprint")
    print("     pip install playwright && playwright install chromium")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Build Nexus Social System Documentation PDF")
    parser.add_argument("--sample", action="store_true", help="Build Stage 0 sample PDF only")
    args = parser.parse_args()

    print("🔨 Nexus Social — PDF Builder")
    print(f"   Output dir: {SCRIPT_DIR}")
    print()

    if args.sample:
        out = build_sample_pdf()
        print(f"\n✅ Sample PDF ready: {out}")
    else:
        out = build_full_pdf()
        print(f"\n✅ Full documentation PDF ready: {out}")


if __name__ == "__main__":
    main()
