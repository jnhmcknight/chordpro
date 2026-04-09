"""Tests for the ChordPro parser: parse() and chord-notation helpers."""

import pytest

from chordpro.constants import KEY_NAMES
from chordpro.models import (
    BreakLine,
    Bridge,
    Chorus,
    ChordLine,
    CommentLine,
    LyricLine,
    PreChorus,
    Section,
    Song,
    Tab,
    Verse,
)
from chordpro.parser import _convert_chord_root, build_chord_semi_to_name, parse

# ---------------------------------------------------------------------------
# build_chord_semi_to_name
# ---------------------------------------------------------------------------


class TestBuildChordSemiToName:
    def test_standard_returns_12_entries(self):
        assert len(build_chord_semi_to_name("standard")) == 12

    def test_standard_c_maps_correctly(self):
        # key_int=3 → "C", chromatic semitone = (3+9)%12 = 0
        assert build_chord_semi_to_name("standard")[0] == "C"

    def test_standard_a_maps_correctly(self):
        # key_int=0 → "A", chromatic = (0+9)%12 = 9
        assert build_chord_semi_to_name("standard")[9] == "A"

    def test_unknown_notation_falls_back_to_standard(self):
        assert build_chord_semi_to_name("nonexistent") == build_chord_semi_to_name(
            "standard"
        )

    def test_german_bb_is_b(self):
        # B-flat (semitone 10) → key_int=1 → "B" in German
        assert build_chord_semi_to_name("german")[10] == "B"

    def test_latin_c_is_do(self):
        assert build_chord_semi_to_name("latin")[0] == "Do"


# ---------------------------------------------------------------------------
# _convert_chord_root
# ---------------------------------------------------------------------------


class TestConvertChordRoot:
    def test_converts_simple_root(self):
        s = build_chord_semi_to_name("latin")
        assert _convert_chord_root("C", s) == "Do"

    def test_preserves_suffix(self):
        s = build_chord_semi_to_name("latin")
        assert _convert_chord_root("Cm", s) == "Dom"

    def test_sharp_root(self):
        s = build_chord_semi_to_name("latin")
        assert _convert_chord_root("F#", s) == "Fa#"

    def test_flat_root(self):
        s = build_chord_semi_to_name("standard")
        assert _convert_chord_root("Bb", s) == "Bb"

    def test_passthrough_if_not_a_note(self):
        s = build_chord_semi_to_name("standard")
        assert _convert_chord_root("N.C.", s) == "N.C."


# ---------------------------------------------------------------------------
# KEY_NAMES completeness
# ---------------------------------------------------------------------------


class TestKeyNames:
    @pytest.mark.parametrize("notation", ["standard", "german", "latin"])
    def test_12_major_keys(self, notation):
        assert len(KEY_NAMES[notation]["major"]) == 12

    @pytest.mark.parametrize("notation", ["standard", "german", "latin"])
    def test_12_minor_keys(self, notation):
        assert len(KEY_NAMES[notation]["minor"]) == 12

    @pytest.mark.parametrize("notation", ["standard", "german", "latin"])
    def test_major_keys_indexed_0_to_11(self, notation):
        assert set(KEY_NAMES[notation]["major"].keys()) == set(range(12))

    @pytest.mark.parametrize("notation", ["standard", "german", "latin"])
    def test_minor_keys_indexed_0_to_11(self, notation):
        assert set(KEY_NAMES[notation]["minor"].keys()) == set(range(12))


# ---------------------------------------------------------------------------
# parse()
# ---------------------------------------------------------------------------


class TestParseEmpty:
    def test_empty_string_returns_empty_song(self):
        assert parse("") == Song()

    def test_none_like_falsy_returns_empty_song(self):
        # parse() accepts str; an empty string is the falsy case
        song = parse("")
        assert song.body == []


class TestParseLines:
    def test_plain_lyric_line(self):
        song = parse("Amazing grace")
        assert len(song.body) == 1
        assert isinstance(song.body[0], LyricLine)
        assert song.body[0].text == "Amazing grace"

    def test_blank_line_becomes_break(self):
        song = parse("line one\n\nline two")
        assert any(isinstance(item, BreakLine) for item in song.body)

    def test_chord_line_parsed(self):
        song = parse("[G]Hello [D]world")
        assert len(song.body) == 1
        assert isinstance(song.body[0], ChordLine)

    def test_chord_line_segments(self):
        song = parse("[G]Hello")
        cl = song.body[0]
        assert isinstance(cl, ChordLine)
        chord_seg = next(s for s in cl.segments if s.chord is not None)
        assert chord_seg.chord == "G"
        assert chord_seg.lyric == "Hello"

    def test_trailing_chord_no_lyric(self):
        song = parse("[G]")
        cl = song.body[0]
        assert cl.segments[-1].chord == "G"
        assert cl.segments[-1].lyric == ""

    def test_crlf_handled(self):
        song = parse("line one\r\nline two")
        assert len(song.body) == 2

    def test_top_level_comment_directive(self):
        song = parse("{comment: A note}")
        assert len(song.body) == 1
        assert isinstance(song.body[0], CommentLine)
        assert song.body[0].text == "A note"

    def test_comment_short_form(self):
        song = parse("{c: Short}")
        assert isinstance(song.body[0], CommentLine)

    def test_unknown_directive_ignored(self):
        song = parse("{title: My Song}")
        assert song.body == []


class TestParseSections:
    def test_verse_creates_verse_instance(self):
        song = parse("{start_of_verse}")
        assert len(song.body) == 1
        assert isinstance(song.body[0], Verse)

    def test_chorus_creates_chorus_instance(self):
        song = parse("{start_of_chorus}")
        assert isinstance(song.body[0], Chorus)

    def test_bridge_creates_bridge_instance(self):
        song = parse("{start_of_bridge}")
        assert isinstance(song.body[0], Bridge)

    def test_prechorus_directive(self):
        song = parse("{start_of_prechorus}")
        assert isinstance(song.body[0], PreChorus)

    def test_pre_chorus_directive_also_maps_to_prechorus(self):
        song = parse("{start_of_pre_chorus}")
        assert isinstance(song.body[0], PreChorus)

    def test_unknown_section_creates_generic_section(self):
        song = parse("{start_of_bridge2}")
        assert isinstance(song.body[0], Section)
        assert song.body[0].kind == "bridge2"

    def test_section_default_label(self):
        song = parse("{start_of_verse}")
        assert song.body[0].label == "Verse"

    def test_section_custom_label(self):
        song = parse("{start_of_verse: Verse 1}")
        assert song.body[0].label == "Verse 1"

    def test_lines_inside_section(self):
        song = parse("{start_of_verse}\n[G]Amazing grace\n{end_of_verse}")
        verse = song.body[0]
        assert isinstance(verse, Verse)
        assert len(verse.lines) == 1
        assert isinstance(verse.lines[0], ChordLine)

    def test_end_of_section_closes_it(self):
        song = parse("{start_of_verse}\nline\n{end_of_verse}\nafter")
        assert len(song.body) == 2
        assert isinstance(song.body[0], Verse)
        assert isinstance(song.body[1], LyricLine)

    def test_unclosed_section_appended_at_eof(self):
        song = parse("{start_of_verse}\nline")
        assert len(song.body) == 1
        assert isinstance(song.body[0], Verse)
        assert len(song.body[0].lines) == 1

    def test_consecutive_sections_no_end_directive(self):
        song = parse("{start_of_verse}\nv\n{start_of_chorus}\nc")
        assert len(song.body) == 2
        assert isinstance(song.body[0], Verse)
        assert isinstance(song.body[1], Chorus)

    def test_comment_inside_section(self):
        song = parse("{start_of_verse}\n{comment: note}\n{end_of_verse}")
        verse = song.body[0]
        assert len(verse.lines) == 1
        assert isinstance(verse.lines[0], CommentLine)

    def test_break_inside_section(self):
        song = parse("{start_of_verse}\nline\n\nline\n{end_of_verse}")
        verse = song.body[0]
        assert any(isinstance(l, BreakLine) for l in verse.lines)

    def test_tab_creates_tab_instance(self):
        song = parse("{start_of_tab}")
        assert isinstance(song.body[0], Tab)


# ---------------------------------------------------------------------------
# Short-form directives
# ---------------------------------------------------------------------------


class TestShortFormDirectives:
    @pytest.mark.parametrize(
        "directive, expected_type",
        [
            ("{sov}", Verse),
            ("{soc}", Chorus),
            ("{sob}", Bridge),
            ("{sot}", Tab),
        ],
    )
    def test_short_start_creates_correct_section(self, directive, expected_type):
        song = parse(directive)
        assert isinstance(song.body[0], expected_type)

    @pytest.mark.parametrize(
        "start, end",
        [
            ("{sov}", "{eov}"),
            ("{soc}", "{eoc}"),
            ("{sob}", "{eob}"),
            ("{sot}", "{eot}"),
        ],
    )
    def test_short_end_closes_section(self, start, end):
        song = parse(f"{start}\nline\n{end}\nafter")
        assert len(song.body) == 2  # section + trailing lyric line

    @pytest.mark.parametrize(
        "start, end",
        [
            ("{start_of_verse}", "{eov}"),
            ("{sov}", "{end_of_verse}"),
            ("{start_of_chorus}", "{eoc}"),
            ("{soc}", "{end_of_chorus}"),
            ("{start_of_bridge}", "{eob}"),
            ("{sob}", "{end_of_bridge}"),
            ("{start_of_tab}", "{eot}"),
            ("{sot}", "{end_of_tab}"),
        ],
    )
    def test_mixed_short_and_long_forms(self, start, end):
        song = parse(f"{start}\nline\n{end}\nafter")
        assert len(song.body) == 2

    def test_short_form_section_has_correct_kind(self):
        song = parse("{sov}")
        section = song.body[0]
        assert isinstance(section, Verse)
        assert section.kind == "verse"

    def test_short_form_uses_default_label(self):
        song = parse("{sov}")
        section = song.body[0]
        assert isinstance(section, Verse)
        assert section.label == "Verse"

    def test_short_form_accepts_custom_label(self):
        song = parse("{sov: Verse 1}")
        section = song.body[0]
        assert isinstance(section, Verse)
        assert section.label == "Verse 1"
