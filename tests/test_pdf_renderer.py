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
from chordpro.renderers import PdfRenderer, render, render_many

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


# ---------------------------------------------------------------------------
# PdfRenderer.render_many — multi-song PDF
# ---------------------------------------------------------------------------


class TestPdfRendererMany:
    renderer = PdfRenderer()

    def _two_songs(self):
        return [
            Song(
                meta=SongMeta(title="Song One"),
                body=[LyricLine("Amazing grace")],
            ),
            Song(
                meta=SongMeta(title="Song Two"),
                body=[LyricLine("How sweet the sound")],
            ),
        ]

    def test_returns_bytes(self):
        assert isinstance(self.renderer.render_many(self._two_songs()), bytes)

    def test_valid_pdf(self):
        assert valid_pdf(self.renderer.render_many(self._two_songs()))

    def test_render_many_dispatch(self):
        result = render_many(self._two_songs(), format="pdf")
        assert valid_pdf(result)

    def test_larger_than_single_song(self):
        single = self.renderer.render(self._two_songs()[0])
        combined = self.renderer.render_many(self._two_songs())
        assert len(combined) > len(single)

    def test_three_songs_larger_than_two(self):
        three = self._two_songs() + [
            Song(meta=SongMeta(title="Song Three"), body=[LyricLine("extra")])
        ]
        two = self.renderer.render_many(self._two_songs())
        result = self.renderer.render_many(three)
        assert len(result) > len(two)

    def test_single_song_is_valid_pdf(self):
        assert valid_pdf(self.renderer.render_many([self._two_songs()[0]]))

    def test_empty_list_is_valid_pdf(self):
        assert valid_pdf(self.renderer.render_many([]))

    def test_songs_with_sections(self):
        songs = [
            song(Verse(label="Verse 1", lines=[chord_line(Segment("G", "Amazing"))])),
            song(Chorus(label="Chorus", lines=[LyricLine("How sweet")])),
        ]
        assert valid_pdf(self.renderer.render_many(songs))

    def test_notation_applied(self):
        semi = build_chord_semi_to_name("latin")
        songs = [song(chord_line(Segment("C", "Do"))), song(LyricLine("second"))]
        assert valid_pdf(self.renderer.render_many(songs, semi))

    def test_songs_with_new_page_directives(self):
        # NewPage within a song should not interfere with the inter-song PageBreak
        songs = [
            song(LyricLine("page one"), NewPage(), LyricLine("page two")),
            song(LyricLine("song two")),
        ]
        assert valid_pdf(self.renderer.render_many(songs))


# ---------------------------------------------------------------------------
# ascii_accidentals in PdfRenderer
# ---------------------------------------------------------------------------


class TestPdfRendererAsciiAccidentals:
    def test_ascii_accidentals_true_produces_valid_pdf(self):
        renderer = PdfRenderer(ascii_accidentals=True)
        # Unicode sharp in chord — renderer should convert it internally
        result = renderer.render(song(chord_line(Segment("F♯", "word"))))
        assert valid_pdf(result)

    def test_ascii_accidentals_with_notation(self):
        renderer = PdfRenderer(ascii_accidentals=True)
        semi = build_chord_semi_to_name("standard")
        result = renderer.render(song(chord_line(Segment("Bb", "word"))), semi)
        assert valid_pdf(result)


# ---------------------------------------------------------------------------
# Unknown line types in PdfRenderer._line_to_flowable
# ---------------------------------------------------------------------------


class TestPdfRendererUnknownLines:
    def test_unknown_line_type_is_skipped(self):
        from chordpro.models import GridOn

        # GridOn is not handled by _line_to_flowable; result should still be a valid PDF
        result = PdfRenderer().render(song(GridOn()))
        assert valid_pdf(result)


# ---------------------------------------------------------------------------
# Unicode font helpers
# ---------------------------------------------------------------------------


class TestFindUnicodeFont:
    def test_returns_none_when_no_candidates(self, monkeypatch):
        monkeypatch.setattr(PdfRenderer, "_UNICODE_FONT_CANDIDATES", ())
        assert PdfRenderer._find_unicode_font() is None

    def test_returns_first_existing_path(self, tmp_path, monkeypatch):
        font = tmp_path / "MyFont.ttf"
        font.write_bytes(b"")
        monkeypatch.setattr(PdfRenderer, "_UNICODE_FONT_CANDIDATES", (str(font),))
        assert PdfRenderer._find_unicode_font() == str(font)

    def test_skips_missing_paths(self, tmp_path, monkeypatch):
        missing = str(tmp_path / "missing.ttf")
        present = tmp_path / "present.ttf"
        present.write_bytes(b"")
        monkeypatch.setattr(
            PdfRenderer, "_UNICODE_FONT_CANDIDATES", (missing, str(present))
        )
        assert PdfRenderer._find_unicode_font() == str(present)


class TestDeriveVariant:
    def test_bold_dash_suffix(self, tmp_path):
        regular = tmp_path / "MyFont.ttf"
        bold = tmp_path / "MyFont-Bold.ttf"
        regular.write_bytes(b"")
        bold.write_bytes(b"")
        assert PdfRenderer._derive_font_variant(str(regular), bold=True) == str(bold)

    def test_bold_bd_suffix(self, tmp_path):
        regular = tmp_path / "arial.ttf"
        bold = tmp_path / "arialbd.ttf"
        regular.write_bytes(b"")
        bold.write_bytes(b"")
        assert PdfRenderer._derive_font_variant(str(regular), bold=True) == str(bold)

    def test_italic_oblique_suffix(self, tmp_path):
        regular = tmp_path / "MyFont.ttf"
        oblique = tmp_path / "MyFont-Oblique.ttf"
        regular.write_bytes(b"")
        oblique.write_bytes(b"")
        assert PdfRenderer._derive_font_variant(str(regular), italic=True) == str(oblique)

    def test_italic_italic_suffix(self, tmp_path):
        regular = tmp_path / "MyFont.ttf"
        italic = tmp_path / "MyFont-Italic.ttf"
        regular.write_bytes(b"")
        italic.write_bytes(b"")
        assert PdfRenderer._derive_font_variant(str(regular), italic=True) == str(italic)

    def test_strips_regular_before_deriving(self, tmp_path):
        regular = tmp_path / "NotoSans-Regular.ttf"
        bold = tmp_path / "NotoSans-Bold.ttf"
        regular.write_bytes(b"")
        bold.write_bytes(b"")
        assert PdfRenderer._derive_font_variant(str(regular), bold=True) == str(bold)

    def test_returns_none_when_no_variant_found(self, tmp_path):
        regular = tmp_path / "MyFont.ttf"
        regular.write_bytes(b"")
        assert PdfRenderer._derive_font_variant(str(regular), bold=True) is None


class TestSetupUnicodeFont:
    """Tests for _setup_unicode_font().

    TTFont and pdfmetrics.registerFont are mocked so no real font file is
    needed; the mocks allow us to verify that the renderer's font name
    attributes are remapped correctly.
    """

    def _patch_reportlab(self, monkeypatch, registered=None):
        """Replace TTFont constructor and registerFont with lightweight stubs."""
        if registered is None:
            registered = []
        monkeypatch.setattr(
            "reportlab.pdfbase.ttfonts.TTFont",
            lambda name, path: name,
        )
        monkeypatch.setattr(
            "reportlab.pdfbase.pdfmetrics.registerFont",
            lambda f: registered.append(f),
        )
        return registered

    def test_no_font_found_keeps_helvetica_defaults(self, monkeypatch):
        monkeypatch.setattr(PdfRenderer, "_UNICODE_FONT_CANDIDATES", ())
        renderer = PdfRenderer()
        renderer._setup_unicode_font()
        assert renderer.LYRIC_FONT == "Helvetica"
        assert renderer.TITLE_FONT == "Helvetica-Bold"
        assert renderer.ARTIST_FONT == "Helvetica-Oblique"

    def test_remaps_all_font_attributes(self, tmp_path, monkeypatch):
        regular = tmp_path / "MyFont.ttf"
        bold = tmp_path / "MyFont-Bold.ttf"
        oblique = tmp_path / "MyFont-Oblique.ttf"
        for f in (regular, bold, oblique):
            f.write_bytes(b"")
        self._patch_reportlab(monkeypatch)

        renderer = PdfRenderer()
        renderer.UNICODE_FONT_PATH = str(regular)
        renderer._setup_unicode_font()

        assert renderer.LYRIC_FONT == "CPSans"
        assert renderer.TITLE_FONT == "CPSans-Bold"
        assert renderer.SUBTITLE_FONT == "CPSans"
        assert renderer.ARTIST_FONT == "CPSans-Italic"
        assert renderer.META_FONT == "CPSans"
        assert renderer.SECTION_LABEL_FONT == "CPSans-Bold"
        assert renderer.CHORD_FONT == "CPSans-Bold"
        assert renderer.COMMENT_FONT == "CPSans-Italic"
        assert renderer.CHORUS_REF_FONT == "CPSans-Italic"

    def test_no_variants_falls_back_to_regular(self, tmp_path, monkeypatch):
        regular = tmp_path / "MyFont.ttf"
        regular.write_bytes(b"")
        self._patch_reportlab(monkeypatch)

        renderer = PdfRenderer()
        renderer.UNICODE_FONT_PATH = str(regular)
        renderer._setup_unicode_font()

        assert renderer.TITLE_FONT == "CPSans"
        assert renderer.ARTIST_FONT == "CPSans"
        assert renderer.LYRIC_FONT == "CPSans"

    def test_registers_three_fonts_when_variants_exist(self, tmp_path, monkeypatch):
        regular = tmp_path / "MyFont.ttf"
        bold = tmp_path / "MyFont-Bold.ttf"
        oblique = tmp_path / "MyFont-Oblique.ttf"
        for f in (regular, bold, oblique):
            f.write_bytes(b"")
        registered = self._patch_reportlab(monkeypatch)

        renderer = PdfRenderer()
        renderer.UNICODE_FONT_PATH = str(regular)
        renderer._setup_unicode_font()

        assert registered == ["CPSans", "CPSans-Bold", "CPSans-Italic"]

    def test_explicit_bold_italic_paths_used(self, tmp_path, monkeypatch):
        for name in ("regular.ttf", "bold.ttf", "italic.ttf"):
            (tmp_path / name).write_bytes(b"")
        registered = self._patch_reportlab(monkeypatch)

        renderer = PdfRenderer()
        renderer.UNICODE_FONT_PATH = str(tmp_path / "regular.ttf")
        renderer.UNICODE_BOLD_FONT_PATH = str(tmp_path / "bold.ttf")
        renderer.UNICODE_ITALIC_FONT_PATH = str(tmp_path / "italic.ttf")
        renderer._setup_unicode_font()

        assert registered == ["CPSans", "CPSans-Bold", "CPSans-Italic"]

    def test_corrupt_font_keeps_helvetica_defaults(self, tmp_path, monkeypatch):
        # Don't mock TTFont — let it fail on a non-TTF file.
        corrupt = tmp_path / "corrupt.ttf"
        corrupt.write_bytes(b"not a real font")
        monkeypatch.setattr(PdfRenderer, "_UNICODE_FONT_CANDIDATES", (str(corrupt),))

        renderer = PdfRenderer()
        renderer._setup_unicode_font()

        assert renderer.LYRIC_FONT == "Helvetica"
        assert renderer.TITLE_FONT == "Helvetica-Bold"

    def test_render_calls_setup_unicode_font(self, monkeypatch):
        """render() must call _setup_unicode_font() before building the document."""
        calls = []
        monkeypatch.setattr(PdfRenderer, "_setup_unicode_font", lambda self: calls.append(1))
        PdfRenderer().render(Song())
        assert calls

    def test_render_many_calls_setup_unicode_font(self, monkeypatch):
        """render_many() must call _setup_unicode_font() before building."""
        calls = []
        monkeypatch.setattr(PdfRenderer, "_setup_unicode_font", lambda self: calls.append(1))
        PdfRenderer().render_many([Song()])
        assert calls
