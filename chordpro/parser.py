"""
ChordPro string parser and chord-notation helpers.

``parse(content)`` converts a raw ChordPro string into a ``Song`` tree.
The chord-notation utilities (``build_chord_semi_to_name``, etc.) are kept
here because they are conceptually part of chord parsing, even though they
are also used at render time.
"""

import re

from .constants import (
    KEY_NAMES,
    _CP_SECTION_LABELS,
    _NASHVILLE_CHROMATIC,
    _SHORT_FORM_DIRECTIVES,
    _STANDARD_NOTE_TO_SEMI,
)
from .models import (
    Abc,
    BreakLine,
    Bridge,
    ChordDefinition,
    ChordDiagram,
    ChordLine,
    Chorus,
    ChorusRef,
    ColumnBreak,
    Columns,
    CommentBox,
    CommentItalic,
    CommentLine,
    Grid,
    GridOff,
    GridOn,
    Highlight,
    Image,
    Instrumental,
    Interlude,
    Intro,
    Lilypond,
    LyricLine,
    NewPage,
    NewPhysicalPage,
    NewSong,
    Outro,
    PreChorus,
    Section,
    Segment,
    Solo,
    Song,
    SongMeta,
    Svg,
    Tab,
    Tag,
    TextBlock,
    Transpose,
    Verse,
)

__all__ = [
    "parse",
    "build_chord_semi_to_name",
    "build_nashville_semi_to_name",
    "key_to_semitone",
]

_SECTION_MAP = {
    "verse": Verse,
    "chorus": Chorus,
    "bridge": Bridge,
    "prechorus": PreChorus,
    "pre_chorus": PreChorus,
    "outro": Outro,
    "intro": Intro,
    "tab": Tab,
    "grid": Grid,
    "tag": Tag,
    "interlude": Interlude,
    "solo": Solo,
    "instrumental": Instrumental,
    "abc": Abc,
    "ly": Lilypond,
    "svg": Svg,
    "textblock": TextBlock,
}

# Metadata directives whose value is stored in a single str | None field.
_META_SINGLE: frozenset[str] = frozenset({"title", "year", "duration", "capo"})

# Metadata directives whose value is appended to a list[str] field.
_META_LIST: frozenset[str] = frozenset(
    {
        "subtitle",
        "sorttitle",
        "artist",
        "sortartist",
        "album",
        "composer",
        "lyricist",
        "copyright",
        "key",
        "time",
        "tempo",
    }
)


def build_chord_semi_to_name(notation: str) -> dict[int, str]:
    """Return a dict mapping chromatic semitone → chord root name.

    Falls back to ``"standard"`` for unknown notations.
    """
    table = KEY_NAMES.get(notation, KEY_NAMES["standard"])["major"]
    return {(key_int + 9) % 12: name for key_int, name in table.items()}


def key_to_semitone(key: str) -> int:
    """Return the chromatic semitone (C=0 … B=11) of the root note in *key*.

    Handles major and minor key strings: ``"G"``, ``"Bb"``, ``"Am"``,
    ``"F#m"``, etc.  Unrecognised strings default to C (0).
    """
    # Strip trailing minor marker so "Am" → "A", "F#m" → "F#"
    root = key.strip().rstrip("m")
    return _STANDARD_NOTE_TO_SEMI.get(root, 0)


def build_nashville_semi_to_name(key_semitone: int) -> dict[int, str]:
    """Return a semitone → Nashville number map for the given key tonic.

    ``key_semitone`` is the chromatic semitone of the key root (C=0 … B=11),
    typically obtained from ``key_to_semitone()``.

    The returned dict covers all 12 chromatic semitones.  Diatonic scale
    degrees are the plain numbers 1–7; chromatic semitones use flat/sharp
    prefixes following standard Nashville Number System convention.
    """
    return {
        (key_semitone + offset) % 12: number
        for offset, number in _NASHVILLE_CHROMATIC.items()
    }


def _convert_chord_root(chord: str, semi_to_name: dict[int, str]) -> str:
    """Translate the root note of *chord* into the target notation."""
    m = re.match(r"^([A-G][#b]?)(.*)", chord, re.DOTALL)
    if not m:
        return chord
    root, rest = m.group(1), m.group(2)
    semi = _STANDARD_NOTE_TO_SEMI.get(root)
    if semi is None:
        return chord
    return semi_to_name.get(semi, root) + rest


def _parse_chord_line(line: str) -> ChordLine:
    parts = re.split(r"(\[[^\]]*\])", line)
    segments: list[Segment] = []
    current_chord: str | None = None
    for part in parts:
        if re.match(r"^\[[^\]]*\]$", part):
            current_chord = part[1:-1]
        else:
            segments.append(Segment(chord=current_chord, lyric=part))
            current_chord = None
    if current_chord is not None:
        segments.append(Segment(chord=current_chord, lyric=""))
    return ChordLine(segments=segments)


def _make_section(kind: str, label: str):
    cls = _SECTION_MAP.get(kind)
    if cls is not None:
        return cls(label=label)
    return Section(kind=kind, label=label)


def _apply_meta(song_meta: SongMeta, directive: str, value: str) -> bool:
    """Try to apply *directive* as a metadata update.

    Returns ``True`` if the directive was consumed as metadata, ``False`` if
    the caller should treat it as a body item instead.
    """
    if directive in _META_SINGLE:
        setattr(song_meta, directive, value or None)
        return True

    if directive in _META_LIST:
        getattr(song_meta, directive).append(value)
        return True

    if directive == "tag":
        # {tag: value} is a metadata categorisation tag (not a section)
        song_meta.meta.setdefault("tag", []).append(value)
        return True

    if directive == "meta":
        # {meta: name value}  —  name is a single word
        parts = value.split(None, 1)
        if len(parts) == 2:
            name, val = parts
            song_meta.meta.setdefault(name, []).append(val)
        elif len(parts) == 1:
            song_meta.meta.setdefault(parts[0], [])
        return True

    return False


def _directive_to_item(directive: str, value: str):
    """Convert a non-metadata, non-section directive to a body/line item.

    Returns the item, or ``None`` if the directive is silently ignored.
    """
    if directive in ("comment", "c"):
        return CommentLine(text=value)
    if directive == "comment_italic":
        return CommentItalic(text=value)
    if directive == "comment_box":
        return CommentBox(text=value)
    if directive == "highlight":
        return Highlight(text=value)
    if directive == "chorus":
        return ChorusRef(label=value or None)
    if directive == "image":
        return Image(raw=value)
    if directive == "define":
        parts = value.split(None, 1)
        name = parts[0] if parts else value
        return ChordDefinition(name=name, raw=value)
    if directive == "chord":
        return ChordDiagram(name=value)
    if directive == "transpose":
        try:
            semitones = int(value) if value else None
        except ValueError:
            semitones = None
        return Transpose(semitones=semitones)
    if directive == "new_page":
        return NewPage()
    if directive == "new_physical_page":
        return NewPhysicalPage()
    if directive == "column_break":
        return ColumnBreak()
    if directive == "columns":
        try:
            count = int(value)
        except (ValueError, TypeError):
            count = 1
        return Columns(count=count)
    if directive == "grid":
        return GridOn()
    if directive == "no_grid":
        return GridOff()
    if directive == "new_song":
        return NewSong()
    return None  # silently ignore all other directives


def parse(content: str) -> Song:
    """Parse a ChordPro string and return a ``Song`` object."""
    if not content:
        return Song()

    song_meta = SongMeta()
    body: list = []
    current_section = None

    for raw_line in content.split("\n"):
        line = raw_line.rstrip("\r")

        directive_match = re.match(r"^\{([\w-]+)(?::\s*(.*?))?\s*\}$", line.strip())
        if directive_match:
            directive = directive_match.group(1).lower().replace("-", "_")
            directive = _SHORT_FORM_DIRECTIVES.get(directive, directive)
            value = directive_match.group(2) or ""

            if directive.startswith("start_of_"):
                kind = directive[9:]
                label = str(
                    _CP_SECTION_LABELS.get(kind, kind.replace("_", " ").title())
                )
                if value:
                    label = value
                if current_section is not None:
                    body.append(current_section)
                current_section = _make_section(kind, label)

            elif directive.startswith("end_of_"):
                if current_section is not None:
                    body.append(current_section)
                    current_section = None

            elif _apply_meta(song_meta, directive, value):
                pass  # metadata consumed; no body item produced

            else:
                item = _directive_to_item(directive, value)
                if item is not None:
                    if current_section is not None:
                        current_section.lines.append(item)
                    else:
                        body.append(item)

            continue

        if "[" in line:
            item = _parse_chord_line(line)
        elif line.strip():
            item = LyricLine(text=line)
        else:
            item = BreakLine()

        if current_section is not None:
            current_section.lines.append(item)
        else:
            body.append(item)

    if current_section is not None:
        body.append(current_section)

    return Song(meta=song_meta, body=body)
