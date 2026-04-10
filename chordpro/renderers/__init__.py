"""
Multi-format renderer for a parsed ChordPro ``Song``.

Built-in formats
----------------
* ``"html"``        — ``markupsafe.Markup`` (default)
* ``"text"``        — plain ``str`` with chords above lyrics
* ``"quill-delta"`` — ``dict`` suitable for the Quill rich-text editor

Custom formats
--------------
Subclass ``BaseRenderer``, implement ``render()``, and register the class::

    from chordpro import BaseRenderer, register_renderer

    class PdfRenderer(BaseRenderer):
        def render(self, song, semi_to_name=None):
            ...  # return PDF bytes

    register_renderer("pdf", PdfRenderer)

The registered name is then usable in the ``chordpro`` Jinja2 filter::

    {{ song.content | chordpro("pdf") }}

Backward-compatibility shims ``render_html()`` and ``chordpro_to_html()``
are preserved unchanged.
"""

from __future__ import annotations

from typing import Any

try:
    from markupsafe import Markup
except ImportError:  # pragma: no cover
    Markup = str  # type: ignore[misc,assignment]

from ..models import Song
from ..parser import parse, transpose_song
from .base import BaseRenderer
from .html import HtmlRenderer
from .pdf import PdfRenderer
from .quill_delta import QuillDeltaRenderer
from .text import TextRenderer

__all__ = [
    "BaseRenderer",
    "HtmlRenderer",
    "TextRenderer",
    "QuillDeltaRenderer",
    "PdfRenderer",
    "render",
    "render_many",
    "register_renderer",
    # backward compat
    "render_html",
    "chordpro_to_html",
]

_REGISTRY: dict[str, type[BaseRenderer]] = {
    "html": HtmlRenderer,
    "text": TextRenderer,
    "quill-delta": QuillDeltaRenderer,
    "pdf": PdfRenderer,
}


def register_renderer(name: str, renderer_cls: type[BaseRenderer]) -> None:
    """Register *renderer_cls* under *name*.

    Once registered, *name* can be passed to ``render()`` or used as the
    *format* argument of the ``chordpro`` Jinja2 filter.

    Example::

        from chordpro import BaseRenderer, register_renderer

        class PdfRenderer(BaseRenderer):
            def render(self, song, semi_to_name=None):
                ...  # return PDF bytes

        register_renderer("pdf", PdfRenderer)
    """
    _REGISTRY[name] = renderer_cls


def render(
    song: Song,
    semi_to_name: dict | None = None,
    format: str = "html",
    ascii_accidentals: bool | None = None,
    key: str | None = None,
) -> Any:
    """Render *song* using the named *format*.

    Built-in formats: ``"html"``, ``"text"``, ``"quill-delta"``.
    Additional formats can be added with ``register_renderer()``.

    *ascii_accidentals* controls whether accidentals are output as ``#``/``b``
    (``True``) or the proper Unicode symbols ``♯``/``♭`` (``False``).  Pass
    ``None`` (the default) to use the renderer's own default — currently
    ``True`` for ``TextRenderer`` and ``False`` for all others.

    Raises ``ValueError`` for unknown format names.
    """
    if key is not None:
        song = transpose_song(song, key)
    try:
        renderer_cls = _REGISTRY[format]
    except KeyError:
        registered = ", ".join(f'"{k}"' for k in _REGISTRY)
        raise ValueError(
            f"Unknown format {format!r}. Registered formats: {registered}"
        ) from None
    return renderer_cls._make(ascii_accidentals).render(song, semi_to_name)


def render_many(
    songs: list[Song],
    semi_to_name: dict | None = None,
    format: str = "html",
    ascii_accidentals: bool | None = None,
    key: str | None = None,
) -> Any:
    """Render multiple *songs* as a single combined output using *format*.

    Songs are combined in order with format-appropriate separators:

    * ``"html"``        — each song wrapped in ``<div class="cp-song">``
    * ``"text"``        — songs joined by form-feed characters (``\\f``)
    * ``"quill-delta"`` — ops merged with ``{"page_break": True}`` between songs
    * ``"pdf"``         — each song starts on a new page

    Additional formats can be added with ``register_renderer()``.  Custom
    renderers that do not override ``render_many()`` receive a list of
    individual ``render()`` results.

    *ascii_accidentals* behaves as in ``render()``.

    Raises ``ValueError`` for unknown format names.
    """
    if key is not None:
        songs = [transpose_song(s, key) for s in songs]
    try:
        renderer_cls = _REGISTRY[format]
    except KeyError:
        registered = ", ".join(f'"{k}"' for k in _REGISTRY)
        raise ValueError(
            f"Unknown format {format!r}. Registered formats: {registered}"
        ) from None
    return renderer_cls._make(ascii_accidentals).render_many(songs, semi_to_name)


# ---------------------------------------------------------------------------
# Backward-compatibility shims
# ---------------------------------------------------------------------------


def render_html(song: Song, semi_to_name: dict | None = None) -> Markup:
    """Render *song* to ``Markup``. Kept for backward compatibility."""
    return HtmlRenderer().render(song, semi_to_name)


def chordpro_to_html(content: str, semi_to_name: dict | None = None) -> Markup:
    """Parse *content* and render to ``Markup`` in one step."""
    if not content:
        return Markup("")
    return render_html(parse(content), semi_to_name)
