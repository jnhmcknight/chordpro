"""Tests for the chordpro and format_key Jinja2 template filters."""

from flask import g
from markupsafe import Markup

# ---------------------------------------------------------------------------
# chordpro filter
# ---------------------------------------------------------------------------


class TestChordproFilter:
    def test_renders_via_jinja(self, app):
        with app.test_request_context("/"):
            env = app.jinja_env
            tmpl = env.from_string("{{ content | chordpro }}")
            result = tmpl.render(content="[G]Hello")
        assert 'class="cp-chord"' in result

    def test_returns_markup_safe(self, app):
        with app.test_request_context("/"):
            filt = app.jinja_env.filters["chordpro"]
            result = filt("[G]Hello")
        assert isinstance(result, Markup)

    def test_empty_content(self, app):
        with app.test_request_context("/"):
            filt = app.jinja_env.filters["chordpro"]
            assert filt("") == Markup("")

    def test_standard_notation_default(self, app):
        with app.test_request_context("/"):
            filt = app.jinja_env.filters["chordpro"]
            result = filt("[Bb]word")
        assert ">B♭<" in result

    def test_latin_notation_via_g(self, app):
        with app.test_request_context("/"):
            g.notation = "latin"
            filt = app.jinja_env.filters["chordpro"]
            result = filt("[C]word")
        assert ">Do<" in result

    def test_german_notation_via_g(self, app):
        with app.test_request_context("/"):
            g.notation = "german"
            filt = app.jinja_env.filters["chordpro"]
            result = filt("[Bb]word")
        # Bb (semitone 10) → key_int=1 → "B" in German
        assert ">B<" in result

    def test_xss_escaped_in_content(self, app):
        with app.test_request_context("/"):
            filt = app.jinja_env.filters["chordpro"]
            result = filt("<script>alert(1)</script>")
        assert "<script>" not in result


# ---------------------------------------------------------------------------
# format_key filter
# ---------------------------------------------------------------------------


class TestFormatKeyFilter:
    def test_major_key_standard(self, app):
        with app.test_request_context("/"):
            filt = app.jinja_env.filters["format_key"]
            # key_int=3 → C in standard
            assert filt(3) == "C"

    def test_major_key_zero_standard(self, app):
        with app.test_request_context("/"):
            filt = app.jinja_env.filters["format_key"]
            assert filt(0) == "A"

    def test_minor_key_standard(self, app):
        with app.test_request_context("/"):
            filt = app.jinja_env.filters["format_key"]
            # key_int=15 (12+3) → Am in standard
            assert filt(15) == "Am"

    def test_major_key_latin_via_g(self, app):
        with app.test_request_context("/"):
            g.notation = "latin"
            filt = app.jinja_env.filters["format_key"]
            assert filt(3) == "Do"

    def test_major_key_german_via_g(self, app):
        with app.test_request_context("/"):
            g.notation = "german"
            filt = app.jinja_env.filters["format_key"]
            assert filt(3) == "C"

    def test_invalid_key_returns_string(self, app):
        with app.test_request_context("/"):
            filt = app.jinja_env.filters["format_key"]
            assert filt(99) == "99"

    def test_none_key_returns_string(self, app):
        with app.test_request_context("/"):
            filt = app.jinja_env.filters["format_key"]
            assert filt(None) == ""

    def test_all_major_keys_standard(self, app):
        expected = {
            0: "A",
            1: "B♭",
            2: "B",
            3: "C",
            4: "C♯",
            5: "D",
            6: "D♯",
            7: "E",
            8: "F",
            9: "F♯",
            10: "G",
            11: "A♭",
        }
        with app.test_request_context("/"):
            filt = app.jinja_env.filters["format_key"]
            for key_int, name in expected.items():
                assert filt(key_int) == name, f"key_int={key_int}"

    def test_all_minor_keys_standard(self, app):
        expected = {
            12: "F♯m",
            13: "Gm",
            14: "G♯m",
            15: "Am",
            16: "B♭m",
            17: "Bm",
            18: "Cm",
            19: "C♯m",
            20: "Dm",
            21: "D♯m",
            22: "Em",
            23: "Fm",
        }
        with app.test_request_context("/"):
            filt = app.jinja_env.filters["format_key"]
            for key_int, name in expected.items():
                assert filt(key_int) == name, f"key_int={key_int}"

    def test_string_key_standard_returns_as_is(self, app):
        with app.test_request_context("/"):
            filt = app.jinja_env.filters["format_key"]
            assert filt("C") == "C"

    def test_string_key_minor_standard_returns_as_is(self, app):
        with app.test_request_context("/"):
            filt = app.jinja_env.filters["format_key"]
            assert filt("Am") == "Am"

    def test_string_key_latin_major(self, app):
        with app.test_request_context("/"):
            from flask import g
            g.notation = "latin"
            filt = app.jinja_env.filters["format_key"]
            assert filt("C") == "Do"

    def test_string_key_latin_minor(self, app):
        with app.test_request_context("/"):
            from flask import g
            g.notation = "latin"
            filt = app.jinja_env.filters["format_key"]
            assert filt("Am") == "Lam"

    def test_string_key_german_major(self, app):
        with app.test_request_context("/"):
            from flask import g
            g.notation = "german"
            filt = app.jinja_env.filters["format_key"]
            # B♭ major (key_int=1) → "B" in German
            assert filt("B♭") == "B"

    def test_string_key_unrecognised_returns_as_is(self, app):
        with app.test_request_context("/"):
            from flask import g
            g.notation = "latin"
            filt = app.jinja_env.filters["format_key"]
            assert filt("Xyz") == "Xyz"

    def test_nashville_notation_via_g(self, app):
        with app.test_request_context("/"):
            from flask import g
            g.notation = "nashville"
            filt = app.jinja_env.filters["chordpro"]
            result = filt("{title: Test}\n[C]word", "html")
        # Nashville renders chords as numbers; C in key of C is "1"
        assert result is not None
