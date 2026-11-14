"""
ChordPro string parser and chord-notation helpers.

``parse(content)`` converts a raw ChordPro string into a ``Song`` tree.
The chord-notation utilities (``build_chord_semi_to_name``, etc.) are kept
here because they are conceptually part of chord parsing, even though they
are also used at render time.
"""

import dataclasses
import re

from .constants import (
    FLAT,
    KEY_NAMES,
    SHARP,
    _CP_SECTION_LABELS,
    _FLAT_PREFERENCE_KEYS,
    _FLAT_SEMI_TO_NAME,
    _NASHVILLE_CHROMATIC,
    _SHARP_SEMI_TO_NAME,
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
    "build_transposed_semi_to_name",
    "build_key_semi_to_name",
    "format_key",
    "key_to_semitone",
    "shift_key",
    "song_parts",
    "transpose_parts",
    "transpose_song",
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


def build_chord_semi_to_name(
    notation: str, prefer_flats: bool = False
) -> dict[int, str]:
    """Return a dict mapping chromatic semitone → chord root name.

    Falls back to ``"standard"`` for unknown notations.

    For ``"standard"`` notation, *prefer_flats* selects flat accidentals
    (D♭, E♭, G♭, A♭, B♭) over sharp ones (C♯, D♯, F♯, G♯, A♯) for
    chromatic (non-diatonic) semitones.  Use ``_key_prefers_flats()`` to
    derive the right value from a key string.
    """
    if notation == "standard" or notation not in KEY_NAMES:
        return dict(_FLAT_SEMI_TO_NAME if prefer_flats else _SHARP_SEMI_TO_NAME)
    table = KEY_NAMES[notation]["major"]
    return {(key_int + 9) % 12: name for key_int, name in table.items()}


def _key_prefers_flats(key: str) -> bool:
    """Return ``True`` when *key* conventionally uses flat accidentals."""
    return _normalize_accidental(key.strip()) in _FLAT_PREFERENCE_KEYS


def key_to_semitone(key: str) -> int:
    """Return the chromatic semitone (C=0 … B=11) of the root note in *key*.

    Handles major and minor key strings: ``"G"``, ``"Bb"``, ``"Am"``,
    ``"F#m"``, etc.  Unrecognised strings default to C (0).
    """
    # Strip trailing minor marker so "Am" → "A", "F#m" → "F#"
    root = key.strip().rstrip("m")
    return _STANDARD_NOTE_TO_SEMI.get(_normalize_accidental(root), 0)


def build_transposed_semi_to_name(
    shift: int, notation: str = "standard"
) -> dict[int, str]:
    """Return a semitone→chord-root dict that transposes by *shift* semitones.

    The returned dict is suitable as the *semi_to_name* argument of any
    renderer's ``render()`` method.  Combine with ``key_to_semitone()`` to
    shift from a known source key to a target key::

        shift = (key_to_semitone("G") - key_to_semitone("C")) % 12
        semi_to_name = build_transposed_semi_to_name(shift)
    """
    base = build_chord_semi_to_name(notation)
    return {s: base[(s + shift) % 12] for s in range(12)}


def transpose_song(song: Song, target_key: str) -> Song:
    """Return a new ``Song`` with all chords transposed to *target_key*.

    The source key is taken from ``song.meta.key[0]``; if the song has no key
    metadata, C major is assumed.  The returned song's ``meta.key`` is set to
    ``[target_key]``.  A section played in a key of its own (see
    ``transpose_parts``) moves with the song: its ``key`` is shifted by the
    same interval, and its chords are spelled for its new key.

    Chord roots in the copy use standard chromatic note names so any renderer
    can process them without further configuration.  Pass an additional
    *semi_to_name* dict to the renderer if you also want notation conversion
    (Nashville numbers, German notation, etc.) applied on top.
    """
    source_key = song.meta.key[0] if song.meta.key else "C"
    shift = (key_to_semitone(target_key) - key_to_semitone(source_key)) % 12

    new_meta = dataclasses.replace(song.meta, key=[target_key])

    if shift == 0:
        return dataclasses.replace(song, meta=new_meta)

    shifted_map = _shifted_map(shift, target_key)

    new_body = []
    for item in song.body:
        item_lines = getattr(item, "lines", None)
        if item_lines is None:
            new_body.append(_transpose_line(item, shifted_map))
        elif getattr(item, "key", None):
            new_body.append(
                _transpose_section(item, item.key, shift_key(item.key, shift))
            )
        else:
            new_body.append(
                dataclasses.replace(
                    item,
                    lines=[_transpose_line(line, shifted_map) for line in item_lines],
                )
            )

    return dataclasses.replace(song, meta=new_meta, body=new_body)


def _shifted_map(shift: int, target_key: str) -> dict[int, str]:
    """A semitone → standard root name map that moves each note *shift*
    semitones up, spelled with the accidentals *target_key* prefers."""
    std_map = build_chord_semi_to_name(
        "standard", prefer_flats=_key_prefers_flats(target_key)
    )
    return {s: std_map[(s + shift) % 12] for s in range(12)}


def _transpose_line(line, shifted_map: dict[int, str]):
    """*line* with its chords mapped through *shifted_map* (see ``_shifted_map``);
    anything but a ``ChordLine`` is returned as it is."""
    if not isinstance(line, ChordLine):
        return line
    return ChordLine(
        segments=[
            Segment(
                chord=(
                    _convert_chord_root(seg.chord, shifted_map)
                    if seg.chord is not None
                    else None
                ),
                lyric=seg.lyric,
            )
            for seg in line.segments
        ]
    )


def _transpose_section(section, from_key: str, to_key: str):
    """A copy of *section*, written in *from_key*, played in *to_key*: its
    chords transposed and spelled for it, and its ``key`` set to it."""
    shift = (key_to_semitone(to_key) - key_to_semitone(from_key)) % 12
    shifted_map = _shifted_map(shift, to_key)
    return dataclasses.replace(
        section,
        lines=[_transpose_line(line, shifted_map) for line in section.lines],
        key=to_key,
    )


def shift_key(key: str, semitones: int) -> str:
    """The key *semitones* above *key*, major or minor as it is, named as
    ``KEY_NAMES["standard"]`` names keys (``shift_key("G", 2)`` → ``"A"``,
    ``shift_key("Am", 1)`` → ``"B♭m"``)."""
    minor = key.strip().endswith("m")
    root = (key_to_semitone(key) + semitones) % 12
    # KEY_NAMES is indexed from A, and lists each minor key at its relative
    # major (3 semitones up)
    index = (root + (3 if minor else 0) - 9) % 12
    return KEY_NAMES["standard"]["minor" if minor else "major"][index]


# Sections that hold no chords to play: they are never parts of a song
_NOT_PARTS: frozenset[str] = frozenset({"abc", "ly", "svg", "textblock"})


def _is_part(item) -> bool:
    if isinstance(item, ChorusRef):
        return True
    return (
        hasattr(item, "kind") and hasattr(item, "lines") and item.kind not in _NOT_PARTS
    )


def song_parts(song: Song) -> list:
    """The parts of *song* that can be played in a key of their own, in
    order: its sections (but ABC, Lilypond, SVG and text blocks) and its
    ``{chorus}`` references.  Lines outside any section aren't parts.

    A part's index in this list is how ``transpose_parts`` names it.
    """
    return [item for item in song.body if _is_part(item)]


def transpose_parts(song: Song, keys: dict[int, str]) -> Song:
    """Return a new ``Song`` in which each part (see ``song_parts``) whose
    index is in *keys* is played in the key given for it.

    The part's chords are transposed from the key it was in (its own, or
    else the song's, or C) to its new key, spelled for it, and its ``key``
    is set to it, for renderers to show.  A ``{chorus}`` reference given a
    key is written out in full, as a copy of the last chorus before it (with
    the reference's label, if it has one), since a bare reference shows no
    chords to play; one with no chorus before it is left as it is.  Indexes
    the song has no part for are ignored.
    """
    song_key = song.meta.key[0] if song.meta.key else "C"
    body = []
    index = -1
    last_chorus = None
    for item in song.body:
        if isinstance(item, Chorus):
            last_chorus = item
        if not _is_part(item):
            body.append(item)
            continue
        index += 1
        key = keys.get(index)
        if key is None:
            body.append(item)
            continue
        if isinstance(item, ChorusRef):
            if last_chorus is None:
                body.append(item)
                continue
            item = dataclasses.replace(
                last_chorus, label=item.label or last_chorus.label
            )
        body.append(_transpose_section(item, item.key or song_key, key))
    return dataclasses.replace(song, body=body)


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


def build_key_semi_to_name(notation: str, key: str | None) -> dict[int, str]:
    """Return the semitone → chord-name map for chords in *key*, in *notation*.

    In Nashville notation, numbers from the key's root (C when there is no
    key); in standard notation, the flats or sharps the key prefers; in the
    other notations, their own names.  Renderers given a ``notation`` build
    each song's and each keyed section's names with this.
    """
    if notation == "nashville":
        return build_nashville_semi_to_name(key_to_semitone(key or "C"))
    prefer_flats = _key_prefers_flats(key) if key else False
    return build_chord_semi_to_name(notation, prefer_flats=prefer_flats)


def format_key(key: str, notation: str = "standard") -> str:
    """Return *key* (a standard key name, ``"B♭"``, ``"F♯m"``) as *notation*
    names it.  Nashville notation, which has no names for keys, and unknown
    notations or keys give the key as it is."""
    if notation == "standard" or notation not in KEY_NAMES:
        return key
    side = "minor" if key.endswith("m") else "major"
    for index, name in KEY_NAMES["standard"][side].items():
        if name == key:
            return KEY_NAMES[notation][side][index]
    return key


def _normalize_accidental(root: str) -> str:
    """Normalize ASCII accidentals to proper symbols (e.g. ``C#`` → ``C♯``)."""
    return root.replace("#", SHARP).replace("b", FLAT)


_NOTE_RE = re.compile(r"[A-G][#b♯♭]?")


def _convert_note(note: str, semi_to_name: dict[int, str]) -> str | None:
    """Map a single note name through *semi_to_name*.

    Returns ``None`` when *note* is not a recognised note name.
    """
    normalized = _normalize_accidental(note)
    semi = _STANDARD_NOTE_TO_SEMI.get(normalized)
    if semi is None:
        return None
    return semi_to_name.get(semi, normalized)


def _convert_chord_root(chord: str, semi_to_name: dict[int, str]) -> str:
    """Translate the root note (and slash-bass note) of *chord* into the
    target notation.

    For slash chords such as ``G/B`` the bass note after the final ``/`` is
    converted too, but only when it is a bare note name — so extensions like
    ``C6/9`` are left untouched.
    """
    m = _NOTE_RE.match(chord)
    if not m:
        return chord
    root = _convert_note(m.group(0), semi_to_name)
    if root is None:
        return chord
    rest = chord[m.end() :]

    head, slash, bass = rest.rpartition("/")
    if slash and _NOTE_RE.fullmatch(bass):
        new_bass = _convert_note(bass, semi_to_name)
        if new_bass is not None:
            rest = head + slash + new_bass

    return root + rest


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
