from __future__ import annotations

from ..models import (
    BreakLine,
    ChordLine,
    ChorusRef,
    CommentBox,
    CommentItalic,
    CommentLine,
    Highlight,
    LyricLine,
    NewPage,
    Song,
)
from ..parser import _convert_chord_root
from .base import BaseRenderer


class _ChordLineFlowable:
    """A reportlab Flowable that draws a chord-over-lyric line."""

    def __init__(
        self,
        segments,
        semi_to_name,
        chord_font: str,
        chord_size: float,
        lyric_font: str,
        lyric_size: float,
        chord_color,
        gap: float = 1,
        seg_pad: float = 4,
    ) -> None:
        from reportlab.platypus.flowables import Flowable

        # Dynamically subclass at runtime so reportlab is a lazy import.
        class _Inner(Flowable):
            pass

        self._flowable_cls = _Inner
        self.segments = segments
        self.semi_to_name = semi_to_name
        self.chord_font = chord_font
        self.chord_size = chord_size
        self.lyric_font = lyric_font
        self.lyric_size = lyric_size
        self.chord_color = chord_color
        self.gap = gap
        self.seg_pad = seg_pad
        self._instance = self._build()

    def _get_chord(self, seg) -> str | None:
        if seg.chord is None:
            return None
        return (
            _convert_chord_root(seg.chord, self.semi_to_name)
            if self.semi_to_name
            else seg.chord
        )

    def _build(self):
        from reportlab.pdfbase.pdfmetrics import stringWidth
        from reportlab.platypus.flowables import Flowable
        from reportlab.lib import colors

        outer = self

        class ChordLine(Flowable):
            def wrap(self, avail_w, avail_h):
                total_w = 0.0
                for seg in outer.segments:
                    chord = outer._get_chord(seg)
                    cw = (
                        stringWidth(chord, outer.chord_font, outer.chord_size)
                        if chord
                        else 0.0
                    )
                    lw = (
                        stringWidth(
                            seg.lyric or "", outer.lyric_font, outer.lyric_size
                        )
                        if seg.lyric
                        else 0.0
                    )
                    total_w += max(cw, lw) + outer.seg_pad
                self.width = total_w
                self.height = outer.chord_size + outer.gap + outer.lyric_size + 2
                return (total_w, self.height)

            def draw(self):
                from reportlab.pdfbase.pdfmetrics import stringWidth
                from reportlab.lib import colors as _colors

                lyric_y = 0.0
                chord_y = outer.lyric_size + outer.gap
                x = 0.0

                for seg in outer.segments:
                    chord = outer._get_chord(seg)
                    lyric = seg.lyric or ""
                    cw = (
                        stringWidth(chord, outer.chord_font, outer.chord_size)
                        if chord
                        else 0.0
                    )
                    lw = (
                        stringWidth(lyric, outer.lyric_font, outer.lyric_size)
                        if lyric
                        else 0.0
                    )
                    seg_w = max(cw, lw) + outer.seg_pad

                    if chord:
                        self.canv.setFont(outer.chord_font, outer.chord_size)
                        self.canv.setFillColor(outer.chord_color)
                        self.canv.drawString(x, chord_y, chord)

                    if lyric:
                        self.canv.setFont(outer.lyric_font, outer.lyric_size)
                        self.canv.setFillColor(_colors.black)
                        self.canv.drawString(x, lyric_y, lyric)

                    x += seg_w

        return ChordLine()

    def get(self):
        return self._instance


class PdfRenderer(BaseRenderer):
    """Renders a ``Song`` to PDF bytes.

    Requires the ``reportlab`` package (``pip install chordpro[pdf]``).

    Layout
    ------
    * Song title, subtitle, artist, and key are printed as a header.
    * Sections are labelled in bold.
    * Chord lines use the classic two-row layout: chords printed in blue
      directly above the corresponding lyric syllables, columns aligned by
      segment width.
    * Comments are italicised; highlights are bold.
    * ``{new_page}`` emits a hard page break.

    The return value is a ``bytes`` object containing a valid PDF document.
    """

    # --- Tuneable defaults -------------------------------------------------
    PAGE_SIZE = None  # set to e.g. A4 to override; None → letter
    MARGIN = None  # inches; None → 1 inch
    COMPRESS = True  # set False to disable PDF stream compression (useful in tests)

    TITLE_FONT = "Helvetica-Bold"
    TITLE_SIZE = 16

    SUBTITLE_FONT = "Helvetica"
    SUBTITLE_SIZE = 12

    ARTIST_FONT = "Helvetica-Oblique"
    ARTIST_SIZE = 12

    META_FONT = "Helvetica"
    META_SIZE = 10

    SECTION_LABEL_FONT = "Helvetica-Bold"
    SECTION_LABEL_SIZE = 10

    CHORD_FONT = "Helvetica-Bold"
    CHORD_SIZE = 9

    LYRIC_FONT = "Helvetica"
    LYRIC_SIZE = 11

    COMMENT_FONT = "Helvetica-Oblique"
    COMMENT_SIZE = 10

    CHORUS_REF_FONT = "Helvetica-Oblique"
    CHORUS_REF_SIZE = 10

    # -----------------------------------------------------------------------

    def render(self, song: Song, semi_to_name: dict | None = None) -> bytes:
        try:
            from io import BytesIO

            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.units import inch
            from reportlab.platypus import (
                PageBreak,
                Paragraph,
                SimpleDocTemplate,
                Spacer,
            )
            from reportlab.lib.styles import ParagraphStyle
        except ImportError:
            raise ImportError(
                "reportlab is required for PDF rendering. "
                "Install it with: pip install chordpro[pdf]"
            ) from None

        page_size = self.PAGE_SIZE or letter
        margin = (self.MARGIN or 1.0) * inch

        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=page_size,
            leftMargin=margin,
            rightMargin=margin,
            topMargin=margin,
            bottomMargin=margin,
            compress=1 if self.COMPRESS else 0,
        )

        chord_color = colors.HexColor("#1a56db")

        def para_style(name, font, size, **kw):
            return ParagraphStyle(name, fontName=font, fontSize=size, **kw)

        title_style = para_style("CPTitle", self.TITLE_FONT, self.TITLE_SIZE, spaceAfter=2)
        subtitle_style = para_style("CPSubtitle", self.SUBTITLE_FONT, self.SUBTITLE_SIZE, spaceAfter=2)
        artist_style = para_style("CPArtist", self.ARTIST_FONT, self.ARTIST_SIZE, spaceAfter=2)
        meta_style = para_style("CPMeta", self.META_FONT, self.META_SIZE, spaceAfter=2)
        section_label_style = para_style(
            "CPSectionLabel", self.SECTION_LABEL_FONT, self.SECTION_LABEL_SIZE,
            spaceBefore=8, spaceAfter=2,
        )
        lyric_style = para_style("CPLyric", self.LYRIC_FONT, self.LYRIC_SIZE, spaceAfter=0)
        comment_style = para_style("CPComment", self.COMMENT_FONT, self.COMMENT_SIZE, spaceAfter=2)
        chorus_ref_style = para_style("CPChorusRef", self.CHORUS_REF_FONT, self.CHORUS_REF_SIZE, spaceAfter=2)

        story = []

        # --- Metadata header ---
        header = []
        if song.meta.title:
            header.append(Paragraph(self._esc(song.meta.title), title_style))
        for sub in song.meta.subtitle:
            header.append(Paragraph(self._esc(sub), subtitle_style))
        if song.meta.artist:
            header.append(Paragraph(self._esc(", ".join(song.meta.artist)), artist_style))
        meta_parts = []
        if song.meta.key:
            meta_parts.append("Key: " + ", ".join(song.meta.key))
        if song.meta.tempo:
            meta_parts.append("Tempo: " + ", ".join(song.meta.tempo))
        if song.meta.time:
            meta_parts.append("Time: " + ", ".join(song.meta.time))
        if song.meta.capo:
            meta_parts.append("Capo: " + song.meta.capo)
        if meta_parts:
            header.append(Paragraph(self._esc("  |  ".join(meta_parts)), meta_style))
        if header:
            story.extend(header)
            story.append(Spacer(1, 0.2 * inch))

        # --- Body ---
        for item in song.body:
            if hasattr(item, "lines"):
                self._append_section(
                    story, item, semi_to_name,
                    section_label_style, lyric_style, comment_style, chorus_ref_style,
                    chord_color,
                )
            else:
                flowable = self._line_to_flowable(
                    item, semi_to_name,
                    lyric_style, comment_style, chorus_ref_style,
                    chord_color,
                )
                if flowable is not None:
                    story.append(flowable)

        doc.build(story)
        return buf.getvalue()

    # -----------------------------------------------------------------------

    @staticmethod
    def _esc(text: str) -> str:
        """Escape text for use in a reportlab Paragraph."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def _chord_line_flowable(self, chord_line, semi_to_name, chord_color):
        return _ChordLineFlowable(
            segments=chord_line.segments,
            semi_to_name=semi_to_name,
            chord_font=self.CHORD_FONT,
            chord_size=self.CHORD_SIZE,
            lyric_font=self.LYRIC_FONT,
            lyric_size=self.LYRIC_SIZE,
            chord_color=chord_color,
        ).get()

    def _line_to_flowable(self, line, semi_to_name, lyric_style, comment_style, chorus_ref_style, chord_color):
        from reportlab.platypus import PageBreak, Paragraph, Spacer
        from reportlab.lib.units import inch

        if isinstance(line, ChordLine):
            return self._chord_line_flowable(line, semi_to_name, chord_color)
        if isinstance(line, LyricLine):
            return Paragraph(self._esc(line.text) or "&nbsp;", lyric_style)
        if isinstance(line, BreakLine):
            return Spacer(1, self.LYRIC_SIZE * 0.8)
        if isinstance(line, (CommentLine, CommentItalic, CommentBox)):
            return Paragraph(self._esc(line.text), comment_style)
        if isinstance(line, Highlight):
            from reportlab.lib.styles import ParagraphStyle
            highlight_style = ParagraphStyle(
                "CPHighlight",
                fontName="Helvetica-Bold",
                fontSize=self.LYRIC_SIZE,
                spaceAfter=0,
            )
            return Paragraph(self._esc(line.text), highlight_style)
        if isinstance(line, ChorusRef):
            label = line.label or "Chorus"
            return Paragraph(f"[{self._esc(label)}]", chorus_ref_style)
        if isinstance(line, NewPage):
            return PageBreak()
        return None

    def _append_section(
        self, story, section, semi_to_name,
        section_label_style, lyric_style, comment_style, chorus_ref_style,
        chord_color,
    ):
        from reportlab.platypus import Paragraph

        if section.label:
            story.append(Paragraph(self._esc(section.label), section_label_style))
        for line in section.lines:
            flowable = self._line_to_flowable(
                line, semi_to_name,
                lyric_style, comment_style, chorus_ref_style,
                chord_color,
            )
            if flowable is not None:
                story.append(flowable)
