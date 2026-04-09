"""Tests for the ChordPro data model dataclasses."""

import pytest

from chordpro.models import (
    BreakLine,
    Bridge,
    Chorus,
    ChordLine,
    CommentLine,
    Instrumental,
    Interlude,
    Intro,
    LyricLine,
    Outro,
    PreChorus,
    Section,
    Segment,
    Solo,
    Song,
    Tab,
    Tag,
    Verse,
)

# ---------------------------------------------------------------------------
# Line types
# ---------------------------------------------------------------------------


class TestSegment:
    def test_with_chord(self):
        s = Segment(chord="G", lyric="Hello")
        assert s.chord == "G"
        assert s.lyric == "Hello"

    def test_lyric_only(self):
        s = Segment(chord=None, lyric="only text")
        assert s.chord is None

    def test_empty_lyric(self):
        s = Segment(chord="C", lyric="")
        assert s.lyric == ""


class TestChordLine:
    def test_default_empty_segments(self):
        assert ChordLine().segments == []

    def test_with_segments(self):
        segs = [Segment("G", "Hello"), Segment(None, " world")]
        cl = ChordLine(segments=segs)
        assert len(cl.segments) == 2


class TestLyricLine:
    def test_stores_text(self):
        assert LyricLine("Amazing grace").text == "Amazing grace"


class TestBreakLine:
    def test_instantiates(self):
        assert BreakLine() is not None


class TestCommentLine:
    def test_stores_text(self):
        assert CommentLine("a note").text == "a note"


# ---------------------------------------------------------------------------
# Named section types
# ---------------------------------------------------------------------------

NAMED_SECTION_CASES = [
    (Verse, "verse"),
    (Chorus, "chorus"),
    (Bridge, "bridge"),
    (PreChorus, "prechorus"),
    (Outro, "outro"),
    (Intro, "intro"),
    (Tab, "tab"),
    (Tag, "tag"),
    (Interlude, "interlude"),
    (Solo, "solo"),
    (Instrumental, "instrumental"),
]


class TestNamedSections:
    @pytest.mark.parametrize("cls, expected_kind", NAMED_SECTION_CASES)
    def test_kind_property(self, cls, expected_kind):
        assert cls(label="Test").kind == expected_kind

    @pytest.mark.parametrize("cls, _", NAMED_SECTION_CASES)
    def test_label_stored(self, cls, _):
        assert cls(label="My Label").label == "My Label"

    @pytest.mark.parametrize("cls, _", NAMED_SECTION_CASES)
    def test_default_empty_lines(self, cls, _):
        assert cls(label="x").lines == []

    @pytest.mark.parametrize("cls, _", NAMED_SECTION_CASES)
    def test_lines_mutable_per_instance(self, cls, _):
        a = cls(label="x")
        b = cls(label="y")
        a.lines.append(BreakLine())
        assert b.lines == [], "lines list must not be shared between instances"

    @pytest.mark.parametrize("cls, _", NAMED_SECTION_CASES)
    def test_kind_is_not_an_init_param(self, cls, _):
        """kind must be a property, not accepted by __init__."""
        import inspect

        sig = inspect.signature(cls.__init__)
        assert "kind" not in sig.parameters


class TestGenericSection:
    def test_stores_kind_and_label(self):
        s = Section(kind="custom", label="Custom Section")
        assert s.kind == "custom"
        assert s.label == "Custom Section"

    def test_default_empty_lines(self):
        assert Section(kind="x", label="y").lines == []


# ---------------------------------------------------------------------------
# Song
# ---------------------------------------------------------------------------


class TestSong:
    def test_default_empty_body(self):
        assert Song().body == []

    def test_body_with_mixed_items(self):
        song = Song(body=[Verse(label="V1"), LyricLine("text"), BreakLine()])
        assert len(song.body) == 3
