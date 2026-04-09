"""
chordpro
~~~~~~~~~~~~~~

A Flask extension that registers Jinja2 template filters for rendering
ChordPro-formatted song content, with multi-notation key support.

Usage::

    from flask import Flask
    from chordpro import ChordPro

    app = Flask(__name__)
    chordpro = ChordPro(app)

Or with the application factory pattern::

    chordpro = ChordPro()

    def create_app():
        app = Flask(__name__)
        chordpro.init_app(app)
        return app

The extension registers two Jinja2 template filters:

* ``chordpro``   — converts a ChordPro string to the requested format,
                   honouring ``flask.g.notation`` (``"standard"``,
                   ``"german"``, ``"latin"``).  The optional *format*
                   argument selects the output format (default ``"html"``);
                   built-in values are ``"html"``, ``"text"``, and
                   ``"quill-delta"``.  Pass a ``BaseRenderer`` instance for
                   a fully custom output type.

                   Examples::

                       {{ song.content | chordpro }}
                       {{ song.content | chordpro("text") }}
                       {{ song.content | chordpro("quill-delta") }}

* ``format_key`` — formats a key integer (0–23) as a human-readable key
                   name in the active notation.

Custom output formats
---------------------
Subclass ``BaseRenderer``, implement ``render()``, and register::

    from chordpro import BaseRenderer, register_renderer

    class PdfRenderer(BaseRenderer):
        def render(self, song, semi_to_name=None):
            ...  # return PDF bytes

    register_renderer("pdf", PdfRenderer)

Then use ``{{ song.content | chordpro("pdf") }}`` in templates, or call
``render(song, semi_to_name, format="pdf")`` directly in Python.
"""

from .extensions.flask import ChordPro
from .constants import KEY_NAMES
from .models import (
    # Content line types
    Segment,
    ChordLine,
    LyricLine,
    BreakLine,
    CommentLine,
    CommentItalic,
    CommentBox,
    Highlight,
    # Chord / transposition items
    ChordDefinition,
    ChordDiagram,
    Transpose,
    # Layout / flow-control items
    ChorusRef,
    Image,
    NewPage,
    NewPhysicalPage,
    ColumnBreak,
    Columns,
    GridOn,
    GridOff,
    NewSong,
    # Section types
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
    # Song
    SongMeta,
    Song,
)
from .parser import (
    build_chord_semi_to_name,
    build_nashville_semi_to_name,
    key_to_semitone,
    parse,
)
from .renderers import (
    BaseRenderer,
    HtmlRenderer,
    TextRenderer,
    QuillDeltaRenderer,
    PdfRenderer,
    render,
    register_renderer,
    render_html,
    chordpro_to_html,
)

__all__ = [
    # Extension
    "ChordPro",
    # Parser
    "parse",
    "build_chord_semi_to_name",
    "build_nashville_semi_to_name",
    "key_to_semitone",
    # Renderer
    "BaseRenderer",
    "HtmlRenderer",
    "TextRenderer",
    "QuillDeltaRenderer",
    "PdfRenderer",
    "render",
    "register_renderer",
    "render_html",
    "chordpro_to_html",
    # Content line types
    "Segment",
    "ChordLine",
    "LyricLine",
    "BreakLine",
    "CommentLine",
    "CommentItalic",
    "CommentBox",
    "Highlight",
    # Chord / transposition
    "ChordDefinition",
    "ChordDiagram",
    "Transpose",
    # Layout / flow-control
    "ChorusRef",
    "Image",
    "NewPage",
    "NewPhysicalPage",
    "ColumnBreak",
    "Columns",
    "GridOn",
    "GridOff",
    "NewSong",
    # Section types
    "Verse",
    "Chorus",
    "Bridge",
    "PreChorus",
    "Outro",
    "Intro",
    "Tab",
    "Grid",
    "Tag",
    "Interlude",
    "Solo",
    "Instrumental",
    "Abc",
    "Lilypond",
    "Svg",
    "TextBlock",
    "Section",
    # Song
    "SongMeta",
    "Song",
    # Constants
    "KEY_NAMES",
]
