"""
Data model for a parsed ChordPro document.

A ``Song`` carries two kinds of data:

* **Metadata** — song-level fields (title, artist, key, …) populated by
  metadata directives such as ``{title: …}`` and ``{meta: name value}``.
* **Body** — a flat list of ``SongItem`` objects representing the rendered
  content in document order: sections, content lines, and layout/control
  items.

Sections (``Verse``, ``Chorus``, …) each carry a ``lines`` list of their
own content items.  Chord roots in ``Segment`` objects are always stored in
standard notation; notation conversion happens at render time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union

# ---------------------------------------------------------------------------
# Content line types
# ---------------------------------------------------------------------------


@dataclass
class Segment:
    """A single chord+lyric unit within a ``ChordLine``.

    ``chord`` is ``None`` for spans that carry only lyrics (no chord above).
    Chord roots are always stored in standard notation.
    """

    chord: str | None
    lyric: str


@dataclass
class ChordLine:
    """A line that contains at least one chord annotation."""

    segments: list[Segment] = field(default_factory=list)


@dataclass
class LyricLine:
    """A plain lyric line with no chords."""

    text: str


@dataclass
class BreakLine:
    """An empty line, rendered as a paragraph break."""


@dataclass
class CommentLine:
    """A ``{comment: …}`` or ``{c: …}`` directive."""

    text: str


@dataclass
class CommentItalic:
    """A ``{comment_italic: …}`` / ``{ci: …}`` directive (italic comment)."""

    text: str


@dataclass
class CommentBox:
    """A ``{comment_box: …}`` directive (legacy boxed comment)."""

    text: str


@dataclass
class Highlight:
    """A ``{highlight: …}`` directive."""

    text: str


# ---------------------------------------------------------------------------
# Chord / transposition items
# ---------------------------------------------------------------------------


@dataclass
class ChordDefinition:
    """A ``{define: …}`` directive that defines a custom chord fingering."""

    name: str
    raw: str  # the full value string as given in the directive


@dataclass
class ChordDiagram:
    """A ``{chord: name}`` directive that displays a chord diagram inline."""

    name: str


@dataclass
class Transpose:
    """A ``{transpose: N}`` directive.

    ``semitones`` is the signed integer offset to apply to subsequent chords.
    ``None`` means the transpose is being cancelled (bare ``{transpose}``).
    """

    semitones: int | None


# ---------------------------------------------------------------------------
# Layout / flow-control items
# ---------------------------------------------------------------------------


@dataclass
class ChorusRef:
    """A standalone ``{chorus}`` directive that references the last chorus.

    ``label`` is the optional label provided (e.g. ``{chorus: Chorus 2}``).
    """

    label: str | None = None


@dataclass
class Image:
    """An ``{image: …}`` directive.

    ``raw`` contains the full value string (e.g. ``"src=photo.png width=50%"``).
    """

    raw: str


@dataclass
class NewPage:
    """A ``{new_page}`` / ``{np}`` directive — forces a page break."""


@dataclass
class NewPhysicalPage:
    """A ``{new_physical_page}`` / ``{npp}`` directive."""


@dataclass
class ColumnBreak:
    """A ``{column_break}`` / ``{cb}`` directive."""


@dataclass
class Columns:
    """A ``{columns: N}`` / ``{col: N}`` directive."""

    count: int


@dataclass
class GridOn:
    """A ``{grid}`` / ``{g}`` directive — enables chord-grid display."""


@dataclass
class GridOff:
    """A ``{no_grid}`` / ``{ng}`` directive — disables chord-grid display."""


@dataclass
class NewSong:
    """A ``{new_song}`` / ``{ns}`` directive — marks the start of a new song
    in a multi-song document."""


# Anything that can appear as a line inside a section or at the top level.
Line = Union[
    ChordLine,
    LyricLine,
    BreakLine,
    CommentLine,
    CommentItalic,
    CommentBox,
    Highlight,
    ChordDefinition,
    ChordDiagram,
    Transpose,
    ChorusRef,
    Image,
    NewPage,
    NewPhysicalPage,
    ColumnBreak,
    Columns,
    GridOn,
    GridOff,
    NewSong,
]


# ---------------------------------------------------------------------------
# Section types
# ---------------------------------------------------------------------------
# Each named section has a read-only ``kind`` property that matches the
# canonical ChordPro directive suffix.  The generic ``Section`` class covers
# any unrecognised ``{start_of_*}`` directive and stores ``kind`` as a plain
# instance field.


@dataclass
class Verse:
    label: str
    lines: list[Line] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return "verse"


@dataclass
class Chorus:
    label: str
    lines: list[Line] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return "chorus"


@dataclass
class Bridge:
    label: str
    lines: list[Line] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return "bridge"


@dataclass
class PreChorus:
    label: str
    lines: list[Line] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return "prechorus"


@dataclass
class Outro:
    label: str
    lines: list[Line] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return "outro"


@dataclass
class Intro:
    label: str
    lines: list[Line] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return "intro"


@dataclass
class Tab:
    label: str
    lines: list[Line] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return "tab"


@dataclass
class Grid:
    label: str
    lines: list[Line] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return "grid"


@dataclass
class Tag:
    label: str
    lines: list[Line] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return "tag"


@dataclass
class Interlude:
    label: str
    lines: list[Line] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return "interlude"


@dataclass
class Solo:
    label: str
    lines: list[Line] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return "solo"


@dataclass
class Instrumental:
    label: str
    lines: list[Line] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return "instrumental"


@dataclass
class Abc:
    """An ``{start_of_abc}`` / ``{end_of_abc}`` section (ABC notation)."""

    label: str
    lines: list[Line] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return "abc"


@dataclass
class Lilypond:
    """A ``{start_of_ly}`` / ``{end_of_ly}`` section (Lilypond notation)."""

    label: str
    lines: list[Line] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return "ly"


@dataclass
class Svg:
    """A ``{start_of_svg}`` / ``{end_of_svg}`` section (inline SVG)."""

    label: str
    lines: list[Line] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return "svg"


@dataclass
class TextBlock:
    """A ``{start_of_textblock}`` / ``{end_of_textblock}`` section."""

    label: str
    lines: list[Line] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return "textblock"


@dataclass
class Section:
    """Generic section for unrecognised ``{start_of_*}`` directives."""

    kind: str
    label: str
    lines: list[Line] = field(default_factory=list)


SongSection = Union[
    Verse,
    Chorus,
    Bridge,
    PreChorus,
    Outro,
    Intro,
    Tab,
    Grid,
    Tag,
    Interlude,
    Solo,
    Instrumental,
    Abc,
    Lilypond,
    Svg,
    TextBlock,
    Section,
]

SongItem = Union[SongSection, Line]


# ---------------------------------------------------------------------------
# Song metadata
# ---------------------------------------------------------------------------


@dataclass
class SongMeta:
    """Song-level metadata populated by metadata directives.

    Fields that the spec allows to appear multiple times (subtitle, artist,
    key, …) are lists.  Fields that are logically singular are ``str | None``.

    The ``meta`` dict captures any ``{meta: name value}`` directive whose
    name does not map to a known field, as well as ``{tag: …}`` values.
    """

    title: str | None = None
    sorttitle: list[str] = field(default_factory=list)
    subtitle: list[str] = field(default_factory=list)
    artist: list[str] = field(default_factory=list)
    sortartist: list[str] = field(default_factory=list)
    album: list[str] = field(default_factory=list)
    composer: list[str] = field(default_factory=list)
    lyricist: list[str] = field(default_factory=list)
    copyright: list[str] = field(default_factory=list)
    year: str | None = None
    key: list[str] = field(default_factory=list)
    time: list[str] = field(default_factory=list)
    tempo: list[str] = field(default_factory=list)
    duration: str | None = None
    capo: str | None = None
    meta: dict[str, list[str]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Song
# ---------------------------------------------------------------------------


@dataclass
class Song:
    """A fully parsed ChordPro document."""

    meta: SongMeta = field(default_factory=SongMeta)
    body: list[SongItem] = field(default_factory=list)
