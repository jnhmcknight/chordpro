"""Words split by chords: where a chord, wider than its syllable, pulls a
word apart, the gap is filled with hyphens."""

import pytest
from reportlab.pdfbase.pdfmetrics import stringWidth

from chordpro.models import ChordLine, Segment, Song
from chordpro.parser import parse
from chordpro.renderers import HtmlRenderer, PdfRenderer, TextRenderer
from chordpro.renderers.pdf import _ChordLineFlowable
from chordpro.renderers.text import hyphens


def chord_line(*segs):
    return ChordLine(segments=list(segs))


def first_line(source: str) -> ChordLine:
    return next(item for item in parse(source).body if isinstance(item, ChordLine))


class TestSplitsWord:
    @pytest.mark.parametrize(
        ("source", "splits"),
        [
            # "A" and "ma" stop within "Amazing"; "zing grace" ends a word
            ("[D]A[G]ma[C]zing grace", [False, True, True, False]),
            # Lyrics alone before a chord split the word too
            ("Hal[C]le[G]lujah", [True, True, False]),
            ("don[Em]'t [A]stop", [True, False, False]),
            # Between words, or a hyphen of the author's own: no split
            ("[G]Amazing [C]grace", [False, False, False]),
            ("Hal[C]le[G]lu-[D]jah", [True, True, False, False]),
            # Punctuation after a chord isn't the rest of a word
            ("[G]grace[C], how", [False, False, False]),
            # Chords alone, or the last segment
            ("[G] [C]", [False, False, False]),
        ],
    )
    def test_where_words_split(self, source, splits):
        line = first_line(source)
        assert [line.splits_word(i) for i in range(len(line.segments))] == splits

    def test_past_the_end(self):
        assert not chord_line(Segment("G", "word")).splits_word(5)


class TestText:
    def test_hyphens(self):
        assert [hyphens(n) for n in range(6)] == ["", "-", "- ", "- -", "- - ", "- - -"]

    def test_a_wide_chord_leaves_hyphens(self):
        result = TextRenderer().render(
            Song(body=[first_line("[D]A[Gmaj7sus4]ma[C]zing grace")])
        )
        chords, lyrics = result.splitlines()
        assert lyrics == "A-ma- - - - zing grace"
        # Each chord still over its syllable
        assert chords.index("Gmaj7sus4") == lyrics.index("ma")
        assert chords.index("C") == lyrics.index("zing")

    def test_a_narrow_chord_leaves_the_word_whole(self):
        result = TextRenderer().render(Song(body=[first_line("Amaz[G]ing grace")]))
        assert result.splitlines()[1] == "Amazing grace"

    def test_between_words_unchanged(self):
        result = TextRenderer().render(Song(body=[first_line("[Em]Amazing [G]grace")]))
        assert result.splitlines()[1] == "Amazing  grace"


class TestHtml:
    def test_a_split_unit_has_a_hyphen_slot(self):
        html = HtmlRenderer()._render_chord_line(
            first_line("[D]A[G]mazing grace"), None
        )
        assert (
            '<span class="cp-unit cp-split"><span class="cp-chord" data-chord="D">D</span>'
            '<span class="cp-lyric-row"><span class="cp-lyric">A</span>'
            '<span class="cp-hyphen" aria-hidden="true"></span></span></span>'
        ) in html
        # The rest of the word, and the units between words, as before
        assert (
            '<span class="cp-unit"><span class="cp-chord" data-chord="G">G</span>'
            in html
        )
        assert html.count("cp-hyphen") == 1

    def test_no_slot_between_words(self):
        html = HtmlRenderer()._render_chord_line(
            first_line("[G]Amazing [C]grace"), None
        )
        assert "cp-split" not in html and "cp-hyphen" not in html


class TestPdf:
    renderer = PdfRenderer()

    def layout(self, source: str):
        laid_out = _ChordLineFlowable(
            chord_line=first_line(source),
            semi_to_name=None,
            chord_font=self.renderer.CHORD_FONT,
            chord_size=self.renderer.CHORD_SIZE,
            lyric_font=self.renderer.LYRIC_FONT,
            lyric_size=self.renderer.LYRIC_SIZE,
            chord_color=None,
        )._layout()
        # A line that starts with a chord has an empty segment before it
        return [seg for seg in laid_out if seg[0] or seg[1]]

    def test_a_wide_chord_leaves_hyphens(self):
        (_, a, _, a_gap, a_hyphens), (_, ma, _, ma_gap, ma_hyphens), *_ = self.layout(
            "[D]A[Gmaj7sus4/F#]ma[C]zing grace"
        )
        assert (a, ma) == ("A", "ma")
        assert a_gap > 0 and a_hyphens == 1
        # A wider gap, more of them
        assert ma_gap > a_gap and ma_hyphens > 1

    def test_no_pad_within_a_word_a_chord_fits_over(self):
        # "Amaz" is wider than "G": "ing" follows straight on
        (_, lyric, width, gap, count), _ = self.layout("[G]Amaz[D]ing grace")
        assert lyric == "Amaz" and (gap, count) == (0, 0)
        assert width == pytest.approx(
            stringWidth("Amaz", self.renderer.LYRIC_FONT, self.renderer.LYRIC_SIZE)
        )

    def test_lyrics_alone_within_a_word(self):
        (_, lyric, _, gap, count), *_ = self.layout("Hal[C]lelujah")
        assert lyric == "Hal" and (gap, count) == (0, 0)

    def test_between_words_unchanged(self):
        (_, _, width, gap, count), _ = self.layout("[G]Amazing [C]grace")
        assert (gap, count) == (0, 0) and width > 0

    def test_renders(self):
        song = parse("[D]A[Gmaj7sus4]ma[C]zing grace")
        assert self.renderer.render(song).startswith(b"%PDF")
