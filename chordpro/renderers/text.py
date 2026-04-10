from __future__ import annotations

from ..models import (
    BreakLine,
    ChordLine,
    ChorusRef,
    CommentBox,
    CommentItalic,
    CommentLine,
    Highlight,
    LyricLine,
    NewPage,
    Song,
)
from ..parser import _convert_chord_root
from .base import BaseRenderer


class TextRenderer(BaseRenderer):
    """Renders a ``Song`` to a plain-text ``str``.

    Chord lines use the classic two-line layout: a chord row directly above
    the corresponding lyric row, columns aligned by segment width.

    Defaults to ASCII accidentals (``#`` / ``b``) for plain-text
    compatibility.  Pass ``ascii_accidentals=False`` to use Unicode symbols.
    """

    def __init__(self, ascii_accidentals: bool = True) -> None:
        super().__init__(ascii_accidentals=ascii_accidentals)

    def render(self, song: Song, semi_to_name: dict | None = None) -> str:
        sections = []
        header = self._render_header(song.meta)
        if header:
            sections.append(header)
        body_parts = []
        for item in song.body:
            if hasattr(item, "lines"):
                body_parts.append(self._render_section(item, semi_to_name))
            else:
                result = self._render_line(item, semi_to_name)
                if result is not None:
                    body_parts.append(result)
        if body_parts:
            sections.append("\n".join(body_parts))
        footer = self._render_footer(song.meta)
        if footer:
            sections.append(footer)
        return "\n\n".join(sections)

    def _render_header(self, meta) -> str:
        lines = []
        if meta.title:
            lines.append(meta.title)
        for sub in meta.subtitle:
            lines.append(sub)
        if meta.artist:
            lines.append(", ".join(meta.artist))
        if meta.album:
            lines.append("Album: " + ", ".join(meta.album))
        if meta.composer:
            lines.append("Composer: " + ", ".join(meta.composer))
        info_parts = []
        if meta.key:
            info_parts.append("Key: " + ", ".join(meta.key))
        if meta.time:
            info_parts.append("Time: " + ", ".join(meta.time))
        if meta.tempo:
            info_parts.append("Tempo: " + ", ".join(meta.tempo))
        if info_parts:
            lines.append("  |  ".join(info_parts))
        return "\n".join(lines)

    def _render_footer(self, meta) -> str:
        if not meta.copyright:
            return ""
        return "\n".join(meta.copyright)

    def render_many(self, songs: list[Song], semi_to_name: dict | None = None) -> str:
        """Render multiple *songs* separated by form-feed characters (``\\f``).

        A form-feed (``\\f``, ASCII 12) is the conventional page-break marker
        for plain-text output and is also used by ``{new_page}`` within a
        single song.
        """
        return "\f".join(self.render(song, semi_to_name) for song in songs)

    def _render_section(self, section, semi_to_name: dict | None) -> str:
        lines = []
        if section.label:
            lines.append(section.label)
        for line in section.lines:
            result = self._render_line(line, semi_to_name)
            if result is not None:
                lines.append(result)
        return "\n".join(lines)

    def _render_line(self, line, semi_to_name: dict | None) -> str | None:
        if isinstance(line, ChordLine):
            chord_row = ""
            lyric_row = ""
            for seg in line.segments:
                if seg.chord is not None:
                    chord = self._finalize_chord(
                        _convert_chord_root(seg.chord, semi_to_name)
                        if semi_to_name
                        else seg.chord
                    )
                    lyric = seg.lyric or ""
                    width = max(len(chord), len(lyric))
                    chord_row += chord.ljust(width) + " "
                    lyric_row += lyric.ljust(width) + " "
                elif seg.lyric:
                    chord_row += " " * len(seg.lyric)
                    lyric_row += seg.lyric
            result = ""
            if chord_row.strip():
                result += chord_row.rstrip() + "\n"
            result += lyric_row.rstrip()
            return result
        if isinstance(line, LyricLine):
            return line.text
        if isinstance(line, BreakLine):
            return ""
        if isinstance(line, (CommentLine, CommentItalic, CommentBox, Highlight)):
            return f"# {line.text}"
        if isinstance(line, ChorusRef):
            return f"[{line.label or 'Chorus'}]"
        if isinstance(line, NewPage):
            return "\f"
        return None
