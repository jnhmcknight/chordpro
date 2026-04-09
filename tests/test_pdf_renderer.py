"""Tests for PdfRenderer.

These tests are skipped automatically when reportlab is not installed.

PDF content streams are zlib-compressed, so tests verify correctness by
asserting that render() returns a valid PDF (b"%PDF" header) without raising
exceptions, rather than searching raw bytes for text.
"""

import pytest

pytest.importorskip("reportlab", reason="reportlab not installed")

from chordpro.models import (
    BreakLine,
    Chorus,
    ChordLine,
    ChorusRef,
    CommentBox,
    CommentItalic,
    CommentLine,
    Highlight,
    LyricLine,
    NewPage,
    Segment,
    Song,
    SongMeta,
    Verse,
)
from chordpro.parser import build_chord_semi_to_name
from chordpro.renderers import PdfRenderer, render

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def song(*body):
    return Song(body=list(body))


def chord_line(*segs):
    return ChordLine(segments=list(segs))


def valid_pdf(result: bytes) -> bool:
    return isinstance(result, bytes) and result.startswith(b"%PDF")


# ---------------------------------------------------------------------------
# Basic output contract
# ---------------------------------------------------------------------------


class TestPdfRendererBasic:
    renderer = PdfRenderer()

    def test_returns_bytes(self):
        assert isinstance(self.renderer.render(Song()), bytes)

    def test_empty_song_is_valid_pdf(self):
        assert valid_pdf(self.renderer.render(Song()))

    def test_song_with_content_is_valid_pdf(self):
        assert valid_pdf(self.renderer.render(song(LyricLine("Amazing grace"))))

    def test_render_dispatch(self):
        result = render(song(LyricLine("hi")), format="pdf")
        assert valid_pdf(result)

    def test_song_with_content_larger_than_empty(self):
        empty = self.renderer.render(Song())
        with_content = self.renderer.render(song(LyricLine("Amazing grace")))
        assert len(with_content) > len(empty)


# ---------------------------------------------------------------------------
# Metadata header — verify no exceptions, valid PDF
# ---------------------------------------------------------------------------


class TestPdfRendererMetadata:
    renderer = PdfRenderer()

    def test_title(self):
        s = Song(meta=SongMeta(title="Amazing Grace"))
        assert valid_pdf(self.renderer.render(s))

    def test_artist(self):
        s = Song(meta=SongMeta(artist=["John Newton"]))
        assert valid_pdf(self.renderer.render(s))

    def test_key(self):
        s = Song(meta=SongMeta(key=["G"]))
        assert valid_pdf(self.renderer.render(s))

    def test_capo(self):
        s = Song(meta=SongMeta(capo="2"))
        assert valid_pdf(self.renderer.render(s))

    def test_subtitle(self):
        s = Song(meta=SongMeta(subtitle=["Hymn"]))
        assert valid_pdf(self.renderer.render(s))

    def test_tempo_and_time(self):
        s = Song(meta=SongMeta(tempo=["120"], time=["4/4"]))
        assert valid_pdf(self.renderer.render(s))

    def test_full_metadata(self):
        s = Song(
            meta=SongMeta(
                title="Amazing Grace",
                subtitle=["Hymn"],
                artist=["John Newton"],
                key=["G"],
                capo="2",
                tempo=["80"],
                time=["3/4"],
            )
        )
        assert valid_pdf(self.renderer.render(s))


# ---------------------------------------------------------------------------
# Body lines — verify no exceptions, valid PDF
# ---------------------------------------------------------------------------


class TestPdfRendererLines:
    renderer = PdfRenderer()

    def test_lyric_line(self):
        assert valid_pdf(self.renderer.render(song(LyricLine("Amazing grace"))))

    def test_comment_line(self):
        assert valid_pdf(self.renderer.render(song(CommentLine("A note"))))

    def test_comment_italic(self):
        assert valid_pdf(self.renderer.render(song(CommentItalic("softer"))))

    def test_comment_box(self):
        assert valid_pdf(self.renderer.render(song(CommentBox("boxed"))))

    def test_highlight(self):
        assert valid_pdf(self.renderer.render(song(Highlight("important"))))

    def test_chorus_ref_default(self):
        assert valid_pdf(self.renderer.render(song(ChorusRef())))

    def test_chorus_ref_custom_label(self):
        assert valid_pdf(self.renderer.render(song(ChorusRef(label="Chorus 2"))))

    def test_break_line(self):
        assert valid_pdf(self.renderer.render(song(BreakLine())))

    def test_new_page(self):
        result = self.renderer.render(
            song(LyricLine("page one"), NewPage(), LyricLine("page two"))
        )
        assert valid_pdf(result)

    def test_chord_line(self):
        cl = chord_line(Segment("G", "Amazing"))
        assert valid_pdf(self.renderer.render(song(cl)))

    def test_chord_line_lyric_only_segment(self):
        cl = chord_line(Segment(None, "no chord"))
        assert valid_pdf(self.renderer.render(song(cl)))

    def test_chord_line_empty_lyric(self):
        cl = chord_line(Segment("G", ""))
        assert valid_pdf(self.renderer.render(song(cl)))

    def test_chord_line_multiple_segments(self):
        cl = chord_line(
            Segment("G", "Amaz"), Segment("D", "ing"), Segment("Em", "grace")
        )
        assert valid_pdf(self.renderer.render(song(cl)))

    def test_chord_line_notation_applied(self):
        semi = build_chord_semi_to_name("latin")
        cl = chord_line(Segment("C", "Do"))
        assert valid_pdf(self.renderer.render(song(cl), semi))


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


class TestPdfRendererSections:
    renderer = PdfRenderer()

    def test_verse_section(self):
        v = Verse(label="Verse 1", lines=[LyricLine("Amazing grace")])
        assert valid_pdf(self.renderer.render(song(v)))

    def test_chorus_section(self):
        c = Chorus(label="Chorus", lines=[LyricLine("How sweet the sound")])
        assert valid_pdf(self.renderer.render(song(c)))

    def test_section_with_chord_lines(self):
        v = Verse(
            label="Verse 1",
            lines=[chord_line(Segment("G", "Amazing"), Segment("D", "grace"))],
        )
        assert valid_pdf(self.renderer.render(song(v)))

    def test_multiple_sections(self):
        s = song(
            Verse(label="Verse 1", lines=[LyricLine("line one")]),
            Chorus(label="Chorus", lines=[LyricLine("chorus line")]),
        )
        assert valid_pdf(self.renderer.render(s))

    def test_unlabelled_section(self):
        v = Verse(label="", lines=[LyricLine("no label")])
        assert valid_pdf(self.renderer.render(song(v)))


# ---------------------------------------------------------------------------
# Output size grows with content (smoke test)
# ---------------------------------------------------------------------------


def test_pdf_grows_with_sections():
    renderer = PdfRenderer()
    small = renderer.render(song(LyricLine("hi")))
    big = renderer.render(
        song(
            Verse(
                label="Verse 1",
                lines=[
                    chord_line(Segment("G", "Amazing"), Segment("D", "grace")),
                    chord_line(Segment("Em", "How sweet"), Segment("C", "the sound")),
                    LyricLine("That saved a wretch like me"),
                ],
            ),
            Chorus(label="Chorus", lines=[LyricLine("Chorus line here")]),
        )
    )
    assert len(big) > len(small)


# ---------------------------------------------------------------------------
# ImportError when reportlab missing (unit test via monkeypatch)
# ---------------------------------------------------------------------------


def test_import_error_message(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "reportlab" or name.startswith("reportlab."):
            raise ImportError("No module named 'reportlab'")
        return real_import(name, *args, **kwargs)

    renderer = PdfRenderer()
    monkeypatch.setattr(builtins, "__import__", mock_import)
    with pytest.raises(ImportError, match="reportlab"):
        renderer.render(Song())
