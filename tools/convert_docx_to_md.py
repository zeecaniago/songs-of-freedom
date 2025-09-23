#!/usr/bin/env python3
"""
Convert a DOCX manuscript into per-chapter Markdown files.

Chapters are detected by Heading 1 paragraphs ("Heading1").
Other headings map to Markdown levels. Lists and basic paragraphs
are handled; inline styling is not preserved to keep things simple
and robust without external dependencies.

Usage:
  python tools/convert_docx_to_md.py INPUT.docx OUTPUT_DIR

This script avoids third-party packages: it parses the DOCX XML directly.
"""

import sys
import re
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{" + W_NS + "}"


def get_text_from_runs(p):
    parts = []
    # Paragraphs can contain runs directly or nested within hyperlinks.
    for elem in p.iter():
        if elem.tag == W + "t":
            parts.append(elem.text or "")
        elif elem.tag == W + "br":
            parts.append("\n")
    # Collapse multiple spaces but preserve intentional newlines from <w:br/>
    text = "".join(parts)
    # Normalize spaces
    text = re.sub(r"[ \t]+", " ", text)
    # Trim stray spaces around newlines
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def get_para_style(p):
    pPr = p.find(W + "pPr")
    if pPr is None:
        return None
    pStyle = pPr.find(W + "pStyle")
    if pStyle is not None:
        val = pStyle.get(W + "val")
        if val:
            return val
    # Some documents use outline level; treat outlineLvl=0 as Heading1, etc.
    outline = pPr.find(W + "outlineLvl")
    if outline is not None:
        lvl = outline.get(W + "val")
        if lvl is not None:
            try:
                n = int(lvl)
                return f"Heading{n+1}"
            except ValueError:
                pass
    return None


def is_list_paragraph(p):
    pPr = p.find(W + "pPr")
    if pPr is None:
        return False
    return pPr.find(W + "numPr") is not None


def md_escape(text: str) -> str:
    # Minimal escaping for Markdown headings and list markers at line start.
    return text.replace("\r", "").replace("\u00A0", " ")


def slugify(title: str) -> str:
    s = title.strip().lower()
    s = re.sub(r"['\"]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "chapter"


def parse_docx(docx_path: Path):
    with zipfile.ZipFile(docx_path) as z:
        with z.open("word/document.xml") as f:
            tree = ET.parse(f)
    root = tree.getroot()
    body = root.find(W + "body")
    if body is None:
        raise RuntimeError("Invalid DOCX: missing body")
    return list(body.findall(W + "p"))


def convert(docx_path: Path, out_dir: Path):
    paras = parse_docx(docx_path)

    chapters = []  # list of (title, [markdown lines])
    current_title = None
    current_lines = []

    known_chapter_re = re.compile(
        r"^(?:(?:chapter|prologue|epilogue|preface|introduction|afterword|acknowledg(?:ements|ment))\b.*)$",
        re.IGNORECASE,
    )
    stopwords = {"of", "the", "and", "a", "an", "to", "from", "for", "in", "on", "with", "without", "or", "by"}

    def looks_like_title_case(s: str) -> bool:
        words = [w for w in re.split(r"\s+", s) if w]
        if not (1 <= len(words) <= 8):
            return False
        ok = 0
        for w in words:
            wn = re.sub(r"[^A-Za-z0-9']", "", w)
            if not wn:
                continue
            lw = wn.lower()
            if lw in stopwords:
                ok += 1
                continue
            if wn[0].isupper():
                ok += 1
            else:
                return False
        return ok == len(words)

    def is_chapter_start_text(text: str, next_text: str, is_first_para: bool) -> bool:
        t = text.strip()
        # Ignore very short fragments
        if len(t) < 3:
            return False
        if known_chapter_re.match(t):
            return True
        # Avoid treating the book title (often first line) as a chapter
        if is_first_para:
            return False
        # Heuristic: short, no terminal punctuation, looks like Title Case, next paragraph is long
        if len(t) <= 60 and not re.search(r"[.!?]$", t) and looks_like_title_case(t):
            if next_text and len(next_text) >= 80:
                return True
        return False

    def start_new_chapter(title: str):
        nonlocal current_title, current_lines
        if current_title is not None:
            chapters.append((current_title, current_lines))
        current_title = title.strip() or "Untitled"
        current_lines = [f"# {md_escape(current_title)}\n"]

    n = len(paras)
    for i, p in enumerate(paras):
        style = (get_para_style(p) or "").lower()
        text = get_text_from_runs(p)
        # Compute next non-empty paragraph's text for heuristics
        next_text = ""
        for j in range(i + 1, n):
            nt = get_text_from_runs(paras[j])
            if nt:
                next_text = nt
                break

        if not text:
            # Blank paragraph: add a blank line to separate blocks
            if current_lines:
                current_lines.append("")
            continue

        # Chapter boundary: Heading 1 or Title style
        if style in {"heading1", "heading 1", "title"} or is_chapter_start_text(text, next_text, is_first_para=(i == 0)):
            start_new_chapter(text)
            continue

        # Within a chapter, map other headings
        if style in {"heading2", "heading 2"}:
            current_lines.append(f"\n## {md_escape(text)}\n")
            continue
        if style in {"heading3", "heading 3"}:
            current_lines.append(f"\n### {md_escape(text)}\n")
            continue

        if is_list_paragraph(p):
            # Without reading numbering.xml, default to unordered list
            current_lines.append(f"- {md_escape(text)}")
        else:
            current_lines.append(md_escape(text))

    # Flush last chapter or create a single chapter fallback
    if current_title is None:
        # No Heading1 seen: dump entire doc as one chapter
        whole = [md_escape(get_text_from_runs(p)) for p in paras]
        whole = [x for x in whole if x]
        if not whole:
            raise RuntimeError("No content found in DOCX")
        chapters.append(("Manuscript", ["# Manuscript\n", *whole]))
    else:
        chapters.append((current_title, current_lines))

    # Write files
    out_dir.mkdir(parents=True, exist_ok=True)
    width = len(str(len(chapters)))
    for idx, (title, lines) in enumerate(chapters, start=1):
        slug = slugify(title)
        fname = f"{idx:0{width}d}-{slug}.md"
        (out_dir / fname).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    return [f for f in sorted(out_dir.iterdir()) if f.suffix == ".md"]


def main(argv):
    if len(argv) != 3:
        print("Usage: python tools/convert_docx_to_md.py INPUT.docx OUTPUT_DIR", file=sys.stderr)
        return 2
    inp = Path(argv[1])
    out = Path(argv[2])
    if not inp.exists():
        print(f"Input not found: {inp}", file=sys.stderr)
        return 2
    files = convert(inp, out)
    print("Wrote:")
    for p in files:
        print(" -", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
