# Songs of Freedom

**Overview**
- This repository contains the manuscript for “Songs of Freedom,” organized as Markdown chapters under `chapters/` with a small tool to regenerate them from a Word document.
- Chapters are numbered and slugged (e.g., `01-preface.md`, `02-introduction.md`) to keep order stable.

**Project Structure**
- `chapters/` — Per‑chapter Markdown files ready for editing and version control. Example: `chapters/01-preface.md`.
- `tools/convert_docx_to_md.py` — Python script that splits a DOCX into per‑chapter Markdown by detecting Heading 1/Title and common chapter markers.
- `Songs-of-Freedom.docx` — Source DOCX exported from Pages (optional; used to regenerate chapters).

**Editing Workflow**
- Prefer editing the Markdown chapters directly in `chapters/`.
- If updating from the source document, export a fresh DOCX from Pages and regenerate chapters (instructions below), then review diffs.

**Regenerate Chapters from DOCX**
- Requirements: Python 3 (no third‑party packages needed).
- Command: `python tools/convert_docx_to_md.py Songs-of-Freedom.docx chapters`
- Notes:
  - The converter treats “Heading 1” (and “Title”) as chapter starts. Subheads map to `##`/`###`.
  - If Heading 1 is absent, it uses sensible text heuristics (e.g., “Preface”, “Introduction”, title‑case lines) to split sections.

**Combine Chapters (optional)**
- Quick one‑file export: `cat chapters/*.md > Manuscript.md`
- Tip: This will include multiple `#` headings (one per chapter), which is fine for most Markdown readers.

**Conventions**
- Each chapter file begins with a single `#` title line.
- Keep filenames short, lowercase, and hyphen‑separated. The numeric prefix preserves order.
- Images or assets (if added later) should use relative paths from chapter files.

**Preview**
- Any Markdown viewer works (VS Code, GitHub, Obsidian, etc.). No build step is required.

**Utilities**
- Script source: `tools/convert_docx_to_md.py`
- Example chapter: `chapters/02-introduction.md`

