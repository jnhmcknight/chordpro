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


class QuillDeltaRenderer(BaseRenderer):
    """Renders a ``Song`` to a `Quill Delta <https://quilljs.com/docs/delta/>`_
    ``dict`` (``{"ops": [...]}``).

    Chords are emitted with ``{"chord": True}`` so a custom Quill blot can
    style them independently from lyric text.  Section labels are bold.
    """

    def render(self, song: Song, semi_to_name: dict | None = None) -> dict:
        ops: list[dict] = []
        for item in song.body:
            if hasattr(item, "lines"):
                self._render_section(ops, item, semi_to_name)
            else:
                self._render_line(ops, item, semi_to_name)
        return {"ops": ops}

    def render_many(self, songs: list[Song], semi_to_name: dict | None = None) -> dict:
        """Render multiple *songs* into a single Quill Delta.

        Songs are separated by a newline op carrying ``{"page_break": True}``
        so a custom Quill blot can render them as page breaks.
        """
        ops: list[dict] = []
        for i, song in enumerate(songs):
            if i > 0:
                self._insert(ops, "\n", page_break=True)
            for item in song.body:
                if hasattr(item, "lines"):
                    self._render_section(ops, item, semi_to_name)
                else:
                    self._render_line(ops, item, semi_to_name)
        return {"ops": ops}

    def _insert(self, ops: list, text: str, **attrs) -> None:
        op: dict = {"insert": text}
        if attrs:
            op["attributes"] = {k: v for k, v in attrs.items() if v is not None}
        ops.append(op)

    def _render_section(self, ops: list, section, semi_to_name: dict | None) -> None:
        if section.label:
            self._insert(ops, section.label, bold=True)
            self._insert(ops, "\n")
        for line in section.lines:
            self._render_line(ops, line, semi_to_name)

    def _render_line(self, ops: list, line, semi_to_name: dict | None) -> None:
        if isinstance(line, ChordLine):
            for seg in line.segments:
                if seg.chord is not None:
                    chord = self._finalize_chord(
                        _convert_chord_root(seg.chord, semi_to_name)
                        if semi_to_name
                        else seg.chord
                    )
                    self._insert(ops, chord or " ", chord=True)
                if seg.lyric:
                    self._insert(ops, seg.lyric)
            self._insert(ops, "\n")
        elif isinstance(line, LyricLine):
            self._insert(ops, line.text)
            self._insert(ops, "\n")
        elif isinstance(line, BreakLine):
            self._insert(ops, "\n")
        elif isinstance(line, CommentLine):
            self._insert(ops, line.text, italic=True)
            self._insert(ops, "\n")
        elif isinstance(line, (CommentItalic, CommentBox)):
            self._insert(ops, line.text, italic=True)
            self._insert(ops, "\n")
        elif isinstance(line, Highlight):
            self._insert(ops, line.text, bold=True)
            self._insert(ops, "\n")
        elif isinstance(line, ChorusRef):
            self._insert(ops, f"[{line.label or 'Chorus'}]", italic=True)
            self._insert(ops, "\n")
        elif isinstance(line, NewPage):
            self._insert(ops, "\n", page_break=True)
