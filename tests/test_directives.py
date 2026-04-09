"""
Tests for all ChordPro directives added from the spec.

Covers:
- Metadata directives (title, artist, key, meta, tag, …)
- Comment variants (comment_italic, comment_box, highlight)
- Layout/flow items (new_page, column_break, columns, new_song, …)
- Chord items (define, chord, transpose)
- Appearance toggles (grid, no_grid)
- Chorus reference (chorus)
- Image directive
- New section types (Grid, Abc, Lilypond, Svg, TextBlock)
- Short forms for all newly added directives
- Mixed short/long forms
"""

import pytest

from chordpro.models import (
    Abc,
    ChordDefinition,
    ChordDiagram,
    ChorusRef,
    ColumnBreak,
    Columns,
    CommentBox,
    CommentItalic,
    Grid,
    GridOff,
    GridOn,
    Highlight,
    Image,
    Lilypond,
    NewPage,
    NewPhysicalPage,
    NewSong,
    Song,
    SongMeta,
    Svg,
    TextBlock,
    Transpose,
)
from chordpro.parser import parse
from chordpro.renderers import chordpro_to_html

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _body_types(content: str) -> list[type]:
    return [type(item) for item in parse(content).body]


def _single_body(content: str):
    song = parse(content)
    assert len(song.body) == 1
    return song.body[0]


# ---------------------------------------------------------------------------
# Metadata directives
# ---------------------------------------------------------------------------


class TestMetadataDirectives:
    def test_title(self):
        assert parse("{title: Amazing Grace}").meta.title == "Amazing Grace"

    def test_title_short_form(self):
        assert parse("{t: Amazing Grace}").meta.title == "Amazing Grace"

    def test_title_does_not_appear_in_body(self):
        assert parse("{title: Amazing Grace}").body == []

    def test_subtitle(self):
        assert parse("{subtitle: A Song}").meta.subtitle == ["A Song"]

    def test_subtitle_short_form(self):
        assert parse("{st: A Song}").meta.subtitle == ["A Song"]

    def test_subtitle_multiple(self):
        song = parse("{subtitle: Part 1}\n{subtitle: Part 2}")
        assert song.meta.subtitle == ["Part 1", "Part 2"]

    def test_artist(self):
        assert parse("{artist: John Newton}").meta.artist == ["John Newton"]

    def test_sortartist(self):
        assert parse("{sortartist: Newton, John}").meta.sortartist == ["Newton, John"]

    def test_album(self):
        assert parse("{album: Greatest Hymns}").meta.album == ["Greatest Hymns"]

    def test_composer(self):
        assert parse("{composer: Bach}").meta.composer == ["Bach"]

    def test_lyricist(self):
        assert parse("{lyricist: Newton}").meta.lyricist == ["Newton"]

    def test_copyright(self):
        assert parse("{copyright: Public Domain}").meta.copyright == ["Public Domain"]

    def test_sorttitle(self):
        assert parse("{sorttitle: Amazing Grace}").meta.sorttitle == ["Amazing Grace"]

    def test_year(self):
        assert parse("{year: 1779}").meta.year == "1779"

    def test_key_single(self):
        assert parse("{key: G}").meta.key == ["G"]

    def test_key_multiple(self):
        song = parse("{key: G}\n{key: Am}")
        assert song.meta.key == ["G", "Am"]

    def test_time(self):
        assert parse("{time: 4/4}").meta.time == ["4/4"]

    def test_tempo(self):
        assert parse("{tempo: 120}").meta.tempo == ["120"]

    def test_duration(self):
        assert parse("{duration: 3:45}").meta.duration == "3:45"

    def test_capo(self):
        assert parse("{capo: 2}").meta.capo == "2"

    def test_tag_goes_to_meta_dict(self):
        song = parse("{tag: hymn}")
        assert "hymn" in song.meta.meta.get("tag", [])

    def test_tag_multiple(self):
        song = parse("{tag: hymn}\n{tag: traditional}")
        assert song.meta.meta["tag"] == ["hymn", "traditional"]

    def test_meta_directive_generic(self):
        song = parse("{meta: genre Gospel}")
        assert song.meta.meta.get("genre") == ["Gospel"]

    def test_meta_directive_multiple_values(self):
        song = parse("{meta: genre Gospel}\n{meta: genre Hymn}")
        assert song.meta.meta["genre"] == ["Gospel", "Hymn"]

    def test_meta_directive_empty_value(self):
        # {meta: name} with no value — key should exist with empty list entry
        song = parse("{meta: keywords}")
        assert "keywords" in song.meta.meta

    def test_metadata_combined_with_body(self):
        song = parse("{title: Song}\n[G]Amazing grace")
        assert song.meta.title == "Song"
        assert len(song.body) == 1  # only the chord line


# ---------------------------------------------------------------------------
# Comment variant directives
# ---------------------------------------------------------------------------


class TestCommentVariants:
    def test_comment_italic(self):
        item = _single_body("{comment_italic: play softly}")
        assert isinstance(item, CommentItalic)
        assert item.text == "play softly"

    def test_comment_italic_short_form(self):
        item = _single_body("{ci: play softly}")
        assert isinstance(item, CommentItalic)

    def test_comment_box(self):
        item = _single_body("{comment_box: important note}")
        assert isinstance(item, CommentBox)
        assert item.text == "important note"

    def test_highlight(self):
        item = _single_body("{highlight: key change here}")
        assert isinstance(item, Highlight)
        assert item.text == "key change here"

    def test_comment_variants_inside_section(self):
        song = parse("{start_of_verse}\n{ci: softly}\n{end_of_verse}")
        verse = song.body[0]
        assert isinstance(verse.lines[0], CommentItalic)

    def test_comment_italic_renders(self):
        result = chordpro_to_html("{ci: gentle}")
        assert "cp-comment-italic" in result
        assert "gentle" in result

    def test_comment_box_renders(self):
        result = chordpro_to_html("{comment_box: note}")
        assert "cp-comment-box" in result

    def test_highlight_renders(self):
        result = chordpro_to_html("{highlight: chorus key}")
        assert "cp-highlight" in result


# ---------------------------------------------------------------------------
# Chorus reference directive
# ---------------------------------------------------------------------------


class TestChorusRef:
    def test_bare_chorus(self):
        item = _single_body("{chorus}")
        assert isinstance(item, ChorusRef)
        assert item.label is None

    def test_chorus_with_label(self):
        item = _single_body("{chorus: Chorus 2}")
        assert isinstance(item, ChorusRef)
        assert item.label == "Chorus 2"

    def test_chorus_ref_renders(self):
        result = chordpro_to_html("{chorus}")
        assert "cp-chorus-ref" in result

    def test_chorus_ref_with_label_renders(self):
        result = chordpro_to_html("{chorus: Repeat}")
        assert "Repeat" in result


# ---------------------------------------------------------------------------
# Image directive
# ---------------------------------------------------------------------------


class TestImageDirective:
    def test_image_basic(self):
        item = _single_body("{image: photo.png}")
        assert isinstance(item, Image)
        assert item.raw == "photo.png"

    def test_image_with_attributes(self):
        item = _single_body("{image: src=photo.png width=50%}")
        assert isinstance(item, Image)
        assert "src=photo.png" in item.raw

    def test_image_renders(self):
        result = chordpro_to_html("{image: photo.png}")
        assert "cp-image" in result


# ---------------------------------------------------------------------------
# Chord definition and diagram directives
# ---------------------------------------------------------------------------


class TestChordDirectives:
    def test_define(self):
        item = _single_body("{define: Am base-fret 1 frets 0 2 2 1 0 0}")
        assert isinstance(item, ChordDefinition)
        assert item.name == "Am"
        assert "base-fret" in item.raw

    def test_define_stores_full_raw(self):
        raw = "G base-fret 1 frets 3 2 0 0 0 3"
        item = _single_body(f"{{define: {raw}}}")
        assert item.raw == raw

    def test_define_no_html_output(self):
        # ChordDefinition has no visual rendering
        result = chordpro_to_html("{define: Am base-fret 1 frets 0 2 2 1 0 0}")
        assert result == ""

    def test_chord_diagram(self):
        item = _single_body("{chord: Am}")
        assert isinstance(item, ChordDiagram)
        assert item.name == "Am"

    def test_chord_diagram_renders(self):
        result = chordpro_to_html("{chord: Am}")
        assert "cp-chord-diagram" in result
        assert 'data-chord="Am"' in result


# ---------------------------------------------------------------------------
# Transpose directive
# ---------------------------------------------------------------------------


class TestTranspose:
    def test_transpose_positive(self):
        item = _single_body("{transpose: 2}")
        assert isinstance(item, Transpose)
        assert item.semitones == 2

    def test_transpose_negative(self):
        item = _single_body("{transpose: -3}")
        assert isinstance(item, Transpose)
        assert item.semitones == -3

    def test_transpose_cancel(self):
        item = _single_body("{transpose}")
        assert isinstance(item, Transpose)
        assert item.semitones is None

    def test_transpose_renders_with_data_attr(self):
        result = chordpro_to_html("{transpose: 2}")
        assert "cp-transpose" in result
        assert 'data-semitones="2"' in result

    def test_transpose_cancel_renders_empty_attr(self):
        result = chordpro_to_html("{transpose}")
        assert 'data-semitones=""' in result


# ---------------------------------------------------------------------------
# Layout / flow-control directives
# ---------------------------------------------------------------------------


class TestLayoutDirectives:
    def test_new_page(self):
        assert isinstance(_single_body("{new_page}"), NewPage)

    def test_new_page_short_form(self):
        assert isinstance(_single_body("{np}"), NewPage)

    def test_new_physical_page(self):
        assert isinstance(_single_body("{new_physical_page}"), NewPhysicalPage)

    def test_new_physical_page_short_form(self):
        assert isinstance(_single_body("{npp}"), NewPhysicalPage)

    def test_column_break(self):
        assert isinstance(_single_body("{column_break}"), ColumnBreak)

    def test_column_break_short_form(self):
        assert isinstance(_single_body("{cb}"), ColumnBreak)

    def test_columns(self):
        item = _single_body("{columns: 2}")
        assert isinstance(item, Columns)
        assert item.count == 2

    def test_columns_short_form(self):
        item = _single_body("{col: 3}")
        assert isinstance(item, Columns)
        assert item.count == 3

    def test_new_song(self):
        assert isinstance(_single_body("{new_song}"), NewSong)

    def test_new_song_short_form(self):
        assert isinstance(_single_body("{ns}"), NewSong)

    def test_new_page_renders(self):
        assert "cp-new-page" in chordpro_to_html("{new_page}")

    def test_column_break_renders(self):
        assert "cp-column-break" in chordpro_to_html("{column_break}")

    def test_new_song_renders_hr(self):
        assert "cp-new-song" in chordpro_to_html("{new_song}")

    def test_columns_renders_data_count(self):
        result = chordpro_to_html("{col: 2}")
        assert 'data-count="2"' in result


# ---------------------------------------------------------------------------
# Appearance toggle directives
# ---------------------------------------------------------------------------


class TestAppearanceToggles:
    def test_grid_on(self):
        assert isinstance(_single_body("{grid}"), GridOn)

    def test_grid_on_short_form(self):
        assert isinstance(_single_body("{g}"), GridOn)

    def test_grid_off(self):
        assert isinstance(_single_body("{no_grid}"), GridOff)

    def test_grid_off_short_form(self):
        assert isinstance(_single_body("{ng}"), GridOff)

    def test_grid_on_renders(self):
        assert "cp-grid-on" in chordpro_to_html("{grid}")

    def test_grid_off_renders(self):
        assert "cp-grid-off" in chordpro_to_html("{no_grid}")


# ---------------------------------------------------------------------------
# New section types from spec
# ---------------------------------------------------------------------------


class TestNewSectionTypes:
    def test_start_of_grid(self):
        assert isinstance(_single_body("{start_of_grid}"), Grid)

    def test_start_of_grid_short_form(self):
        assert isinstance(_single_body("{sog}"), Grid)

    def test_grid_section_kind(self):
        section = _single_body("{sog}")
        assert section.kind == "grid"

    def test_start_of_abc(self):
        assert isinstance(_single_body("{start_of_abc}"), Abc)

    def test_start_of_ly(self):
        assert isinstance(_single_body("{start_of_ly}"), Lilypond)

    def test_start_of_svg(self):
        assert isinstance(_single_body("{start_of_svg}"), Svg)

    def test_start_of_textblock(self):
        assert isinstance(_single_body("{start_of_textblock}"), TextBlock)

    @pytest.mark.parametrize(
        "cls, kind, start, end",
        [
            (Grid, "grid", "{sog}", "{eog}"),
            (Abc, "abc", "{start_of_abc}", "{end_of_abc}"),
            (Lilypond, "ly", "{start_of_ly}", "{end_of_ly}"),
            (Svg, "svg", "{start_of_svg}", "{end_of_svg}"),
            (TextBlock, "textblock", "{start_of_textblock}", "{end_of_textblock}"),
        ],
    )
    def test_section_kind_and_closes(self, cls, kind, start, end):
        song = parse(f"{start}\nline\n{end}\nafter")
        assert isinstance(song.body[0], cls)
        assert song.body[0].kind == kind
        assert len(song.body) == 2  # section + trailing lyric

    def test_grid_section_renders(self):
        result = chordpro_to_html("{sog}\nline\n{eog}")
        assert 'data-section="grid"' in result

    def test_abc_section_renders(self):
        result = chordpro_to_html("{start_of_abc}\n|: C D :|{end_of_abc}")
        assert 'data-section="abc"' in result


# ---------------------------------------------------------------------------
# SongMeta dataclass
# ---------------------------------------------------------------------------


class TestSongMeta:
    def test_default_values(self):
        m = SongMeta()
        assert m.title is None
        assert m.year is None
        assert m.capo is None
        assert m.duration is None
        assert m.subtitle == []
        assert m.artist == []
        assert m.key == []
        assert m.time == []
        assert m.tempo == []
        assert m.meta == {}

    def test_song_has_meta_field(self):
        assert hasattr(Song(), "meta")
        assert isinstance(Song().meta, SongMeta)

    def test_meta_independent_per_instance(self):
        a, b = SongMeta(), SongMeta()
        a.artist.append("Test")
        assert b.artist == []
