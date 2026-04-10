"""Tests for Nashville Number System notation support."""

import pytest
from flask import g

from chordpro.constants import _NASHVILLE_CHROMATIC
from chordpro.parser import (
    build_nashville_semi_to_name,
    key_to_semitone,
)
from chordpro.renderers import chordpro_to_html

# ---------------------------------------------------------------------------
# _NASHVILLE_CHROMATIC constant
# ---------------------------------------------------------------------------


class TestNashvilleChromatic:
    def test_covers_all_12_semitones(self):
        assert set(_NASHVILLE_CHROMATIC.keys()) == set(range(12))

    def test_diatonic_degrees_are_plain_numbers(self):
        diatonic_offsets = {0, 2, 4, 5, 7, 9, 11}
        for offset in diatonic_offsets:
            assert _NASHVILLE_CHROMATIC[offset].lstrip("♭♯").isdigit()
            assert not _NASHVILLE_CHROMATIC[offset].startswith(("♭", "♯"))

    def test_chromatic_degrees_have_accidental(self):
        chromatic_offsets = {1, 3, 6, 8, 10}
        for offset in chromatic_offsets:
            assert _NASHVILLE_CHROMATIC[offset][0] in ("♭", "♯")

    def test_tonic_is_1(self):
        assert _NASHVILLE_CHROMATIC[0] == "1"

    def test_tritone_is_sharp_4(self):
        # Nashville convention: tritone = ♯4, not ♭5
        assert _NASHVILLE_CHROMATIC[6] == "♯4"

    def test_minor_seventh_is_flat_7(self):
        assert _NASHVILLE_CHROMATIC[10] == "♭7"


# ---------------------------------------------------------------------------
# key_to_semitone
# ---------------------------------------------------------------------------


class TestKeyToSemitone:
    @pytest.mark.parametrize(
        "key, expected",
        [
            ("C", 0),
            ("C#", 1),
            ("Db", 1),
            ("D", 2),
            ("Eb", 3),
            ("E", 4),
            ("F", 5),
            ("F#", 6),
            ("G", 7),
            ("Ab", 8),
            ("A", 9),
            ("Bb", 10),
            ("B", 11),
        ],
    )
    def test_major_keys(self, key, expected):
        assert key_to_semitone(key) == expected

    @pytest.mark.parametrize(
        "key, expected",
        [
            ("Am", 9),
            ("Em", 4),
            ("Bm", 11),
            ("F#m", 6),
            ("Cm", 0),
            ("Gm", 7),
            ("Dm", 2),
        ],
    )
    def test_minor_keys_strip_m(self, key, expected):
        assert key_to_semitone(key) == expected

    def test_unknown_key_defaults_to_c(self):
        assert key_to_semitone("X") == 0

    def test_strips_whitespace(self):
        assert key_to_semitone("  G  ") == 7


# ---------------------------------------------------------------------------
# build_nashville_semi_to_name
# ---------------------------------------------------------------------------


class TestBuildNashvilleSemiToName:
    def test_returns_12_entries(self):
        assert len(build_nashville_semi_to_name(0)) == 12

    def test_key_of_c_tonic_is_1(self):
        # C = semitone 0; in key of C the tonic maps to "1"
        m = build_nashville_semi_to_name(0)
        assert m[0] == "1"

    def test_key_of_c_g_is_5(self):
        # G = semitone 7; in key of C that's a perfect fifth → "5"
        m = build_nashville_semi_to_name(0)
        assert m[7] == "5"

    def test_key_of_g_g_is_1(self):
        m = build_nashville_semi_to_name(7)
        assert m[7] == "1"

    def test_key_of_g_c_is_4(self):
        # C (semitone 0) is 5 semitones below G (semitone 7), i.e. offset = (0 - 7) % 12 = 5 → "4"
        m = build_nashville_semi_to_name(7)
        assert m[0] == "4"

    def test_key_of_g_d_is_5(self):
        # D = semitone 2; (2 - 7) % 12 = 7 → "5"
        m = build_nashville_semi_to_name(7)
        assert m[2] == "5"

    def test_key_of_g_f_sharp_is_7(self):
        # F# = semitone 6; (6 - 7) % 12 = 11 → "7"
        m = build_nashville_semi_to_name(7)
        assert m[6] == "7"

    def test_key_of_a_a_is_1(self):
        m = build_nashville_semi_to_name(9)
        assert m[9] == "1"

    def test_key_of_bb_d_is_3(self):
        # D = semitone 2; Bb = semitone 10; (2 - 10) % 12 = 4 → "3"
        m = build_nashville_semi_to_name(10)
        assert m[2] == "3"


# ---------------------------------------------------------------------------
# Chord conversion with Nashville numbers
# ---------------------------------------------------------------------------


class TestNashvilleChordConversion:
    """Test that chordpro_to_html produces Nashville numbers in chord spans."""

    def _html(self, content, key="C"):
        semi_to_name = build_nashville_semi_to_name(key_to_semitone(key))
        return chordpro_to_html(content, semi_to_name)

    def test_tonic_chord_is_1(self):
        assert ">1<" in self._html("[C]Hello", key="C")

    def test_fourth_chord(self):
        assert ">4<" in self._html("[F]word", key="C")

    def test_fifth_chord(self):
        assert ">5<" in self._html("[G]word", key="C")

    def test_minor_chord_keeps_suffix(self):
        # Am in key of C = 6th scale degree → "6m"
        assert ">6m<" in self._html("[Am]word", key="C")

    def test_seventh_chord_keeps_suffix(self):
        # G7 in key of C = 5th degree → "57"
        assert ">57<" in self._html("[G7]word", key="C")

    def test_flat_seventh_chord(self):
        # Bb in key of C = ♭7
        assert ">♭7<" in self._html("[Bb]word", key="C")

    def test_data_chord_still_standard(self):
        # data-chord must retain the original standard notation
        html = self._html("[G]word", key="C")
        assert 'data-chord="G"' in html

    def test_in_key_of_g(self):
        # D chord in key of G = "5"
        assert ">5<" in self._html("[D]word", key="G")

    def test_in_key_of_g_c_is_4(self):
        assert ">4<" in self._html("[C]word", key="G")

    def test_sharp_chord_in_key(self):
        # C# in key of C = ♭2
        assert ">♭2<" in self._html("[C#]word", key="C")


# ---------------------------------------------------------------------------
# Flask filter integration
# ---------------------------------------------------------------------------


class TestNashvilleFilter:
    def test_filter_with_g_notation_and_g_key(self, app):
        with app.test_request_context("/"):
            g.notation = "nashville"
            g.key = "G"
            filt = app.jinja_env.filters["chordpro"]
            result = filt("[G]Amazing [D]grace")
        assert ">1<" in result  # G = 1 in key of G
        assert ">5<" in result  # D = 5 in key of G

    def test_filter_reads_key_from_song_meta(self, app):
        with app.test_request_context("/"):
            g.notation = "nashville"
            # No g.key set — should fall back to {key: G} in content
            filt = app.jinja_env.filters["chordpro"]
            result = filt("{key: G}\n[G]Amazing [D]grace")
        assert ">1<" in result
        assert ">5<" in result

    def test_filter_defaults_to_c_when_no_key(self, app):
        with app.test_request_context("/"):
            g.notation = "nashville"
            filt = app.jinja_env.filters["chordpro"]
            result = filt("[C]Hello")
        assert ">1<" in result  # C = 1 in default key of C

    def test_g_key_takes_precedence_over_meta(self, app):
        with app.test_request_context("/"):
            g.notation = "nashville"
            g.key = "G"
            filt = app.jinja_env.filters["chordpro"]
            # Content says key D, but g.key = G should win
            result = filt("{key: D}\n[G]word")
        assert ">1<" in result  # G = 1 in key of G, not 4 in key of D

    def test_non_nashville_notation_unaffected(self, app):
        with app.test_request_context("/"):
            g.notation = "standard"
            filt = app.jinja_env.filters["chordpro"]
            result = filt("[G]Hello")
        assert ">G<" in result
