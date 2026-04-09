from flask import g
from flask.cli import AppGroup

from ..cli import convert
from ..constants import KEY_NAMES
from ..parser import (
    build_chord_semi_to_name,
    build_nashville_semi_to_name,
    key_to_semitone,
    parse,
)
from ..renderers import BaseRenderer, render


class ChordPro:
    """Flask extension for ChordPro template filters."""

    cli: AppGroup = None  # type: ignore

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.extensions["chordpro"] = self

        @app.template_filter("chordpro")
        def _chordpro_filter(content, format="html"):
            if not content:
                return ""
            notation = getattr(g, "notation", "standard")
            song = parse(content)
            if notation == "nashville":
                key_str = getattr(g, "key", None) or (
                    song.meta.key[0] if song.meta.key else "C"
                )
                semi_to_name = build_nashville_semi_to_name(key_to_semitone(key_str))
            else:
                semi_to_name = build_chord_semi_to_name(notation)
            if isinstance(format, BaseRenderer):
                return format.render(song, semi_to_name)
            return render(song, semi_to_name, format=format)

        @app.template_filter("format_key")
        def _format_key_filter(key_int):
            try:
                notation = getattr(g, "notation", "standard")
                table = KEY_NAMES.get(notation, KEY_NAMES["standard"])
                if key_int >= 12:
                    return table["minor"][key_int - 12]
                return table["major"][key_int]
            except (KeyError, TypeError):
                return str(key_int)

        self.cli = AppGroup("chordpro", help="ChordPro related tools")
        self.cli.add_command(convert)
        app.cli.add_command(self.cli)
