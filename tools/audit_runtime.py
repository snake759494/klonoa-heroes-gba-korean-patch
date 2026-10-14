"""Audit translated scenario pages against the game's dialogue-box limits.

Run after tools/compile_tr.py. This checks the exact wrapped text that the ROM
builder will encode; it is static layout evidence, not a substitute for an
emulator play-through.
"""
import json
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import build
from kowrap import width

MESSAGES = os.path.join(ROOT, "work", "tr", "messages_ko.json")
SEPARATOR = re.compile(r"(<PAGE><CLR>|<PAGE>|<CLR>|<END>)")
PORTRAIT = re.compile(r"<FFFC>.")
LIMIT_CELLS = build.CELLS
LIMIT_LINES = build.MAXLINES


def pages_of(laid_out):
    """Return visible line lists; PAGE's newline parameter is not a blank line."""
    pages, lines, last_delimiter = [], [], None
    for part in SEPARATOR.split(laid_out):
        if not part:
            continue
        if SEPARATOR.fullmatch(part):
            if lines:
                pages.append(lines)
                lines = []
            last_delimiter = part
            continue
        if last_delimiter == "<PAGE>" and part.startswith("\n"):
            part = part[1:]
        lines.extend(part.split("\n"))
        last_delimiter = None
    if lines:
        pages.append(lines)
    return pages


def main():
    messages = json.load(open(MESSAGES, encoding="utf-8"))
    overflow = []
    too_many_lines = []
    warnings = []
    max_cells = 0
    max_lines = 0
    for address, source in messages.items():
        laid, warn = build.layout(source)
        warnings.extend((address, x) for x in warn)
        if len(PORTRAIT.findall(source)) != len(PORTRAIT.findall(laid)):
            warnings.append((address, "portrait control count changed during layout"))
        if source.count("<END>") != laid.count("<END>"):
            warnings.append((address, "END control count changed during layout"))
        for page_index, lines in enumerate(pages_of(laid), 1):
            max_lines = max(max_lines, len(lines))
            if len(lines) > LIMIT_LINES:
                too_many_lines.append((address, page_index, len(lines)))
            for line_index, line in enumerate(lines, 1):
                cells = width(line)
                max_cells = max(max_cells, cells)
                if cells > LIMIT_CELLS:
                    overflow.append((address, page_index, line_index, cells, line))

    print("scenario messages:", len(messages))
    print("dialogue limit:", f"{LIMIT_CELLS} cells x {LIMIT_LINES} lines")
    print("maximum emitted line:", f"{max_cells} cells")
    print("maximum emitted page:", f"{max_lines} lines")
    print("over-width lines:", len(overflow))
    print("over-height pages:", len(too_many_lines))
    print("layout/control warnings:", len(warnings))
    for address, page, line, cells, text in overflow:
        print(f"OVERFLOW {address} page={page} line={line} cells={cells}: {text!r}")
    for item in too_many_lines:
        print("TOO MANY LINES", *item)
    for item in warnings:
        print("WARNING", *item)
    if overflow or too_many_lines or warnings:
        return 1
    print("result: PASS (static scenario layout only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
