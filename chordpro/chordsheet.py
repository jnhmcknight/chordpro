"""Plain-text chord sheets, with chords on a line of their own above the
lyrics (as OnSong, Ultimate Guitar and most PDFs of charts have them), and
turning their songs into ChordPro.

Usage::

    from chordpro.chordsheet import chord_sheet_to_chordpro, section_kind

    def section(line):
        kind = section_kind(line.rstrip(":"))
        return (kind, line.strip().rstrip(":")) if kind else None

    chordpro = "\n".join(chord_sheet_to_chordpro(text.splitlines(), section))
"""
import re
from collections.abc import Callable, Iterable

# Section names, by their first word, and the ChordPro section each opens
SECTION_KINDS = {
    "verse": "verse",
    "chorus": "chorus",
    "refrain": "chorus",
    "prechorus": "prechorus",
    "bridge": "bridge",
    "intro": "intro",
    "outro": "outro",
    "ending": "outro",
    "coda": "outro",
    "tag": "tag",
    "interlude": "interlude",
    "turnaround": "interlude",
    "vamp": "interlude",
    "instrumental": "instrumental",
    "solo": "solo",
}
_FIRST_WORD_RE = re.compile(r"\s*(pre[- ]?chorus|[A-Za-z]+)", re.IGNORECASE)

CHORD_RE = re.compile(
    r"[A-H][#b♯♭]?(?:maj|min|aug|dim|sus|add|m|M|\d|[#b♯♭+°ø-])*(?:/[A-H][#b♯♭]?)?"
)
# Bar lines, repeats and the like, allowed on a line of chords
_CHORD_LINE_SYMBOLS = re.compile(r"\|+|/|-|%|x\d+|N\.?C\.?", re.IGNORECASE)
# Parenthesised instructions, also allowed on a line of chords
_INSTRUCTION_RE = re.compile(r"\([^)]*\)")
# A line of guitar tab, like "e|---0---3---|"
_TAB_LINE_RE = re.compile(r"^\s*[A-Ga-g][#b]?\s*\|.*-{2,}")


def section_kind(name: str) -> str | None:
    """The ChordPro section a section named *name* ("Verse 1") is, if known."""
    m = _FIRST_WORD_RE.match(name)
    return SECTION_KINDS.get(re.sub(r"[- ]", "", m.group(1).lower())) if m else None


def chord_line(line: str) -> str | None:
    """*line* if it holds only chords (with any instructions), else None.
    A leading "." or "`" marks a line as chords whatever is on it."""
    stripped = line.lstrip()
    if stripped[:1] in (".", "`"):
        return line.replace(stripped[0], "", 1)
    if not stripped or "[" in line or "{" in line:
        return None
    tokens = _INSTRUCTION_RE.sub(" ", line).split()
    if not any(CHORD_RE.fullmatch(t) for t in tokens):
        return None
    if all(CHORD_RE.fullmatch(t) or _CHORD_LINE_SYMBOLS.fullmatch(t) for t in tokens):
        return line
    return None


def place_chords(chords: str, lyric: str = "") -> list[str]:
    """ChordPro for a line of chords over *lyric*: each chord goes in brackets
    where it stood above the lyric. Instructions come first, as comments."""
    had_lyric = bool(lyric.strip())
    comments = [f"{{comment: {m.group(0)[1:-1].strip()}}}" for m in _INSTRUCTION_RE.finditer(chords)]
    chords = _INSTRUCTION_RE.sub(lambda m: " " * len(m.group(0)), chords)
    placed = [(m.start(), m.group(0)) for m in re.finditer(r"\S+", chords)]
    if placed:
        lyric = lyric.ljust(placed[-1][0])
    for column, chord in reversed(placed):
        lyric = f"{lyric[:column]}[{chord}]{lyric[column:]}"
    return comments + ([lyric.rstrip() if had_lyric else lyric.strip()] if placed else [])


def chord_sheet_to_chordpro(
    lines: Iterable[str], section: Callable[[str], tuple[str, str] | None]
) -> list[str]:
    """The ChordPro lines for a chord sheet's song. *section* gives the
    (ChordPro section, label) a line opens, if it's a section label.

    Chords over a lyric go into it; chords with no lyric stay on a line of
    their own. Lines in parentheses become comments, and runs of tab lines
    become tab sections (taking the label of a section they start)."""
    body: list[str] = []
    open_kind: str | None = None
    open_at = 0  # where the open section starts in body
    chords = None  # a line of chords, waiting for its lyric

    def flush():
        nonlocal chords
        if chords is not None:
            body.extend(place_chords(chords))
            chords = None

    def close():
        """End the open section before the blank lines that follow it."""
        nonlocal open_kind
        if open_kind:
            blanks = 0
            while body and not body[-1].strip():
                body.pop()
                blanks += 1
            body.append(f"{{end_of_{open_kind}}}")
            body.extend([""] * blanks)
            open_kind = None

    def open_section(kind: str, label: str = ""):
        nonlocal open_kind, open_at
        close()
        body.append(f"{{start_of_{kind}: {label}}}" if label else f"{{start_of_{kind}}}")
        open_kind, open_at = kind, len(body)

    label = ""
    for line in lines:
        stripped = line.strip()
        if found := section(line):
            flush()
            open_section(*found)
            label = found[1]
            continue
        if _TAB_LINE_RE.match(line):
            flush()
            if open_kind != "tab":
                if open_kind and not any(entry.strip() for entry in body[open_at:]):
                    # The tab is all the section holds: make it a tab section
                    del body[open_at - 1 :]
                    open_kind = None
                    open_section("tab", label)
                else:
                    open_section("tab")
            body.append(line.rstrip())
            continue
        if open_kind == "tab" and stripped:
            close()
        if (found_chords := chord_line(line)) is not None:
            flush()
            chords = found_chords
            continue
        if chords is not None and stripped and not stripped.startswith(("{", "(")):
            body.extend(place_chords(chords, line.rstrip()))
            chords = None
            continue
        flush()
        if stripped.startswith("(") and stripped.endswith(")"):
            body.append(f"{{comment: {stripped[1:-1].strip()}}}")
        else:
            body.append(line.rstrip())
    flush()
    close()

    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    return body
