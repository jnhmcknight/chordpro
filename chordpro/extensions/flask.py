import typing as t
import dataclasses

from flask import g
from flask.cli import AppGroup

from ..cli import convert
from ..constants import KEY_NAMES
from ..models import SongMeta
from ..parser import (
    build_chord_semi_to_name,
    build_nashville_semi_to_name,
    key_to_semitone,
    parse,
)
from ..renderers import BaseRenderer, render


def _supplement_meta(song_meta: SongMeta, supplement: SongMeta) -> None:
    """Fill empty fields on *song_meta* with values from *supplement* in-place."""
    for f in dataclasses.fields(SongMeta):
        parsed_val = getattr(song_meta, f.name)
        supp_val = getattr(supplement, f.name)
        if f.name == "meta":
            # dict: copy only keys absent in the parsed meta
            for k, v in supp_val.items():
                parsed_val.setdefault(k, v)
        elif isinstance(parsed_val, list):
            if not parsed_val and supp_val:
                setattr(song_meta, f.name, supp_val)
        else:
            if parsed_val is None and supp_val is not None:
                setattr(song_meta, f.name, supp_val)


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
        def _chordpro_filter(
            content: str,
            format: t.Literal["html", "text", "pdf", "quill-delta"] = "html",
            meta: t.Optional[SongMeta] = None,
        ):
            if not content:
                return ""
            notation = getattr(g, "notation", "standard")
            song = parse(content)
            if meta is not None:
                _supplement_meta(song.meta, meta)
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
        def _format_key_filter(key):
            if key is None:
                return ""
            notation = getattr(g, "notation", "standard")
            # String key path (new model)
            if isinstance(key, str):
                if notation == "standard":
                    return key
                # Convert from standard string to the requested notation
                std_table = KEY_NAMES["standard"]
                target_table = KEY_NAMES.get(notation, KEY_NAMES["standard"])
                is_minor = key.endswith("m")
                side = "minor" if is_minor else "major"
                for idx, name in std_table[side].items():
                    if name == key:
                        return target_table[side][idx]
                return key  # unrecognised — return as-is
            # Legacy integer key path (kept for backward compatibility)
            try:
                table = KEY_NAMES.get(notation, KEY_NAMES["standard"])
                if key >= 12:
                    return table["minor"][key - 12]
                return table["major"][key]
            except (KeyError, TypeError):
                return str(key)

        self.cli = AppGroup("chordpro", help="ChordPro related tools")
        self.cli.add_command(convert)
        app.cli.add_command(self.cli)
