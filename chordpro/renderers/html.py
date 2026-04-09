from __future__ import annotations

import html as _html

try:
    from markupsafe import Markup
except ImportError:  # pragma: no cover
    Markup = str  # type: ignore[misc,assignment]

from ..models import (
    BreakLine,
    ChordDiagram,
    ChordLine,
    ChorusRef,
    ColumnBreak,
    Columns,
    CommentBox,
    CommentItalic,
    CommentLine,
    GridOff,
    GridOn,
    Highlight,
    Image,
    LyricLine,
    NewPage,
    NewPhysicalPage,
    NewSong,
    Song,
    Transpose,
)
from ..parser import _convert_chord_root
from .base import BaseRenderer


class HtmlRenderer(BaseRenderer):
    """Renders a ``Song`` to ``markupsafe.Markup`` HTML."""

    def render(self, song: Song, semi_to_name: dict | None = None) -> Markup:
        parts = []
        for item in song.body:
            if hasattr(item, "lines"):
                parts.append(self._render_section(item, semi_to_name))
            else:
                rendered = self._render_line(item, semi_to_name)
                if rendered:
                    parts.append(rendered)
        return Markup("\n".join(parts))

    def render_many(
        self, songs: list[Song], semi_to_name: dict | None = None
    ) -> Markup:
        """Render multiple *songs* into a single HTML string.

        Each song is wrapped in ``<div class="cp-song">`` so they can be styled
        or targeted independently.
        """
        song_parts = []
        for song in songs:
            inner = []
            for item in song.body:
                if hasattr(item, "lines"):
                    inner.append(self._render_section(item, semi_to_name))
                else:
                    rendered = self._render_line(item, semi_to_name)
                    if rendered:
                        inner.append(rendered)
            song_parts.append('<div class="cp-song">\n' + "\n".join(inner) + "\n</div>")
        return Markup("\n".join(song_parts))

    def _chord_display(self, chord: str, semi_to_name: dict | None) -> tuple[str, str]:
        display = _convert_chord_root(chord, semi_to_name) if semi_to_name else chord
        chord_html = _html.escape(display) if display else "&nbsp;"
        data_attr = f' data-chord="{_html.escape(chord)}"' if chord else ""
        return chord_html, data_attr

    def _render_chord_line(
        self, chord_line: ChordLine, semi_to_name: dict | None
    ) -> str:
        buf = ['<div class="cp-line">']
        for seg in chord_line.segments:
            if seg.chord is not None:
                chord_html, data_attr = self._chord_display(seg.chord, semi_to_name)
                lyric_html = _html.escape(seg.lyric) if seg.lyric else "&nbsp;"
                buf.append(
                    f'<span class="cp-unit">'
                    f'<span class="cp-chord"{data_attr}>{chord_html}</span>'
                    f'<span class="cp-lyric">{lyric_html}</span>'
                    f"</span>"
                )
            elif seg.lyric:
                buf.append(
                    f'<span class="cp-lyric-only">{_html.escape(seg.lyric)}</span>'
                )
        buf.append("</div>")
        return "".join(buf)

    def _render_line(self, line, semi_to_name: dict | None) -> str:  # noqa: PLR0911
        if isinstance(line, ChordLine):
            return self._render_chord_line(line, semi_to_name)
        if isinstance(line, LyricLine):
            return f'<div class="cp-lyric-line">{_html.escape(line.text)}</div>'
        if isinstance(line, BreakLine):
            return '<div class="cp-break"></div>'
        if isinstance(line, CommentLine):
            return f'<div class="cp-comment">{_html.escape(line.text)}</div>'
        if isinstance(line, CommentItalic):
            return f'<div class="cp-comment cp-comment-italic">{_html.escape(line.text)}</div>'
        if isinstance(line, CommentBox):
            return f'<div class="cp-comment cp-comment-box">{_html.escape(line.text)}</div>'
        if isinstance(line, Highlight):
            return f'<div class="cp-highlight">{_html.escape(line.text)}</div>'
        if isinstance(line, ChorusRef):
            label_html = _html.escape(line.label) if line.label else ""
            inner = (
                f'<span class="cp-chorus-ref-label">{label_html}</span>'
                if label_html
                else ""
            )
            return f'<div class="cp-chorus-ref">{inner}</div>'
        if isinstance(line, Image):
            return f'<div class="cp-image" data-raw="{_html.escape(line.raw)}"></div>'
        if isinstance(line, ChordDiagram):
            return f'<div class="cp-chord-diagram" data-chord="{_html.escape(line.name)}"></div>'
        if isinstance(line, Transpose):
            value = str(line.semitones) if line.semitones is not None else ""
            return f'<span class="cp-transpose" data-semitones="{_html.escape(value)}" hidden></span>'
        if isinstance(line, NewPage):
            return '<div class="cp-new-page"></div>'
        if isinstance(line, NewPhysicalPage):
            return '<div class="cp-new-physical-page"></div>'
        if isinstance(line, ColumnBreak):
            return '<div class="cp-column-break"></div>'
        if isinstance(line, Columns):
            return f'<div class="cp-columns" data-count="{line.count}"></div>'
        if isinstance(line, GridOn):
            return '<span class="cp-grid-on" hidden></span>'
        if isinstance(line, GridOff):
            return '<span class="cp-grid-off" hidden></span>'
        if isinstance(line, NewSong):
            return '<hr class="cp-new-song">'
        # ChordDefinition has no visual rendering
        return ""

    def _render_section(self, section, semi_to_name: dict | None) -> str:
        parts = [
            f'<div class="cp-section" data-section="{_html.escape(section.kind)}">',
            f'<div class="cp-section-label">{_html.escape(section.label)}</div>',
        ]
        for line in section.lines:
            parts.append(self._render_line(line, semi_to_name))
        parts.append("</div>")
        return "\n".join(parts)
