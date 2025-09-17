#!/usr/bin/env python3
"""
smart_page_chunker.py
Goal: Merge page-wise .md files into semantic chunks that
      NEVER break inside a paragraph.
Usage:
    python smart_page_chunker.py  --pages-dir ./pages  --output-dir ./chunks  --max-chars 2000
"""

import re
import os
import argparse
from typing import List, Tuple

SENTENCE_DELIM = re.compile(r'[.!?؟。]')  # Latin + Persian + Chinese sentence endings


# ---------- helpers ----------
# def natural_sort_key(fname: str):
#     """Sort 1.md .. 10.md .. 100.md correctly."""
#     return int(os.path.splitext(fname)[0])
# ---------- helpers ----------
def natural_sort_key(fname: str):
    """Extract trailing number from names like page_1153.md -> 1153"""
    base = os.path.splitext(fname)[0]          # page_1153
    digits = re.search(r'\d+$', base)          # 1153
    return int(digits.group()) if digits else 0

def read_page(path: str) -> str:
    with open(path, encoding='utf-8') as f:
        return f.read()


def split_paragraphs(text: str) -> List[str]:
    """
    Split by *real* paragraph breaks (blank lines).
    Preserve internal newlines of a paragraph (soft-breaks).
    """
    return [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]


def break_long_paragraph(paragraph: str, hard_limit: int) -> List[str]:
    """
    If a single paragraph is longer than hard_limit, break it
    at sentence boundaries.
    """
    if len(paragraph) <= hard_limit:
        return [paragraph]

    sentences = SENTENCE_DELIM.split(paragraph)
    endings = SENTENCE_DELIM.findall(paragraph)
    parts = []
    for i, sent in enumerate(sentences):
        if i < len(endings):
            sent += endings[i]
        if sent.strip():
            parts.append(sent.strip())

    chunks, buffer = [], ""
    for p in parts:
        if len(buffer) + len(p) + 1 <= hard_limit:
            buffer += (" " + p if buffer else p)
        else:
            if buffer:
                chunks.append(buffer.strip())
            buffer = p
    if buffer:
        chunks.append(buffer.strip())
    return chunks


# ---------- core logic ----------
def build_chunks(pages_dir: str, max_chars: int) -> List[str]:
    md_files = sorted(
        [f for f in os.listdir(pages_dir) if f.lower().endswith('.md')],
        key=natural_sort_key
    )
    if not md_files:
        raise ValueError("No *.md files found in pages-dir")

    chunks: List[str] = []
    buffer = ""  # carries incomplete paragraph from previous page

    for fname in md_files:
        text = read_page(os.path.join(pages_dir, fname))
        # merge with carry-over
        full_text = (buffer + "\n\n" + text) if buffer else text
        paragraphs = split_paragraphs(full_text)

        # last paragraph might be incomplete (cut by page break)
        *complete, maybe_incomplete = paragraphs if paragraphs else ["", ""]
        if complete:
            # process all complete paras
            for para in complete:
                if len(para) > max_chars:
                    broken = break_long_paragraph(para, max_chars)
                    chunks.extend(broken)
                else:
                    # try to append to last chunk if possible
                    if chunks and (len(chunks[-1]) + len(para) + 2 <= max_chars):
                        chunks[-1] += "\n\n" + para
                    else:
                        chunks.append(para)

        # decide about the last (maybe incomplete) paragraph
        # it is incomplete if original page did NOT end with blank line(s)
        ends_with_para_break = text.rstrip().endswith(("\n\n", "\n"))
        if ends_with_para_break:
            # it was complete
            if len(maybe_incomplete) > max_chars:
                broken = break_long_paragraph(maybe_incomplete, max_chars)
                chunks.extend(broken)
            else:
                if chunks and (len(chunks[-1]) + len(maybe_incomplete) + 2 <= max_chars):
                    chunks[-1] += "\n\n" + maybe_incomplete
                else:
                    chunks.append(maybe_incomplete)
            buffer = ""
        else:
            # carry it to next page
            buffer = maybe_incomplete

    # After last page, flush any remaining buffer
    if buffer:
        if len(buffer) > max_chars:
            broken = break_long_paragraph(buffer, max_chars)
            chunks.extend(broken)
        else:
            if chunks and (len(chunks[-1]) + len(buffer) + 2 <= max_chars):
                chunks[-1] += "\n\n" + buffer
            else:
                chunks.append(buffer)

    return chunks


def save_chunks(chunks: List[str], output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    for idx, chk in enumerate(chunks, 1):
        out_path = os.path.join(output_dir, f"chunk_{idx:03d}.md")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(chk)
    print(f"Saved {len(chunks)} chunks into {output_dir}")


# ---------- CLI ----------
def main():
    parser = argparse.ArgumentParser(
        description="Smart page-wise chunker that never breaks inside a paragraph.")
    parser.add_argument('--pages-dir', required=True,
                        help='Folder containing 1.md, 2.md, ...')
    parser.add_argument('--output-dir', required=True,
                        help='Folder to save chunk_001.md, chunk_002.md, ...')
    parser.add_argument('--max-chars', type=int, default=2000,
                        help='Maximum characters per chunk (default 2000)')
    args = parser.parse_args()

    chunks = build_chunks(args.pages_dir, args.max_chars)
    save_chunks(chunks, args.output_dir)


if __name__ == '__main__':
    main()