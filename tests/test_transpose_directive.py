"""Tests for apply_transpose_directives and the chordpro filter's
``transpose_directives`` argument."""

from flask import g

from chordpro.models import ChordLine, Transpose
from chordpro.parser import apply_transpose_directives, parse


def chords(lines) -> list[str]:
    return [
        segment.chord
        for line in lines
        if isinstance(line, ChordLine)
        for segment in line.segments
        if segment.chord
    ]


def test_a_song_without_directives_is_returned_as_it_is():
    song = parse("{key: G}\n[G]Grace")
    assert apply_transpose_directives(song) is song


def test_a_directive_before_the_first_chord_moves_the_song_and_its_key():
    song = apply_transpose_directives(
        parse("{key: G}\n{transpose: 2}\n[G]Grace [D/F#]so")
    )
    assert song.meta.key == ["A"]
    assert chords(song.body) == ["A", "E/G♯"]
    assert not any(isinstance(item, Transpose) for item in song.body)


def test_chords_are_spelled_for_the_key_they_land_in():
    song = apply_transpose_directives(parse("{key: G}\n{transpose: 1}\n[G]Grace [C]so"))
    assert song.meta.key == ["A♭"]
    assert chords(song.body) == ["A♭", "D♭"]


def test_with_no_key_sharps_go_up_and_flats_go_down():
    up = apply_transpose_directives(parse("{transpose: 2}\n[E]Grace"))
    down = apply_transpose_directives(parse("{transpose: -10}\n[E]Grace"))
    assert chords(up.body) == ["F♯"]
    assert chords(down.body) == ["G♭"]


def test_a_directive_counts_from_the_chart_as_written_until_the_next():
    song = apply_transpose_directives(
        parse(
            "[C]one\n{transpose: 2}\n[C]two\n{transpose: 5}\n[C]three\n{transpose}\n[C]four"
        )
    )
    assert chords(song.body) == ["C", "D", "F", "C"]


def test_a_section_begun_at_another_offset_is_in_a_key_of_its_own():
    song = apply_transpose_directives(
        parse(
            "{key: G}\n{sov}\n[G]one\n{eov}\n{transpose: 2}\n{soc}\n[G]two\n{eoc}"
            "\n{transpose}\n{soc}\n[G]three\n{eoc}"
        )
    )
    verse, chorus, last = song.body
    assert song.meta.key == ["G"]
    assert (verse.key, chords(verse.lines)) == (None, ["G"])
    assert (chorus.key, chords(chorus.lines)) == ("A", ["A"])
    assert (last.key, chords(last.lines)) == (None, ["G"])


def test_a_directive_inside_a_section_moves_the_lines_after_it():
    song = apply_transpose_directives(
        parse("{key: G}\n{sov}\n[G]one\n{transpose: 2}\n[G]two\n{eov}")
    )
    assert chords(song.body[0].lines) == ["G", "A"]


def test_the_filter_applies_them_only_when_asked(app):
    with app.test_request_context("/"):
        filt = app.jinja_env.filters["chordpro"]
        content = "{key: G}\n{transpose: 2}\n[G]Grace"
        assert ">G<" in filt(content)
        played = filt(content, transpose_directives=True)
    assert ">A<" in played
    assert "cp-transpose" not in played


def test_the_filter_names_them_in_the_notation(app):
    with app.test_request_context("/"):
        g.notation = "nashville"
        filt = app.jinja_env.filters["chordpro"]
        played = filt("{key: G}\n{transpose: 2}\n[G]Grace", transpose_directives=True)
    assert ">1<" in played
