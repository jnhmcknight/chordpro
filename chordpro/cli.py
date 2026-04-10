"""
Command-line interface for chordpro.

Usage::

    chordpro <file.cho> [--format html|text|quill-delta|pdf] [--notation standard|german|latin|nashville] [--key C]
    chordpro song1.cho song2.cho --format pdf   # multi-song PDF
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
from .renderers import render, render_many


@click.command()
@click.argument("files", nargs=-1, metavar="FILE...", type=click.Path(allow_dash=True))
@click.option(
    "--format",
    "-f",
    default="html",
    type=click.Choice(["html", "text", "quill-delta", "pdf"]),
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
@click.option(
    "--ascii-accidentals/--unicode-accidentals",
    default=None,
    help=(
        "Use ASCII # and b for accidentals (--ascii-accidentals) or proper Unicode "
        "♯ and ♭ symbols (--unicode-accidentals). "
        "Defaults to ASCII for text output and Unicode for all other formats."
    ),
)
def convert(
    files: tuple[str, ...],
    format: str,
    notation: str,
    key: str | None,
    ascii_accidentals: bool | None,
) -> None:
    """Convert one or more ChordPro files to the selected output format.

    Pass multiple FILE arguments to combine songs into a single output.
    For PDF, each song will start on its own page.  Use ``-`` to read from
    stdin.
    """
    if not files:
        files = ("-",)

    songs = []
    for path in files:
        if path == "-":
            content = click.get_text_stream("stdin").read()
        else:
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
        songs.append(parse(content))

    if notation == "nashville":
        # For multi-song Nashville, use --key if given, else first song's key.
        key_str = key or (songs[0].meta.key[0] if songs[0].meta.key else "C")
        semi_to_name = build_nashville_semi_to_name(key_to_semitone(key_str))
    else:
        semi_to_name = build_chord_semi_to_name(notation)

    if len(songs) == 1:
        result = render(songs[0], semi_to_name, format=format, ascii_accidentals=ascii_accidentals)
    else:
        result = render_many(songs, semi_to_name, format=format, ascii_accidentals=ascii_accidentals)

    if isinstance(result, bytes):
        import sys

        sys.stdout.buffer.write(result)
    elif isinstance(result, dict):
        import json

        click.echo(json.dumps(result, ensure_ascii=False))
    else:
        click.echo(str(result))


if __name__ == "__main__":
    convert()
