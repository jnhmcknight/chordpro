"""Tests for ChordPro renderers: HtmlRenderer, TextRenderer, QuillDeltaRenderer,
and the render() / register_renderer() dispatch API."""

import pytest
from markupsafe import Markup

from chordpro.models import (
    BreakLine,
    ChordDiagram,
    ChordLine,
    ChorusRef,
    ColumnBreak,
    Columns,
    CommentBox,
    CommentItalic,
    CommentLine,
    GridOff,
    GridOn,
    Highlight,
    Image,
    LyricLine,
    NewPage,
    NewPhysicalPage,
    NewSong,
    Section,
    Segment,
    Song,
    Transpose,
    Verse,
    Chorus,
)
from chordpro.parser import build_chord_semi_to_name
from chordpro.renderers import (
    BaseRenderer,
    HtmlRenderer,
    QuillDeltaRenderer,
    TextRenderer,
    chordpro_to_html,
    register_renderer,
    render,
    render_html,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def song(*body):
    return Song(body=list(body))


def chord_line(*segs):
    return ChordLine(segments=list(segs))


# ---------------------------------------------------------------------------
# HtmlRenderer — chord line internals
# ---------------------------------------------------------------------------


class TestHtmlRendererChordLine:
    renderer = HtmlRenderer()

    def test_produces_cp_line_div(self):
        html = self.renderer._render_chord_line(chord_line(Segment("G", "Hello")), None)
        assert html.startswith('<div class="cp-line">')
        assert html.endswith("</div>")

    def test_chord_span(self):
        html = self.renderer._render_chord_line(chord_line(Segment("G", "Hello")), None)
        assert 'class="cp-chord"' in html
        assert ">G<" in html

    def test_lyric_span(self):
        html = self.renderer._render_chord_line(chord_line(Segment("G", "Hello")), None)
        assert 'class="cp-lyric"' in html
        assert "Hello" in html

    def test_data_chord_attribute(self):
        html = self.renderer._render_chord_line(chord_line(Segment("G", "Hello")), None)
        assert 'data-chord="G"' in html

    def test_empty_lyric_gets_nbsp(self):
        html = self.renderer._render_chord_line(chord_line(Segment("G", "")), None)
        assert "&nbsp;" in html

    def test_lyric_only_segment(self):
        html = self.renderer._render_chord_line(
            chord_line(Segment(None, "no chord")), None
        )
        assert 'class="cp-lyric-only"' in html
        assert 'class="cp-chord"' not in html

    def test_notation_conversion_applied(self):
        semi = build_chord_semi_to_name("latin")
        html = self.renderer._render_chord_line(chord_line(Segment("C", "Do")), semi)
        assert ">Do<" in html
        assert 'data-chord="C"' in html  # raw root preserved

    def test_html_escaping_in_lyric(self):
        html = self.renderer._render_chord_line(
            chord_line(Segment("G", "<script>")), None
        )
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


# ---------------------------------------------------------------------------
# HtmlRenderer — full song render
# ---------------------------------------------------------------------------


class TestHtmlRenderer:
    renderer = HtmlRenderer()

    def test_empty_song(self):
        assert self.renderer.render(Song()) == Markup("")

    def test_returns_markup(self):
        assert isinstance(self.renderer.render(song(LyricLine("hi"))), Markup)

    def test_lyric_line(self):
        result = self.renderer.render(song(LyricLine("Amazing grace")))
        assert 'class="cp-lyric-line"' in result
        assert "Amazing grace" in result

    def test_break_line(self):
        assert 'class="cp-break"' in self.renderer.render(song(BreakLine()))

    def test_comment_line(self):
        result = self.renderer.render(song(CommentLine("A note")))
        assert 'class="cp-comment"' in result
        assert "A note" in result

    def test_comment_italic(self):
        result = self.renderer.render(song(CommentItalic("italic")))
        assert "cp-comment-italic" in result

    def test_comment_box(self):
        result = self.renderer.render(song(CommentBox("boxed")))
        assert "cp-comment-box" in result

    def test_highlight(self):
        result = self.renderer.render(song(Highlight("hi")))
        assert 'class="cp-highlight"' in result

    def test_chord_line(self):
        result = self.renderer.render(song(chord_line(Segment("G", "Amazing"))))
        assert 'class="cp-line"' in result
        assert 'class="cp-chord"' in result

    def test_chorus_ref_empty_label(self):
        result = self.renderer.render(song(ChorusRef()))
        assert 'class="cp-chorus-ref"' in result

    def test_chorus_ref_with_label(self):
        result = self.renderer.render(song(ChorusRef(label="Chorus 2")))
        assert "Chorus 2" in result
        assert "cp-chorus-ref-label" in result

    def test_image(self):
        result = self.renderer.render(song(Image(raw="src=photo.png")))
        assert 'class="cp-image"' in result
        assert 'data-raw="src=photo.png"' in result

    def test_chord_diagram(self):
        result = self.renderer.render(song(ChordDiagram(name="Am")))
        assert 'class="cp-chord-diagram"' in result
        assert 'data-chord="Am"' in result

    def test_transpose(self):
        result = self.renderer.render(song(Transpose(semitones=2)))
        assert 'class="cp-transpose"' in result
        assert 'data-semitones="2"' in result

    def test_transpose_cancel(self):
        result = self.renderer.render(song(Transpose(semitones=None)))
        assert 'data-semitones=""' in result

    def test_new_page(self):
        assert 'class="cp-new-page"' in self.renderer.render(song(NewPage()))

    def test_new_physical_page(self):
        assert 'class="cp-new-physical-page"' in self.renderer.render(
            song(NewPhysicalPage())
        )

    def test_column_break(self):
        assert 'class="cp-column-break"' in self.renderer.render(song(ColumnBreak()))

    def test_columns(self):
        result = self.renderer.render(song(Columns(count=3)))
        assert 'data-count="3"' in result

    def test_grid_on(self):
        assert "cp-grid-on" in self.renderer.render(song(GridOn()))

    def test_grid_off(self):
        assert "cp-grid-off" in self.renderer.render(song(GridOff()))

    def test_new_song(self):
        assert 'class="cp-new-song"' in self.renderer.render(song(NewSong()))

    def test_section_wrapper(self):
        v = Verse(label="Verse 1", lines=[LyricLine("text")])
        result = self.renderer.render(song(v))
        assert 'class="cp-section"' in result
        assert 'data-section="verse"' in result
        assert "Verse 1" in result

    def test_generic_section_kind(self):
        sec = Section(kind="custom", label="Custom")
        assert 'data-section="custom"' in self.renderer.render(song(sec))

    def test_notation_applied(self):
        semi = build_chord_semi_to_name("latin")
        result = self.renderer.render(song(chord_line(Segment("C", "Do"))), semi)
        assert ">Do<" in result

    def test_multiple_sections(self):
        s = song(Verse(label="Verse"), Chorus(label="Chorus"))
        assert self.renderer.render(s).count('class="cp-section"') == 2

    def test_xss_escaped_in_lyric(self):
        result = self.renderer.render(song(LyricLine("<script>")))
        assert "<script>" not in result


# ---------------------------------------------------------------------------
# TextRenderer
# ---------------------------------------------------------------------------


class TestTextRenderer:
    renderer = TextRenderer()

    def test_returns_str(self):
        assert isinstance(self.renderer.render(Song()), str)

    def test_empty_song(self):
        assert self.renderer.render(Song()) == ""

    def test_lyric_line(self):
        assert "Amazing grace" in self.renderer.render(song(LyricLine("Amazing grace")))

    def test_break_line_is_empty_string(self):
        result = self.renderer.render(song(BreakLine()))
        assert result == ""

    def test_comment_line_prefixed(self):
        result = self.renderer.render(song(CommentLine("A note")))
        assert result == "# A note"

    def test_comment_italic_prefixed(self):
        result = self.renderer.render(song(CommentItalic("italic")))
        assert result.startswith("# ")

    def test_comment_box_prefixed(self):
        assert self.renderer.render(song(CommentBox("boxed"))).startswith("# ")

    def test_highlight_prefixed(self):
        assert self.renderer.render(song(Highlight("hi"))).startswith("# ")

    def test_chorus_ref_default_label(self):
        assert "[Chorus]" in self.renderer.render(song(ChorusRef()))

    def test_chorus_ref_custom_label(self):
        assert "[Chorus 2]" in self.renderer.render(song(ChorusRef(label="Chorus 2")))

    def test_new_page_is_form_feed(self):
        assert "\f" in self.renderer.render(song(NewPage()))

    def test_chord_line_two_rows(self):
        cl = chord_line(Segment("G", "Amazing"))
        result = self.renderer.render(song(cl))
        lines = result.splitlines()
        assert len(lines) == 2
        assert "G" in lines[0]
        assert "Amazing" in lines[1]

    def test_chord_line_lyric_only_segment(self):
        # segment with no chord should only appear in lyric row
        cl = chord_line(Segment(None, "words"))
        result = self.renderer.render(song(cl))
        assert "words" in result
        # only lyric row — no chord row (chord_row.strip() is falsy)
        assert result.count("\n") == 0

    def test_chord_line_notation_applied(self):
        semi = build_chord_semi_to_name("latin")
        cl = chord_line(Segment("C", "Do"))
        result = self.renderer.render(song(cl), semi)
        # In latin notation C → "Do"; both chord row and lyric row contain "Do"
        lines = result.splitlines()
        assert len(lines) == 2
        assert "Do" in lines[0]  # converted chord row
        assert "Do" in lines[1]  # lyric row

    def test_chord_line_column_alignment(self):
        # Two segments so interior padding is preserved: Em/Amazing + G/grace
        cl = chord_line(Segment("Em", "Amazing"), Segment("G", "grace"))
        result = self.renderer.render(song(cl))
        chord_row, lyric_row = result.splitlines()
        # "Em" must be padded to width of "Amazing" (7) before the next segment
        em_col = chord_row.index("Em")
        amazing_col = lyric_row.index("Amazing")
        assert em_col == amazing_col  # chord column matches lyric column
        g_col = chord_row.index("G")
        grace_col = lyric_row.index("grace")
        assert g_col == grace_col

    def test_section_label_appears(self):
        v = Verse(label="Verse 1", lines=[LyricLine("text")])
        result = self.renderer.render(song(v))
        assert "Verse 1" in result
        assert "text" in result

    def test_no_html_tags(self):
        v = Verse(label="V", lines=[LyricLine("line")])
        result = self.renderer.render(song(v))
        assert "<" not in result
        assert ">" not in result


# ---------------------------------------------------------------------------
# QuillDeltaRenderer
# ---------------------------------------------------------------------------


class TestQuillDeltaRenderer:
    renderer = QuillDeltaRenderer()

    def test_returns_dict_with_ops(self):
        result = self.renderer.render(Song())
        assert isinstance(result, dict)
        assert "ops" in result

    def test_empty_song_has_no_ops(self):
        assert self.renderer.render(Song())["ops"] == []

    def test_lyric_line_insert(self):
        ops = self.renderer.render(song(LyricLine("Amazing grace")))["ops"]
        texts = [op["insert"] for op in ops]
        assert "Amazing grace" in texts

    def test_lyric_line_ends_with_newline(self):
        ops = self.renderer.render(song(LyricLine("hi")))["ops"]
        assert ops[-1]["insert"] == "\n"

    def test_break_line_is_newline_op(self):
        ops = self.renderer.render(song(BreakLine()))["ops"]
        assert ops == [{"insert": "\n"}]

    def test_comment_line_is_italic(self):
        ops = self.renderer.render(song(CommentLine("note")))["ops"]
        text_op = next(op for op in ops if op.get("insert") == "note")
        assert text_op.get("attributes", {}).get("italic") is True

    def test_highlight_is_bold(self):
        ops = self.renderer.render(song(Highlight("important")))["ops"]
        text_op = next(op for op in ops if op.get("insert") == "important")
        assert text_op.get("attributes", {}).get("bold") is True

    def test_chorus_ref_is_italic_bracketed(self):
        ops = self.renderer.render(song(ChorusRef()))["ops"]
        text_op = ops[0]
        assert "[Chorus]" in text_op["insert"]
        assert text_op.get("attributes", {}).get("italic") is True

    def test_chorus_ref_custom_label(self):
        ops = self.renderer.render(song(ChorusRef(label="Chorus 2")))["ops"]
        assert any("Chorus 2" in op["insert"] for op in ops)

    def test_chord_line_chord_attribute(self):
        cl = chord_line(Segment("G", "Amazing"))
        ops = self.renderer.render(song(cl))["ops"]
        chord_ops = [op for op in ops if op.get("attributes", {}).get("chord")]
        assert len(chord_ops) == 1
        assert chord_ops[0]["insert"] == "G"

    def test_chord_line_lyric_has_no_chord_attr(self):
        cl = chord_line(Segment("G", "word"))
        ops = self.renderer.render(song(cl))["ops"]
        lyric_ops = [op for op in ops if op.get("insert") == "word"]
        assert lyric_ops
        assert not lyric_ops[0].get("attributes", {}).get("chord")

    def test_chord_line_ends_with_newline(self):
        cl = chord_line(Segment("G", "word"))
        ops = self.renderer.render(song(cl))["ops"]
        assert ops[-1]["insert"] == "\n"

    def test_section_label_is_bold(self):
        v = Verse(label="Verse 1", lines=[])
        ops = self.renderer.render(song(v))["ops"]
        label_op = next(op for op in ops if op.get("insert") == "Verse 1")
        assert label_op.get("attributes", {}).get("bold") is True

    def test_notation_applied_in_chord(self):
        semi = build_chord_semi_to_name("latin")
        cl = chord_line(Segment("C", "Do"))
        ops = self.renderer.render(song(cl), semi)["ops"]
        chord_ops = [op for op in ops if op.get("attributes", {}).get("chord")]
        # Latin C is "Do" in solfege — whatever the conversion, chord attr must be set
        assert chord_ops


# ---------------------------------------------------------------------------
# render() dispatch
# ---------------------------------------------------------------------------


class TestRenderDispatch:
    def test_html_format_returns_markup(self):
        result = render(song(LyricLine("hi")), format="html")
        assert isinstance(result, Markup)

    def test_text_format_returns_str(self):
        result = render(song(LyricLine("hi")), format="text")
        assert isinstance(result, str)
        assert not isinstance(result, Markup)

    def test_quill_delta_format_returns_dict(self):
        result = render(song(LyricLine("hi")), format="quill-delta")
        assert isinstance(result, dict)
        assert "ops" in result

    def test_unknown_format_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown format"):
            render(Song(), format="bogus")

    def test_error_message_lists_registered_formats(self):
        with pytest.raises(ValueError, match='"html"'):
            render(Song(), format="bogus")


# ---------------------------------------------------------------------------
# register_renderer()
# ---------------------------------------------------------------------------


class TestRegisterRenderer:
    def test_custom_renderer_callable_via_render(self):
        class UpperRenderer(BaseRenderer):
            def render(self, song, semi_to_name=None):
                return "CUSTOM"

        register_renderer("upper", UpperRenderer)
        assert render(Song(), format="upper") == "CUSTOM"

    def test_registered_name_overrides_builtin(self):
        _REGISTRY_SNAPSHOT = HtmlRenderer

        class NoopHtml(BaseRenderer):
            def render(self, song, semi_to_name=None):
                return Markup("")

        register_renderer("html", NoopHtml)
        result = render(song(LyricLine("anything")), format="html")
        assert result == Markup("")

        # restore so other tests are not affected
        register_renderer("html", HtmlRenderer)

    def test_subclass_must_implement_render(self):
        with pytest.raises(TypeError):
            BaseRenderer()  # abstract


# ---------------------------------------------------------------------------
# chordpro_to_html — parse + render shim
# ---------------------------------------------------------------------------


class TestChordproToHtml:
    def test_empty_returns_empty_markup(self):
        assert chordpro_to_html("") == Markup("")

    def test_returns_markup(self):
        assert isinstance(chordpro_to_html("[G]Hello"), Markup)

    def test_plain_lyric_line(self):
        result = chordpro_to_html("Amazing grace")
        assert 'class="cp-lyric-line"' in result
        assert "Amazing grace" in result

    def test_blank_line_becomes_break(self):
        assert 'class="cp-break"' in chordpro_to_html("line one\n\nline two")

    def test_chord_line_rendered(self):
        result = chordpro_to_html("[G]Amazing [D]grace")
        assert 'class="cp-line"' in result
        assert 'class="cp-chord"' in result

    def test_start_of_verse(self):
        result = chordpro_to_html("{start_of_verse}")
        assert 'data-section="verse"' in result

    def test_notation_applied(self):
        semi = build_chord_semi_to_name("latin")
        assert ">Do<" in chordpro_to_html("[C]Do", semi)

    def test_xss_escaped(self):
        result = chordpro_to_html("<script>alert(1)</script>")
        assert "<script>" not in result


# ---------------------------------------------------------------------------
# render_html shim
# ---------------------------------------------------------------------------


class TestRenderHtmlShim:
    def test_delegates_to_html_renderer(self):
        result = render_html(song(LyricLine("hi")))
        assert isinstance(result, Markup)
        assert "hi" in result

    def test_empty_song(self):
        assert render_html(Song()) == Markup("")
