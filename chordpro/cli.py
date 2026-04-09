"""
Command-line interface for chordpro.

Usage::

    chordpro <file.cho> [--format html|text|quill-delta] [--notation standard|german|latin|nashville] [--key C]
    cat file.cho | chordpro -
"""

from __future__ import annotations

import click

from .parser import (
    build_chord_semi_to_name,
    build_nashville_semi_to_name,
    key_to_semitone,
    parse,
)
from .renderers import render


@click.command()
@click.argument("file", default="-", metavar="FILE", type=click.Path(allow_dash=True))
@click.option(
    "--format",
    "-f",
    default="html",
    type=click.Choice(["html", "text", "quill-delta"]),
    help="Output format (default: html)",
)
@click.option(
    "--notation",
    "-n",
    default="standard",
    type=click.Choice(["standard", "german", "latin", "nashville"]),
    help="Chord notation (default: standard)",
)
@click.option(
    "--key",
    "-k",
    default=None,
    metavar="KEY",
    help="Root key for Nashville notation (e.g. C, G, Bb). Defaults to the song's own key.",
)
def convert(file: str, format: str, notation: str, key: str | None) -> None:
    """Convert a ChordPro file to HTML, plain text, or Quill Delta."""
    if file == "-":
        content = click.get_text_stream("stdin").read()
    else:
        with open(file, encoding="utf-8") as fh:
            content = fh.read()

    song = parse(content)

    if notation == "nashville":
        key_str = key or (song.meta.key[0] if song.meta.key else "C")
        semi_to_name = build_nashville_semi_to_name(key_to_semitone(key_str))
    else:
        semi_to_name = build_chord_semi_to_name(notation)

    result = render(song, semi_to_name, format=format)

    if isinstance(result, dict):
        import json

        click.echo(json.dumps(result, ensure_ascii=False))
    else:
        click.echo(str(result))


if __name__ == "__main__":
    convert()
