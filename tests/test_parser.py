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
from chordpro.constants import sbp_key_int_to_str, str_key_to_sbp_int
from chordpro.models import Segment, SongMeta
from chordpro.parser import (
    _convert_chord_root,
    _normalize_accidental,
    build_chord_semi_to_name,
    build_transposed_semi_to_name,
    parse,
    transpose_song,
)

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
        assert _convert_chord_root("F#", s) == "Fa♯"

    def test_flat_root(self):
        s = build_chord_semi_to_name("standard")
        assert _convert_chord_root("Bb", s) == "B♭"

    def test_passthrough_if_not_a_note(self):
        s = build_chord_semi_to_name("standard")
        assert _convert_chord_root("N.C.", s) == "N.C."

    def test_already_unicode_sharp_accepted(self):
        # Input already uses ♯ — should still resolve correctly
        s = build_chord_semi_to_name("standard")
        assert _convert_chord_root("F♯", s) == "F♯"

    def test_already_unicode_flat_accepted(self):
        s = build_chord_semi_to_name("standard")
        assert _convert_chord_root("B♭", s) == "B♭"

    def test_unrecognised_accidental_passthrough(self):
        # "Cb" normalizes to "C♭" which is not in _STANDARD_NOTE_TO_SEMI;
        # _convert_chord_root should return the original chord unchanged.
        s = build_chord_semi_to_name("standard")
        assert _convert_chord_root("Cb", s) == "Cb"


# ---------------------------------------------------------------------------
# _normalize_accidental
# ---------------------------------------------------------------------------


class TestNormalizeAccidental:
    def test_ascii_sharp_to_unicode(self):
        assert _normalize_accidental("C#") == "C♯"

    def test_ascii_flat_to_unicode(self):
        assert _normalize_accidental("Bb") == "B♭"

    def test_natural_note_unchanged(self):
        assert _normalize_accidental("C") == "C"

    def test_already_unicode_sharp_unchanged(self):
        assert _normalize_accidental("F♯") == "F♯"

    def test_already_unicode_flat_unchanged(self):
        assert _normalize_accidental("B♭") == "B♭"


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
        assert any(isinstance(line, BreakLine) for line in verse.lines)

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


# ---------------------------------------------------------------------------
# _directive_to_item edge cases
# ---------------------------------------------------------------------------


class TestDirectiveEdgeCases:
    def test_invalid_transpose_value_gives_none_semitones(self):
        from chordpro.models import Transpose

        song = parse("{transpose: abc}")
        assert len(song.body) == 1
        item = song.body[0]
        assert isinstance(item, Transpose)
        assert item.semitones is None

    def test_invalid_columns_value_defaults_to_one(self):
        from chordpro.models import Columns

        song = parse("{columns: bad}")
        assert len(song.body) == 1
        item = song.body[0]
        assert isinstance(item, Columns)
        assert item.count == 1

    def test_unknown_directive_is_silently_ignored(self):
        # {frobnicate: value} is not a known directive — body should be empty.
        song = parse("{frobnicate: some value}")
        assert song.body == []


# ---------------------------------------------------------------------------
# sbp_key_int_to_str
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# build_transposed_semi_to_name
# ---------------------------------------------------------------------------


class TestBuildTransposedSemiToName:
    def test_returns_12_entries(self):
        assert len(build_transposed_semi_to_name(0)) == 12

    def test_zero_shift_is_identity(self):
        assert build_transposed_semi_to_name(0) == build_chord_semi_to_name("standard")

    def test_full_octave_shift_is_identity(self):
        assert build_transposed_semi_to_name(12) == build_chord_semi_to_name("standard")

    def test_c_shifts_to_g_with_shift_7(self):
        # C is semitone 0; up 7 semitones → G (semitone 7)
        result = build_transposed_semi_to_name(7)
        assert result[0] == "G"

    def test_g_shifts_to_d_with_shift_7(self):
        # G is semitone 7; up 7 → D (semitone 2)
        result = build_transposed_semi_to_name(7)
        assert result[7] == "D"

    def test_latin_notation_respected(self):
        result = build_transposed_semi_to_name(0, notation="latin")
        assert result[0] == "Do"

    def test_german_notation_respected(self):
        result = build_transposed_semi_to_name(0, notation="german")
        assert result[0] == "C"


# ---------------------------------------------------------------------------
# transpose_song
# ---------------------------------------------------------------------------


def _song_in_key(key: str, *chord_strings: str) -> Song:
    """Helper: build a Song in *key* with one ChordLine per chord string."""
    from chordpro.models import ChordLine, Segment, SongMeta

    body = [
        ChordLine(segments=[Segment(chord=c, lyric="word")]) for c in chord_strings
    ]
    return Song(meta=SongMeta(key=[key]), body=body)


class TestTransposeSong:
    def test_meta_key_updated_to_target(self):
        song = _song_in_key("C", "C")
        result = transpose_song(song, "G")
        assert result.meta.key == ["G"]

    def test_same_key_returns_updated_meta_key_only(self):
        song = _song_in_key("C", "G")
        result = transpose_song(song, "C")
        assert result.meta.key == ["C"]
        chord = result.body[0].segments[0].chord
        assert chord == "G"  # unchanged

    def test_c_to_g_shifts_c_chord(self):
        # C → G (up 7 semitones): C becomes G
        song = _song_in_key("C", "C")
        result = transpose_song(song, "G")
        assert result.body[0].segments[0].chord == "G"

    def test_c_to_g_shifts_am_chord(self):
        # Am → Em (up 7 semitones)
        song = _song_in_key("C", "Am")
        result = transpose_song(song, "G")
        assert result.body[0].segments[0].chord == "Em"

    def test_chord_suffix_preserved(self):
        song = _song_in_key("C", "Cmaj7")
        result = transpose_song(song, "G")
        chord = result.body[0].segments[0].chord
        assert chord == "Gmaj7"

    def test_ascii_sharp_input_transposed(self):
        # F# (=F♯, semitone 6) + 7 = C♯ (semitone 1)
        song = _song_in_key("C", "F#")
        result = transpose_song(song, "G")
        chord = result.body[0].segments[0].chord
        assert chord == "C♯"

    def test_ascii_flat_input_transposed(self):
        # Bb (=B♭, semitone 10) + 7 = F (semitone 5)
        song = _song_in_key("C", "Bb")
        result = transpose_song(song, "G")
        chord = result.body[0].segments[0].chord
        assert chord == "F"

    def test_unicode_sharp_input_transposed(self):
        song = _song_in_key("C", "F♯")
        result = transpose_song(song, "G")
        assert result.body[0].segments[0].chord == "C♯"

    def test_unicode_flat_input_transposed(self):
        song = _song_in_key("C", "B♭")
        result = transpose_song(song, "G")
        assert result.body[0].segments[0].chord == "F"

    def test_non_chord_segment_none_preserved(self):
        from chordpro.models import ChordLine, SongMeta

        song = Song(
            meta=SongMeta(key=["C"]),
            body=[ChordLine(segments=[Segment(chord=None, lyric="lyrics only")])],
        )
        result = transpose_song(song, "G")
        assert result.body[0].segments[0].chord is None
        assert result.body[0].segments[0].lyric == "lyrics only"

    def test_lyric_line_preserved_unchanged(self):
        from chordpro.models import LyricLine, SongMeta

        song = Song(
            meta=SongMeta(key=["C"]),
            body=[LyricLine("Amazing grace")],
        )
        result = transpose_song(song, "G")
        assert isinstance(result.body[0], LyricLine)
        assert result.body[0].text == "Amazing grace"

    def test_chords_inside_section_transposed(self):
        song = parse("{key: C}\n{start_of_verse}\n[C]Amazing [G]grace\n{end_of_verse}")
        result = transpose_song(song, "G")
        verse = result.body[0]
        segs = verse.lines[0].segments
        chords = [s.chord for s in segs if s.chord is not None]
        assert chords == ["G", "D"]

    def test_song_without_key_meta_defaults_to_c(self):
        from chordpro.models import ChordLine, SongMeta

        song = Song(
            meta=SongMeta(),  # no key set
            body=[ChordLine(segments=[Segment(chord="C", lyric="word")])],
        )
        result = transpose_song(song, "G")
        assert result.body[0].segments[0].chord == "G"

    def test_original_song_not_mutated(self):
        song = _song_in_key("C", "C")
        _ = transpose_song(song, "G")
        assert song.body[0].segments[0].chord == "C"
        assert song.meta.key == ["C"]

    def test_unrecognised_chord_root_passed_through(self):
        from chordpro.models import ChordLine, SongMeta

        song = Song(
            meta=SongMeta(key=["C"]),
            body=[ChordLine(segments=[Segment(chord="N.C.", lyric="")])],
        )
        result = transpose_song(song, "G")
        assert result.body[0].segments[0].chord == "N.C."

    def test_unknown_accidental_combo_passed_through(self):
        # "Cb" normalises to "C♭" which is not in _STANDARD_NOTE_TO_SEMI;
        # the chord should be returned unchanged.
        from chordpro.models import ChordLine, SongMeta

        song = Song(
            meta=SongMeta(key=["C"]),
            body=[ChordLine(segments=[Segment(chord="Cb", lyric="")])],
        )
        result = transpose_song(song, "G")
        assert result.body[0].segments[0].chord == "Cb"


# ---------------------------------------------------------------------------
# sbp_key_int_to_str
# ---------------------------------------------------------------------------


class TestSbpKeyIntToStr:
    def test_none_returns_none(self):
        assert sbp_key_int_to_str(None) is None

    def test_major_key_zero(self):
        assert sbp_key_int_to_str(0) == "A"

    def test_major_key_three(self):
        assert sbp_key_int_to_str(3) == "C"

    def test_major_key_eleven(self):
        assert sbp_key_int_to_str(11) == "A♭"

    def test_minor_key_twelve(self):
        # 12 → minor[0] → "F♯m"
        assert sbp_key_int_to_str(12) == "F♯m"

    def test_minor_key_fifteen(self):
        # 15 → minor[3] → "Am"
        assert sbp_key_int_to_str(15) == "Am"

    def test_minor_key_twenty_three(self):
        # 23 → minor[11] → "Fm"
        assert sbp_key_int_to_str(23) == "Fm"

    def test_out_of_range_returns_none(self):
        assert sbp_key_int_to_str(24) is None


# ---------------------------------------------------------------------------
# str_key_to_sbp_int
# ---------------------------------------------------------------------------


class TestStrKeyToSbpInt:
    def test_none_returns_none(self):
        assert str_key_to_sbp_int(None) is None

    def test_empty_string_returns_none(self):
        assert str_key_to_sbp_int("") is None

    def test_major_key_a(self):
        assert str_key_to_sbp_int("A") == 0

    def test_major_key_c(self):
        assert str_key_to_sbp_int("C") == 3

    def test_major_key_ab(self):
        assert str_key_to_sbp_int("A♭") == 11

    def test_minor_key_fsharpm(self):
        # "F♯m" → minor[0] → 0 + 12 = 12
        assert str_key_to_sbp_int("F♯m") == 12

    def test_minor_key_am(self):
        # "Am" → minor[3] → 3 + 12 = 15
        assert str_key_to_sbp_int("Am") == 15

    def test_minor_key_fm(self):
        # "Fm" → minor[11] → 11 + 12 = 23
        assert str_key_to_sbp_int("Fm") == 23

    def test_unrecognised_returns_none(self):
        assert str_key_to_sbp_int("X") is None

    def test_roundtrip(self):
        for i in range(24):
            key_str = sbp_key_int_to_str(i)
            assert str_key_to_sbp_int(key_str) == i
