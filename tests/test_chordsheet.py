"""Tests for plain-text chord sheets and their conversion to ChordPro."""

import pytest

from chordpro.chordsheet import (
    chord_line,
    chord_sheet_to_chordpro,
    place_chords,
    section_kind,
)
from chordpro.parser import parse


def _section(line: str):
    """Section labels as a chord sheet usually has them: "Verse 1:"."""
    label = line.strip().rstrip(":")
    kind = section_kind(label) if line.strip().endswith(":") else None
    return (kind, label) if kind else None


def _convert(text: str) -> str:
    return "\n".join(chord_sheet_to_chordpro(text.splitlines(), _section))


# ---------------------------------------------------------------------------
# section_kind
# ---------------------------------------------------------------------------


class TestSectionKind:
    @pytest.mark.parametrize(
        "name, kind",
        [
            ("Verse 1", "verse"),
            ("CHORUS", "chorus"),
            ("Refrain", "chorus"),
            ("Pre-Chorus", "prechorus"),
            ("Pre Chorus 2", "prechorus"),
            ("Bridge", "bridge"),
            ("Ending", "outro"),
            ("Turnaround", "interlude"),
        ],
    )
    def test_known_names(self, name, kind):
        assert section_kind(name) == kind

    def test_unknown_name(self):
        assert section_kind("Amazing grace") is None


# ---------------------------------------------------------------------------
# chord_line
# ---------------------------------------------------------------------------


class TestChordLine:
    @pytest.mark.parametrize(
        "line",
        [
            "G       D/F#    Em7   C",
            "  Bbmaj7   Csus4  F",
            "| G / / / | C / / / |",
            "Am  G  (x2)",
            "N.C.   E",
        ],
    )
    def test_chords(self, line):
        assert chord_line(line) == line

    @pytest.mark.parametrize(
        "line",
        [
            "Amazing grace how sweet the sound",
            "A mighty fortress is our God",
            "",
            "[G]Already ChordPro",
            "{comment: Capo 2}",
            "(Repeat)",
        ],
    )
    def test_not_chords(self, line):
        assert chord_line(line) is None

    def test_marked_as_chords(self):
        assert chord_line(".Whatever it holds") == "Whatever it holds"


# ---------------------------------------------------------------------------
# place_chords
# ---------------------------------------------------------------------------


class TestPlaceChords:
    def test_over_lyric(self):
        assert place_chords("G       C", "Amazing grace") == ["[G]Amazing [C]grace"]

    def test_past_the_lyric(self):
        assert place_chords("G           D", "Grace") == ["[G]Grace       [D]"]

    def test_without_lyric(self):
        # The chords keep their columns, as spaces
        assert place_chords("G   C   D") == ["[G]    [C]    [D]"]

    def test_instructions_become_comments(self):
        assert place_chords("G  C  (x2)") == ["{comment: x2}", "[G]   [C]"]


# ---------------------------------------------------------------------------
# chord_sheet_to_chordpro
# ---------------------------------------------------------------------------

SHEET = """\
Verse 1:
G             C             G
Amazing grace how sweet the sound
G                        D
That saved a wretch like me

Chorus:
C         G
My chains are gone
(Repeat)
"""


class TestChordSheetToChordPro:
    def test_sections_and_chords(self):
        assert _convert(SHEET) == (
            "{start_of_verse: Verse 1}\n"
            "[G]Amazing grace [C]how sweet the [G]sound\n"
            "[G]That saved a wretch like [D]me\n"
            "{end_of_verse}\n"
            "\n"
            "{start_of_chorus: Chorus}\n"
            "[C]My chains [G]are gone\n"
            "{comment: Repeat}\n"
            "{end_of_chorus}"
        )

    def test_result_parses(self):
        song = parse(_convert(SHEET))
        assert len(song.body) > 0

    def test_tab_section(self):
        text = "Intro:\ne|---0---3---|\nB|---1---0---|\n\nVerse:\nG\nHello"
        result = _convert(text)
        assert result.startswith("{start_of_tab: Intro}\ne|---0---3---|\nB|---1---0---|\n{end_of_tab}")
        assert "{start_of_verse: Verse}\n[G]Hello\n{end_of_verse}" in result

    def test_chords_without_lyric(self):
        assert _convert("Intro:\nG  C  D\n") == "{start_of_intro: Intro}\n[G]   [C]   [D]\n{end_of_intro}"

    def test_trims_blank_lines(self):
        assert _convert("\n\nG\nHello\n\n") == "[G]Hello"
