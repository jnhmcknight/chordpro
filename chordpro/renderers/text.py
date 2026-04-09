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
    """

    def render(self, song: Song, semi_to_name: dict | None = None) -> str:
        parts = []
        for item in song.body:
            if hasattr(item, "lines"):
                parts.append(self._render_section(item, semi_to_name))
            else:
                result = self._render_line(item, semi_to_name)
                if result is not None:
                    parts.append(result)
        return "\n".join(parts)

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
                    chord = (
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
