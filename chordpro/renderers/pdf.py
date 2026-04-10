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
        ascii_accidentals: bool = False,
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
        self.ascii_accidentals = ascii_accidentals
        self._instance = self._build()

    def _get_chord(self, seg) -> str | None:
        from ..constants import FLAT, SHARP

        if seg.chord is None:
            return None
        chord = (
            _convert_chord_root(seg.chord, self.semi_to_name)
            if self.semi_to_name
            else seg.chord
        )
        if self.ascii_accidentals:
            chord = chord.replace(SHARP, "#").replace(FLAT, "b")
        return chord

    def _build(self):
        from reportlab.pdfbase.pdfmetrics import stringWidth
        from reportlab.platypus.flowables import Flowable

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
                        stringWidth(seg.lyric or "", outer.lyric_font, outer.lyric_size)
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
    MARGIN = None  # inches; None → 0.5 inch
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

    # --- Unicode font support -----------------------------------------------
    # The built-in Helvetica fonts are Latin-1 only and cannot render Unicode
    # musical symbols such as ♭, ♯, and ♮.  Set UNICODE_FONT_PATH to a
    # TTF/OTF file that covers those code points (e.g. DejaVu Sans, Noto Sans)
    # to enable full Unicode rendering.  When None, common system locations are
    # searched automatically before falling back to Helvetica.
    UNICODE_FONT_PATH: str | None = None
    UNICODE_BOLD_FONT_PATH: str | None = None
    UNICODE_ITALIC_FONT_PATH: str | None = None

    # Ordered list of paths searched when UNICODE_FONT_PATH is None.
    _UNICODE_FONT_CANDIDATES: tuple[str, ...] = (
        # Linux — DejaVu Sans (covers ♭ ♯ ♮)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        # macOS — Homebrew DejaVu
        "/opt/homebrew/opt/font-dejavu/share/fonts/truetype/DejaVuSans.ttf",
        "/usr/local/opt/font-dejavu/share/fonts/truetype/DejaVuSans.ttf",
        # macOS — Arial Unicode MS (ships with Microsoft Office / macOS extras)
        "/Library/Fonts/Arial Unicode MS.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode MS.ttf",
        # Windows — Arial
        "C:\\Windows\\Fonts\\arial.ttf",
        # Noto Sans (Fedora / Ubuntu / Arch variants)
        "/usr/share/fonts/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/google-noto/NotoSans-Regular.ttf",
    )

    # -----------------------------------------------------------------------

    def render(self, song: Song, semi_to_name: dict | None = None) -> bytes:
        self._setup_unicode_font()
        buf, doc = self._make_doc()
        styles, chord_color = self._make_styles()
        story = self._build_song_story(song, semi_to_name, styles, chord_color)
        story = self._maybe_two_column(story, doc)
        footer_cb = self._make_footer_cb(song.meta.copyright)
        doc.build(story, onFirstPage=footer_cb, onLaterPages=footer_cb)
        return buf.getvalue()

    def render_many(self, songs: list[Song], semi_to_name: dict | None = None) -> bytes:
        """Render multiple *songs* into a single PDF.  Each song starts on a new page."""
        from reportlab.platypus import PageBreak, Flowable

        class _SetCopyright(Flowable):
            """Zero-size flowable that records the current song's copyright on the canvas."""

            def __init__(self, copyright_texts):
                super().__init__()
                self.copyright_texts = copyright_texts
                self.width = 0
                self.height = 0

            def draw(self):
                self.canv._sbp_current_copyright = self.copyright_texts

        self._setup_unicode_font()
        buf, doc = self._make_doc()
        styles, chord_color = self._make_styles()
        story = []
        for i, song in enumerate(songs):
            if i > 0:
                story.append(PageBreak())
            story.append(_SetCopyright(song.meta.copyright))
            story.extend(
                self._build_song_story(song, semi_to_name, styles, chord_color)
            )
        footer_cb = self._make_footer_cb_dynamic()
        doc.build(story, onFirstPage=footer_cb, onLaterPages=footer_cb)
        return buf.getvalue()

    def _make_footer_cb(self, copyright_texts: list[str]):
        """Return a reportlab page callback that draws copyright text at the page bottom."""
        font = self.META_FONT
        size = max(self.META_SIZE - 2, 6)
        margin_in = self.MARGIN or 0.5

        def draw_footer(canvas, doc):
            if not copyright_texts:
                return
            from reportlab.lib import colors
            from reportlab.lib.units import inch

            canvas.saveState()
            canvas.setFont(font, size)
            canvas.setFillColor(colors.grey)
            text = " | ".join(copyright_texts)
            canvas.drawString(margin_in * inch, margin_in * 0.35 * inch, text)
            canvas.restoreState()

        return draw_footer

    def _make_footer_cb_dynamic(self):
        """Return a page callback that draws only the current song's copyright per page.

        Reads the copyright set by the ``_SetCopyright`` flowable rendered earlier on
        the same page, so multi-song PDFs show each song's own copyright rather than
        every song's copyright on every page.
        """
        font = self.META_FONT
        size = max(self.META_SIZE - 2, 6)
        margin_in = self.MARGIN or 0.5

        def draw_footer(canvas, doc):
            copyright_texts = getattr(canvas, "_sbp_current_copyright", [])
            if not copyright_texts:
                return
            from reportlab.lib import colors
            from reportlab.lib.units import inch

            canvas.saveState()
            canvas.setFont(font, size)
            canvas.setFillColor(colors.grey)
            text = " | ".join(copyright_texts)
            canvas.drawString(margin_in * inch, margin_in * 0.35 * inch, text)
            canvas.restoreState()

        return draw_footer

    # -----------------------------------------------------------------------
    # Unicode font helpers
    # -----------------------------------------------------------------------

    def _setup_unicode_font(self) -> None:
        """Register a Unicode TTF font and remap all renderer font attributes.

        Called automatically by :meth:`render` and :meth:`render_many`.  Sets
        instance-level font name attributes so that :meth:`_make_styles` and
        the chord-line flowable pick up the TTF font instead of Helvetica.
        Has no effect if no suitable font file can be found.
        """
        import os
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        regular = self.UNICODE_FONT_PATH or self._find_unicode_font()
        if regular is None:
            return

        try:
            pdfmetrics.registerFont(TTFont("CPSans", regular))
        except Exception:
            return  # corrupt / unsupported file — keep Helvetica

        bold_path = self.UNICODE_BOLD_FONT_PATH or self._derive_font_variant(
            regular, bold=True
        )
        italic_path = self.UNICODE_ITALIC_FONT_PATH or self._derive_font_variant(
            regular, italic=True
        )

        bold_name = "CPSans"
        italic_name = "CPSans"

        if bold_path:
            try:
                pdfmetrics.registerFont(TTFont("CPSans-Bold", bold_path))
                bold_name = "CPSans-Bold"
            except Exception:
                pass

        if italic_path:
            try:
                pdfmetrics.registerFont(TTFont("CPSans-Italic", italic_path))
                italic_name = "CPSans-Italic"
            except Exception:
                pass

        self.TITLE_FONT = bold_name
        self.SUBTITLE_FONT = "CPSans"
        self.ARTIST_FONT = italic_name
        self.META_FONT = "CPSans"
        self.SECTION_LABEL_FONT = bold_name
        self.CHORD_FONT = bold_name
        self.LYRIC_FONT = "CPSans"
        self.COMMENT_FONT = italic_name
        self.CHORUS_REF_FONT = italic_name

    @classmethod
    def _find_unicode_font(cls) -> str | None:
        """Return the first candidate font path that exists on this system."""
        import os

        return next(
            (p for p in cls._UNICODE_FONT_CANDIDATES if os.path.isfile(p)), None
        )

    @staticmethod
    def _derive_font_variant(
        regular: str, *, bold: bool = False, italic: bool = False
    ) -> str | None:
        """Infer a bold or italic TTF path from the regular font path.

        Tries common naming conventions (DejaVu, Noto, Windows Arial) in the
        same directory as *regular*.  Returns *None* if no file is found.
        """
        import os

        stem, ext = os.path.splitext(regular)
        # Strip trailing "-Regular" so "NotoSans-Regular" → "NotoSans"
        base = stem[: -len("-Regular")] if stem.endswith("-Regular") else stem
        suffixes = ("-Bold", "bd", "b") if bold else ("-Oblique", "-Italic", "i")
        for suf in suffixes:
            candidate = base + suf + ext
            if os.path.isfile(candidate):
                return candidate
        return None

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _make_doc(self):
        """Create a BytesIO buffer and a SimpleDocTemplate for this renderer's settings."""
        try:
            from io import BytesIO
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate
        except ImportError:
            raise ImportError(
                "reportlab is required for PDF rendering. "
                "Install it with: pip install chordpro[pdf]"
            ) from None

        page_size = self.PAGE_SIZE or letter
        margin = (self.MARGIN or 0.5) * inch
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
        return buf, doc

    def _measure_height(self, flowables: list, avail_w: float, avail_h: float) -> float:
        """Estimate the total rendered height of *flowables* at *avail_w* width."""
        total = 0.0
        for f in flowables:
            try:
                _, h = f.wrap(avail_w, avail_h)
                total += h
                # Paragraph spaceBefore/spaceAfter live on the style object
                style = getattr(f, "style", None)
                if style is not None:
                    total += getattr(style, "spaceBefore", 0)
                    total += getattr(style, "spaceAfter", 0)
            except Exception:
                pass
        return total

    def _maybe_two_column(self, story: list, doc) -> list:
        """If *story* overflows one page, attempt a 2-column layout to keep it on one page.

        The header (everything up to and including the post-header Spacer) stays
        full-width; only the body sections are flowed into two columns, left
        column first.
        """
        from reportlab.lib.units import inch
        from reportlab.platypus import Spacer

        page_w, page_h = doc.pagesize
        avail_w = page_w - doc.leftMargin - doc.rightMargin
        avail_h = page_h - doc.topMargin - doc.bottomMargin

        if self._measure_height(story, avail_w, avail_h) <= avail_h:
            return story  # already fits on one page

        # Split at the first Spacer (the one appended after the metadata header)
        split_idx = 0
        for i, f in enumerate(story):
            if isinstance(f, Spacer):
                split_idx = i + 1
                break

        header_items = story[:split_idx]
        body_items = story[split_idx:]

        if not body_items:
            return story

        header_h = self._measure_height(header_items, avail_w, avail_h)
        remaining_h = avail_h - header_h

        col_gap = 0.2 * inch
        col_w = (avail_w - col_gap) / 2

        if self._measure_height(body_items, col_w, remaining_h) <= remaining_h:
            try:
                from reportlab.platypus.flowables import BalancedColumns

                bc = BalancedColumns(
                    body_items,
                    nCols=2,
                    needed=0,
                    innerPadding=col_gap / 2,
                )
                return header_items + [bc]
            except Exception:
                pass  # reportlab version doesn't support BalancedColumns

        return story  # can't fit in 2 columns either — let it flow normally

    def _make_styles(self):
        """Create and return (styles_dict, chord_color) for this renderer's settings."""
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle

        def para_style(name, font, size, **kw):
            return ParagraphStyle(name, fontName=font, fontSize=size, **kw)

        styles = {
            "title": para_style(
                "CPTitle", self.TITLE_FONT, self.TITLE_SIZE, spaceAfter=2
            ),
            "subtitle": para_style(
                "CPSubtitle", self.SUBTITLE_FONT, self.SUBTITLE_SIZE, spaceAfter=2
            ),
            "artist": para_style(
                "CPArtist", self.ARTIST_FONT, self.ARTIST_SIZE, spaceAfter=2
            ),
            "meta": para_style("CPMeta", self.META_FONT, self.META_SIZE, spaceAfter=2),
            "section_label": para_style(
                "CPSectionLabel",
                self.SECTION_LABEL_FONT,
                self.SECTION_LABEL_SIZE,
                spaceBefore=8,
                spaceAfter=2,
            ),
            "lyric": para_style(
                "CPLyric", self.LYRIC_FONT, self.LYRIC_SIZE, spaceAfter=0
            ),
            "comment": para_style(
                "CPComment", self.COMMENT_FONT, self.COMMENT_SIZE, spaceAfter=2
            ),
            "chorus_ref": para_style(
                "CPChorusRef", self.CHORUS_REF_FONT, self.CHORUS_REF_SIZE, spaceAfter=2
            ),
        }
        chord_color = colors.HexColor("#1a56db")
        return styles, chord_color

    def _build_song_story(
        self, song: Song, semi_to_name, styles: dict, chord_color
    ) -> list:
        """Build and return the list of reportlab flowables for a single song."""
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, Spacer

        story = []

        # --- Metadata header ---
        header = []
        if song.meta.title:
            header.append(Paragraph(self._esc(song.meta.title), styles["title"]))
        for sub in song.meta.subtitle:
            header.append(Paragraph(self._esc(sub), styles["subtitle"]))
        if song.meta.artist:
            header.append(
                Paragraph(self._esc(", ".join(song.meta.artist)), styles["artist"])
            )
        if song.meta.album:
            header.append(
                Paragraph(self._esc(", ".join(song.meta.album)), styles["meta"])
            )
        if song.meta.composer:
            header.append(
                Paragraph(self._esc(", ".join(song.meta.composer)), styles["meta"])
            )
        meta_parts = []
        if song.meta.key:
            meta_parts.append("Key: " + ", ".join(song.meta.key))
        if song.meta.time:
            meta_parts.append("Time: " + ", ".join(song.meta.time))
        if song.meta.tempo:
            meta_parts.append("Tempo: " + ", ".join(song.meta.tempo))
        if song.meta.capo:
            meta_parts.append("Capo: " + song.meta.capo)
        if meta_parts:
            header.append(
                Paragraph(self._esc("  |  ".join(meta_parts)), styles["meta"])
            )
        if header:
            story.extend(header)
            story.append(Spacer(1, 0.2 * inch))

        # --- Body ---
        for item in song.body:
            if hasattr(item, "lines"):
                self._append_section(
                    story,
                    item,
                    semi_to_name,
                    styles["section_label"],
                    styles["lyric"],
                    styles["comment"],
                    styles["chorus_ref"],
                    chord_color,
                )
            else:
                flowable = self._line_to_flowable(
                    item,
                    semi_to_name,
                    styles["lyric"],
                    styles["comment"],
                    styles["chorus_ref"],
                    chord_color,
                )
                if flowable is not None:
                    story.append(flowable)

        return story

    # -----------------------------------------------------------------------

    @staticmethod
    def _esc(text: str) -> str:
        """Escape text for use in a reportlab Paragraph."""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _chord_line_flowable(self, chord_line, semi_to_name, chord_color):
        return _ChordLineFlowable(
            segments=chord_line.segments,
            semi_to_name=semi_to_name,
            chord_font=self.CHORD_FONT,
            chord_size=self.CHORD_SIZE,
            lyric_font=self.LYRIC_FONT,
            lyric_size=self.LYRIC_SIZE,
            chord_color=chord_color,
            ascii_accidentals=self.ascii_accidentals,
        ).get()

    def _line_to_flowable(
        self,
        line,
        semi_to_name,
        lyric_style,
        comment_style,
        chorus_ref_style,
        chord_color,
    ):
        from reportlab.platypus import PageBreak, Paragraph, Spacer

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
                fontName=self.SECTION_LABEL_FONT,
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
        self,
        story,
        section,
        semi_to_name,
        section_label_style,
        lyric_style,
        comment_style,
        chorus_ref_style,
        chord_color,
    ):
        from reportlab.platypus import KeepTogether, Paragraph

        section_flowables = []
        if section.label:
            section_flowables.append(
                Paragraph(self._esc(section.label), section_label_style)
            )
        for line in section.lines:
            flowable = self._line_to_flowable(
                line,
                semi_to_name,
                lyric_style,
                comment_style,
                chorus_ref_style,
                chord_color,
            )
            if flowable is not None:
                section_flowables.append(flowable)
        if section_flowables:
            story.append(KeepTogether(section_flowables))
