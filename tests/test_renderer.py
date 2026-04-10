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
    render_many,
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


# ---------------------------------------------------------------------------
# BaseRenderer.render_many — default implementation
# ---------------------------------------------------------------------------


class TestBaseRendererManyDefault:
    """The default render_many() returns a list of individual render() results."""

    def test_default_returns_list(self):
        class EchoRenderer(BaseRenderer):
            def render(self, s, semi_to_name=None):
                return "SONG"

        renderer = EchoRenderer()
        result = renderer.render_many([Song(), Song()])
        assert result == ["SONG", "SONG"]

    def test_default_empty_list(self):
        class EchoRenderer(BaseRenderer):
            def render(self, s, semi_to_name=None):
                return "SONG"

        assert EchoRenderer().render_many([]) == []

    def test_default_single_song(self):
        class EchoRenderer(BaseRenderer):
            def render(self, s, semi_to_name=None):
                return "SONG"

        assert EchoRenderer().render_many([Song()]) == ["SONG"]


# ---------------------------------------------------------------------------
# HtmlRenderer.render_many
# ---------------------------------------------------------------------------


class TestHtmlRendererMany:
    renderer = HtmlRenderer()

    def _two_songs(self):
        return [
            song(LyricLine("Amazing grace")),
            song(LyricLine("How sweet the sound")),
        ]

    def test_returns_markup(self):
        assert isinstance(self.renderer.render_many(self._two_songs()), Markup)

    def test_each_song_wrapped_in_cp_song_div(self):
        result = self.renderer.render_many(self._two_songs())
        assert result.count('<div class="cp-song">') == 2

    def test_content_from_both_songs_present(self):
        result = self.renderer.render_many(self._two_songs())
        assert "Amazing grace" in result
        assert "How sweet the sound" in result

    def test_single_song_still_wrapped(self):
        result = self.renderer.render_many([song(LyricLine("hi"))])
        assert '<div class="cp-song">' in result

    def test_empty_list_returns_empty_markup(self):
        assert self.renderer.render_many([]) == Markup("")

    def test_sections_inside_cp_song_wrapper(self):
        songs = [song(Verse(label="Verse 1", lines=[LyricLine("text")]))]
        result = self.renderer.render_many(songs)
        # cp-section must appear inside cp-song
        cp_song_pos = result.index('class="cp-song"')
        cp_section_pos = result.index('class="cp-section"')
        assert cp_section_pos > cp_song_pos

    def test_notation_applied(self):
        semi = build_chord_semi_to_name("latin")
        result = self.renderer.render_many([song(chord_line(Segment("C", "Do")))], semi)
        assert ">Do<" in result

    def test_xss_escaped(self):
        result = self.renderer.render_many([song(LyricLine("<script>"))])
        assert "<script>" not in result


# ---------------------------------------------------------------------------
# TextRenderer.render_many
# ---------------------------------------------------------------------------


class TestTextRendererMany:
    renderer = TextRenderer()

    def _two_songs(self):
        return [song(LyricLine("song one")), song(LyricLine("song two"))]

    def test_returns_str(self):
        assert isinstance(self.renderer.render_many(self._two_songs()), str)

    def test_songs_joined_by_form_feed(self):
        result = self.renderer.render_many(self._two_songs())
        assert "\f" in result
        parts = result.split("\f")
        assert len(parts) == 2

    def test_content_from_both_songs_present(self):
        result = self.renderer.render_many(self._two_songs())
        assert "song one" in result
        assert "song two" in result

    def test_three_songs_have_two_form_feeds(self):
        songs = [song(LyricLine(f"s{i}")) for i in range(3)]
        assert self.renderer.render_many(songs).count("\f") == 2

    def test_single_song_no_form_feed(self):
        result = self.renderer.render_many([song(LyricLine("only"))])
        assert "\f" not in result

    def test_empty_list_returns_empty_string(self):
        assert self.renderer.render_many([]) == ""

    def test_notation_applied(self):
        semi = build_chord_semi_to_name("latin")
        result = self.renderer.render_many([song(chord_line(Segment("C", "Do")))], semi)
        assert "Do" in result


# ---------------------------------------------------------------------------
# QuillDeltaRenderer.render_many
# ---------------------------------------------------------------------------


class TestQuillDeltaRendererMany:
    renderer = QuillDeltaRenderer()

    def _two_songs(self):
        return [song(LyricLine("song one")), song(LyricLine("song two"))]

    def test_returns_dict_with_ops(self):
        result = self.renderer.render_many(self._two_songs())
        assert isinstance(result, dict)
        assert "ops" in result

    def test_content_from_both_songs_present(self):
        ops = self.renderer.render_many(self._two_songs())["ops"]
        texts = [op["insert"] for op in ops]
        assert "song one" in texts
        assert "song two" in texts

    def test_page_break_op_inserted_between_songs(self):
        ops = self.renderer.render_many(self._two_songs())["ops"]
        page_break_ops = [
            op for op in ops if op.get("attributes", {}).get("page_break")
        ]
        assert len(page_break_ops) == 1

    def test_page_break_op_is_newline(self):
        ops = self.renderer.render_many(self._two_songs())["ops"]
        page_break_op = next(
            op for op in ops if op.get("attributes", {}).get("page_break")
        )
        assert page_break_op["insert"] == "\n"

    def test_three_songs_have_two_page_breaks(self):
        songs = [song(LyricLine(f"s{i}")) for i in range(3)]
        ops = self.renderer.render_many(songs)["ops"]
        page_breaks = [op for op in ops if op.get("attributes", {}).get("page_break")]
        assert len(page_breaks) == 2

    def test_single_song_no_page_break(self):
        ops = self.renderer.render_many([song(LyricLine("only"))])["ops"]
        assert not any(op.get("attributes", {}).get("page_break") for op in ops)

    def test_empty_list_returns_empty_ops(self):
        assert self.renderer.render_many([]) == {"ops": []}

    def test_notation_applied(self):
        semi = build_chord_semi_to_name("latin")
        ops = self.renderer.render_many([song(chord_line(Segment("C", "Do")))], semi)[
            "ops"
        ]
        chord_ops = [op for op in ops if op.get("attributes", {}).get("chord")]
        assert chord_ops


# ---------------------------------------------------------------------------
# render_many() dispatch
# ---------------------------------------------------------------------------


class TestRenderManyDispatch:
    def test_html_format_returns_markup(self):
        songs = [song(LyricLine("hi")), song(LyricLine("there"))]
        assert isinstance(render_many(songs, format="html"), Markup)

    def test_text_format_returns_str(self):
        songs = [song(LyricLine("hi")), song(LyricLine("there"))]
        result = render_many(songs, format="text")
        assert isinstance(result, str)
        assert not isinstance(result, Markup)

    def test_quill_delta_format_returns_dict(self):
        songs = [song(LyricLine("hi")), song(LyricLine("there"))]
        result = render_many(songs, format="quill-delta")
        assert isinstance(result, dict)
        assert "ops" in result

    def test_unknown_format_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown format"):
            render_many([Song()], format="bogus")

    def test_custom_renderer_render_many_called(self):
        class MultiRenderer(BaseRenderer):
            def render(self, s, semi_to_name=None):
                return "SONG"

            def render_many(self, songs, semi_to_name=None):
                return f"MULTI:{len(songs)}"

        register_renderer("multi", MultiRenderer)
        assert render_many([Song(), Song()], format="multi") == "MULTI:2"


# ---------------------------------------------------------------------------
# ascii_accidentals — BaseRenderer helpers
# ---------------------------------------------------------------------------


class TestFinalizeChord:
    """Unit tests for BaseRenderer._finalize_chord."""

    def test_unicode_mode_passes_through_sharp(self):
        r = HtmlRenderer(ascii_accidentals=False)
        assert r._finalize_chord("F♯") == "F♯"

    def test_unicode_mode_passes_through_flat(self):
        r = HtmlRenderer(ascii_accidentals=False)
        assert r._finalize_chord("B♭") == "B♭"

    def test_ascii_mode_converts_sharp(self):
        r = HtmlRenderer(ascii_accidentals=True)
        assert r._finalize_chord("F♯") == "F#"

    def test_ascii_mode_converts_flat(self):
        r = HtmlRenderer(ascii_accidentals=True)
        assert r._finalize_chord("B♭") == "Bb"

    def test_ascii_mode_natural_note_unchanged(self):
        r = HtmlRenderer(ascii_accidentals=True)
        assert r._finalize_chord("G") == "G"

    def test_ascii_mode_suffix_preserved(self):
        r = HtmlRenderer(ascii_accidentals=True)
        assert r._finalize_chord("B♭m7") == "Bbm7"


class TestMakeClassmethod:
    def test_none_uses_html_default(self):
        r = HtmlRenderer._make(None)
        assert r.ascii_accidentals is False

    def test_none_uses_text_default(self):
        r = TextRenderer._make(None)
        assert r.ascii_accidentals is True

    def test_explicit_true_overrides_html_default(self):
        r = HtmlRenderer._make(True)
        assert r.ascii_accidentals is True

    def test_explicit_false_overrides_text_default(self):
        r = TextRenderer._make(False)
        assert r.ascii_accidentals is False


# ---------------------------------------------------------------------------
# ascii_accidentals — renderer defaults
# ---------------------------------------------------------------------------

# A standard-notation semi_to_name so B♭ and F♯ appear in output.
_STD = build_chord_semi_to_name("standard")


class TestTextRendererAsciiDefaults:
    """TextRenderer defaults to ASCII accidentals."""

    def test_default_is_ascii(self):
        assert TextRenderer().ascii_accidentals is True

    def test_flat_chord_output_ascii_by_default(self):
        cl = chord_line(Segment("Bb", "word"))
        result = TextRenderer().render(song(cl), _STD)
        assert "Bb" in result
        assert "♭" not in result

    def test_sharp_chord_output_ascii_by_default(self):
        cl = chord_line(Segment("F#", "word"))
        result = TextRenderer().render(song(cl), _STD)
        assert "F#" in result
        assert "♯" not in result

    def test_unicode_override_outputs_flat_symbol(self):
        cl = chord_line(Segment("Bb", "word"))
        result = TextRenderer(ascii_accidentals=False).render(song(cl), _STD)
        assert "B♭" in result
        assert "Bb" not in result

    def test_unicode_override_outputs_sharp_symbol(self):
        cl = chord_line(Segment("F#", "word"))
        result = TextRenderer(ascii_accidentals=False).render(song(cl), _STD)
        assert "F♯" in result
        assert "F#" not in result


class TestHtmlRendererAsciiDefaults:
    """HtmlRenderer defaults to Unicode accidentals."""

    def test_default_is_unicode(self):
        assert HtmlRenderer().ascii_accidentals is False

    def test_flat_chord_output_unicode_by_default(self):
        cl = chord_line(Segment("Bb", "word"))
        result = HtmlRenderer().render(song(cl), _STD)
        assert ">B♭<" in result

    def test_sharp_chord_output_unicode_by_default(self):
        cl = chord_line(Segment("F#", "word"))
        result = HtmlRenderer().render(song(cl), _STD)
        assert ">F♯<" in result

    def test_ascii_override_flat(self):
        cl = chord_line(Segment("Bb", "word"))
        result = HtmlRenderer(ascii_accidentals=True).render(song(cl), _STD)
        assert ">Bb<" in result
        assert "♭" not in result

    def test_ascii_override_sharp(self):
        cl = chord_line(Segment("F#", "word"))
        result = HtmlRenderer(ascii_accidentals=True).render(song(cl), _STD)
        assert ">F#<" in result
        assert "♯" not in result


class TestQuillDeltaRendererAsciiDefaults:
    """QuillDeltaRenderer defaults to Unicode accidentals."""

    def test_default_is_unicode(self):
        assert QuillDeltaRenderer().ascii_accidentals is False

    def test_flat_chord_unicode_by_default(self):
        cl = chord_line(Segment("Bb", "word"))
        ops = QuillDeltaRenderer().render(song(cl), _STD)["ops"]
        chord_ops = [op for op in ops if op.get("attributes", {}).get("chord")]
        assert chord_ops[0]["insert"] == "B♭"

    def test_sharp_chord_unicode_by_default(self):
        cl = chord_line(Segment("F#", "word"))
        ops = QuillDeltaRenderer().render(song(cl), _STD)["ops"]
        chord_ops = [op for op in ops if op.get("attributes", {}).get("chord")]
        assert chord_ops[0]["insert"] == "F♯"

    def test_ascii_override_flat(self):
        cl = chord_line(Segment("Bb", "word"))
        ops = QuillDeltaRenderer(ascii_accidentals=True).render(song(cl), _STD)["ops"]
        chord_ops = [op for op in ops if op.get("attributes", {}).get("chord")]
        assert chord_ops[0]["insert"] == "Bb"

    def test_ascii_override_sharp(self):
        cl = chord_line(Segment("F#", "word"))
        ops = QuillDeltaRenderer(ascii_accidentals=True).render(song(cl), _STD)["ops"]
        chord_ops = [op for op in ops if op.get("attributes", {}).get("chord")]
        assert chord_ops[0]["insert"] == "F#"


# ---------------------------------------------------------------------------
# ascii_accidentals — render() / render_many() dispatch
# ---------------------------------------------------------------------------


class TestRenderDispatchAsciiAccidentals:
    _cl = chord_line(Segment("Bb", "word"))

    def test_text_none_uses_ascii_default(self):
        result = render(song(self._cl), _STD, format="text", ascii_accidentals=None)
        assert "Bb" in result
        assert "♭" not in result

    def test_text_explicit_false_uses_unicode(self):
        result = render(song(self._cl), _STD, format="text", ascii_accidentals=False)
        assert "B♭" in result

    def test_html_none_uses_unicode_default(self):
        result = render(song(self._cl), _STD, format="html", ascii_accidentals=None)
        assert ">B♭<" in result

    def test_html_explicit_true_uses_ascii(self):
        result = render(song(self._cl), _STD, format="html", ascii_accidentals=True)
        assert ">Bb<" in result
        assert "♭" not in result

    def test_quill_delta_none_uses_unicode_default(self):
        ops = render(song(self._cl), _STD, format="quill-delta", ascii_accidentals=None)["ops"]
        chord_ops = [op for op in ops if op.get("attributes", {}).get("chord")]
        assert chord_ops[0]["insert"] == "B♭"

    def test_quill_delta_explicit_true_uses_ascii(self):
        ops = render(song(self._cl), _STD, format="quill-delta", ascii_accidentals=True)["ops"]
        chord_ops = [op for op in ops if op.get("attributes", {}).get("chord")]
        assert chord_ops[0]["insert"] == "Bb"


class TestRenderManyDispatchAsciiAccidentals:
    _cl = chord_line(Segment("F#", "word"))

    def test_html_none_uses_unicode_default(self):
        result = render_many([song(self._cl)], _STD, format="html", ascii_accidentals=None)
        assert ">F♯<" in result

    def test_html_explicit_true_uses_ascii(self):
        result = render_many([song(self._cl)], _STD, format="html", ascii_accidentals=True)
        assert ">F#<" in result
        assert "♯" not in result

    def test_text_none_uses_ascii_default(self):
        result = render_many([song(self._cl)], _STD, format="text", ascii_accidentals=None)
        assert "F#" in result
        assert "♯" not in result

    def test_text_explicit_false_uses_unicode(self):
        result = render_many([song(self._cl)], _STD, format="text", ascii_accidentals=False)
        assert "F♯" in result
