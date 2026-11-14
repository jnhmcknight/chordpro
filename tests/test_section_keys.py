"""Tests for sections played in a key of their own: song_parts,
transpose_parts, shift_key, transpose_song with keyed sections, and how the
renderers name and label them (``notation=``)."""

import pytest

from chordpro.models import (
    Bridge,
    ChordLine,
    Chorus,
    ChorusRef,
    LyricLine,
    Segment,
    Song,
    SongMeta,
    Svg,
    Verse,
)
from chordpro.parser import (
    build_key_semi_to_name,
    format_key,
    parse,
    shift_key,
    song_parts,
    transpose_parts,
    transpose_song,
)
from chordpro.renderers import HtmlRenderer, render, render_many

SONG = """\
{title: Up a step}
{key: G}
{start_of_verse}
[G]Line one [C]here [D/F#]now
{end_of_verse}
{start_of_chorus}
[C]Sing [G]it [Em]out
{end_of_chorus}
{start_of_bridge: Bridge}
[Am]Down [D]low
{end_of_bridge}
{chorus: Last chorus}
"""


def chords(section) -> list[str]:
    return [
        seg.chord
        for line in section.lines
        if isinstance(line, ChordLine)
        for seg in line.segments
        if seg.chord
    ]


# ---------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------


class TestSongParts:
    def test_sections_and_chorus_refs_in_order(self):
        parts = song_parts(parse(SONG))
        assert [type(p) for p in parts] == [Verse, Chorus, Bridge, ChorusRef]

    def test_loose_lines_are_not_parts(self):
        song = parse("[G]Loose line\n{start_of_verse}\n[C]Verse\n{end_of_verse}")
        assert [type(p) for p in song_parts(song)] == [Verse]

    def test_sections_without_chords_to_play_are_not_parts(self):
        song = parse(
            "{start_of_svg}\n<svg/>\n{end_of_svg}\n{start_of_tab}\ne|--|\n{end_of_tab}"
        )
        parts = song_parts(song)
        assert [p.kind for p in parts] == ["tab"]
        assert not any(isinstance(p, Svg) for p in parts)


class TestShiftKey:
    @pytest.mark.parametrize(
        "key, semitones, expected",
        [
            ("G", 2, "A"),
            ("G", 1, "A♭"),
            ("B", 1, "C"),
            ("C", -1, "B"),
            ("Am", 1, "B♭m"),
            ("Em", 2, "F♯m"),
            ("Bb", 2, "C"),
        ],
    )
    def test_shift(self, key, semitones, expected):
        assert shift_key(key, semitones) == expected


# ---------------------------------------------------------------------------
# transpose_parts
# ---------------------------------------------------------------------------


class TestTransposeParts:
    def test_only_the_given_part_is_transposed(self):
        song = transpose_parts(parse(SONG), {1: "A"})
        verse, chorus, bridge = song.body[:3]
        assert chords(verse) == ["G", "C", "D/F#"]  # as written
        assert chords(chorus) == ["D", "A", "F♯m"]
        assert chorus.key == "A"
        assert verse.key is None and bridge.key is None

    def test_song_key_is_unchanged(self):
        song = transpose_parts(parse(SONG), {0: "A"})
        assert song.meta.key == ["G"]

    def test_original_is_not_changed(self):
        original = parse(SONG)
        transpose_parts(original, {1: "A"})
        assert chords(original.body[1]) == ["C", "G", "Em"]
        assert original.body[1].key is None

    def test_spelled_for_the_parts_key(self):
        song = transpose_parts(parse(SONG), {1: "A♭"})
        assert chords(song.body[1]) == ["D♭", "A♭", "Fm"]

    def test_chorus_ref_is_written_out(self):
        song = transpose_parts(parse(SONG), {3: "A"})
        last = song.body[3]
        assert isinstance(last, Chorus)
        assert last.label == "Last chorus"
        assert last.key == "A"
        assert chords(last) == ["D", "A", "F♯m"]
        # The chorus it copies stays as it was
        assert chords(song.body[1]) == ["C", "G", "Em"]
        assert song.body[1].key is None

    def test_chorus_ref_without_label_takes_the_chorus_label(self):
        song = parse(
            "{key: C}\n{start_of_chorus: Refrain}\n[C]Hey\n{end_of_chorus}\n{chorus}"
        )
        last = transpose_parts(song, {1: "D"}).body[1]
        assert isinstance(last, Chorus)
        assert last.label == "Refrain"

    def test_chorus_ref_repeats_the_last_chorus_before_it(self):
        song = parse(
            "{key: C}\n"
            "{start_of_chorus}\n[C]First\n{end_of_chorus}\n"
            "{start_of_chorus}\n[F]Second\n{end_of_chorus}\n"
            "{chorus}"
        )
        last = transpose_parts(song, {2: "D"}).body[2]
        assert chords(last) == ["G"]

    def test_chorus_ref_without_chorus_is_left_alone(self):
        song = parse("{key: C}\n{chorus}")
        assert transpose_parts(song, {0: "D"}).body == [ChorusRef(label=None)]

    def test_unkeyed_chorus_refs_are_kept(self):
        song = transpose_parts(parse(SONG), {0: "A"})
        assert isinstance(song.body[3], ChorusRef)

    def test_several_parts(self):
        song = transpose_parts(parse(SONG), {2: "A", 3: "A"})
        assert song.body[2].key == "A" and song.body[3].key == "A"
        assert chords(song.body[2]) == ["Bm", "E"]

    def test_out_of_range_parts_are_ignored(self):
        original = parse(SONG)
        assert transpose_parts(original, {9: "A"}).body == original.body

    def test_loose_lines_are_not_counted(self):
        song = parse("{key: C}\n[C]Loose\n{start_of_verse}\n[C]Verse\n{end_of_verse}")
        song = transpose_parts(song, {0: "D"})
        assert chords(song.body[1]) == ["D"]
        assert [s.chord for s in song.body[0].segments if s.chord] == ["C"]

    def test_without_song_key_c_is_assumed(self):
        song = parse("{start_of_verse}\n[C]Hey\n{end_of_verse}")
        assert chords(transpose_parts(song, {0: "D"}).body[0]) == ["D"]

    def test_minor_keys(self):
        song = parse("{key: Am}\n{start_of_chorus}\n[Am]Hey [E7]you\n{end_of_chorus}")
        chorus = transpose_parts(song, {0: "B♭m"}).body[0]
        assert chords(chorus) == ["B♭m", "F7"]
        assert chorus.key == "B♭m"

    def test_a_keyed_part_moves_again_from_its_own_key(self):
        song = transpose_parts(parse(SONG), {1: "A"})
        chorus = transpose_parts(song, {1: "B"}).body[1]
        assert chords(chorus) == ["E", "B", "G♯m"]


class TestTransposeSongWithKeyedSections:
    def test_keyed_section_moves_with_the_song(self):
        song = transpose_song(transpose_parts(parse(SONG), {1: "A"}), "A")
        verse, chorus = song.body[:2]
        assert chords(verse) == ["A", "D", "E/G♯"]
        assert chorus.key == "B"
        assert chords(chorus) == ["E", "B", "G♯m"]

    def test_either_order_gives_the_same_chords(self):
        one = transpose_song(transpose_parts(parse(SONG), {1: "A"}), "B♭")
        two = transpose_parts(transpose_song(parse(SONG), "B♭"), {1: "C"})
        assert one.body[1] == two.body[1]

    def test_same_key_leaves_sections_alone(self):
        song = transpose_parts(parse(SONG), {1: "A"})
        assert transpose_song(song, "G").body == song.body


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------


class TestKeyHelpers:
    def test_build_key_semi_to_name_nashville_is_from_the_key(self):
        names = build_key_semi_to_name("nashville", "A")
        assert names[9] == "1" and names[2] == "4"

    def test_build_key_semi_to_name_nashville_without_key_is_from_c(self):
        assert build_key_semi_to_name("nashville", None)[0] == "1"

    def test_build_key_semi_to_name_standard_prefers_the_keys_accidentals(self):
        assert build_key_semi_to_name("standard", "F")[10] == "B♭"
        assert build_key_semi_to_name("standard", "E")[10] == "A♯"

    @pytest.mark.parametrize(
        "key, notation, expected",
        [
            ("A", "standard", "A"),
            ("A", "latin", "La"),
            ("B♭", "german", "B"),
            ("A", "nashville", "A"),
            ("X", "latin", "X"),
        ],
    )
    def test_format_key(self, key, notation, expected):
        assert format_key(key, notation) == expected


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def keyed_song():
    return Song(
        meta=SongMeta(key=["G"]),
        body=[
            Verse(label="Verse", lines=[ChordLine([Segment("G", "One")])]),
            Chorus(
                label="Chorus",
                lines=[ChordLine([Segment("A", "Two"), Segment("B♭", "three")])],
                key="A",
            ),
        ],
    )


class TestHtmlSectionKey:
    def test_data_key_and_label(self):
        html = render(keyed_song())
        assert '<div class="cp-section" data-section="chorus" data-key="A">' in html
        assert (
            '<div class="cp-section-label">Chorus – '
            '<span class="cp-section-key">A</span></div>'
        ) in html

    def test_unkeyed_section_has_neither(self):
        html = render(keyed_song())
        assert '<div class="cp-section" data-section="verse">' in html
        assert html.count("cp-section-key") == 1

    def test_key_named_in_notation(self):
        html = render(keyed_song(), notation="latin")
        assert 'data-key="A"' in html
        assert '<span class="cp-section-key">La</span>' in html

    def test_keyed_section_without_label(self):
        song = Song(body=[Chorus(label="", key="D")])
        assert (
            '<div class="cp-section-label"><span class="cp-section-key">D</span></div>'
            in render(song)
        )

    def test_nashville_numbers_from_each_sections_key(self):
        html = render(keyed_song(), notation="nashville")
        # G in G is 1; A in A is 1, B♭ in A is ♭2
        assert html.count(">1</span>") == 2
        assert ">♭2</span>" in html
        assert '<span class="cp-section-key">A</span>' in html

    def test_standard_spelling_from_each_sections_key(self):
        song = Song(
            meta=SongMeta(key=["E"]),
            body=[
                Verse(label="V", lines=[ChordLine([Segment("A♯", "x")])]),
                Chorus(label="C", lines=[ChordLine([Segment("A♯", "y")])], key="F"),
            ],
        )
        html = render(song, notation="standard")
        assert ">A♯</span>" in html and ">B♭</span>" in html

    def test_without_notation_semi_to_name_is_used_throughout(self):
        names = build_key_semi_to_name("nashville", "G")
        html = render(keyed_song(), names)
        # The chorus's A is 2 from G, as the song's map names it
        assert ">2</span>" in html

    def test_notation_given_to_the_renderer(self):
        html = HtmlRenderer(notation="nashville").render(keyed_song())
        assert ">♭2</span>" in html


class TestTextAndQuillSectionKey:
    def test_text_label(self):
        text = render(keyed_song(), format="text")
        assert "Chorus – A\n" in text
        assert "\nVerse\n" in "\n" + text

    def test_text_nashville(self):
        text = render(keyed_song(), format="text", notation="nashville")
        assert "Chorus – A\n1  b2\n" in text

    def test_quill_label(self):
        ops = render(keyed_song(), format="quill-delta")["ops"]
        assert {"insert": "Chorus – A", "attributes": {"bold": True}} in ops

    def test_quill_many_names_each_song_for_its_key(self):
        other = Song(
            meta=SongMeta(key=["D"]),
            body=[Verse(label="V", lines=[ChordLine([Segment("D", "x")])])],
        )
        ops = render_many(
            [keyed_song(), other], format="quill-delta", notation="nashville"
        )["ops"]
        chords_ = [op["insert"] for op in ops if op.get("attributes", {}).get("chord")]
        assert chords_ == ["1", "1", "♭2", "1"]


class TestHtmlManyNashville:
    def test_each_song_from_its_own_key(self):
        a = Song(meta=SongMeta(key=["G"]), body=[ChordLine([Segment("G", "x")])])
        b = Song(meta=SongMeta(key=["D"]), body=[ChordLine([Segment("D", "y")])])
        html = render_many([a, b], notation="nashville")
        assert html.count(">1</span>") == 2


class TestPdfSectionKey:
    @pytest.fixture(autouse=True)
    def _reportlab(self):
        pytest.importorskip("reportlab", reason="reportlab not installed")

    def test_labels_and_names(self, monkeypatch):
        from chordpro.renderers import PdfRenderer

        labels, names = [], []
        original_label = PdfRenderer._section_label
        original_line = PdfRenderer._chord_line_flowable

        def spy_label(self, section):
            label = original_label(self, section)
            labels.append(label)
            return label

        def spy_line(self, chord_line, semi_to_name, chord_color):
            names.append(
                [
                    semi_to_name[{"G": 7, "A": 9, "B♭": 10}[seg.chord]]
                    for seg in chord_line.segments
                ]
            )
            return original_line(self, chord_line, semi_to_name, chord_color)

        monkeypatch.setattr(PdfRenderer, "_section_label", spy_label)
        monkeypatch.setattr(PdfRenderer, "_chord_line_flowable", spy_line)
        pdf = render_many([keyed_song()], format="pdf", notation="nashville")
        assert pdf[:4] == b"%PDF"
        assert labels == ["Verse", "Chorus – A"]
        assert names == [["1"], ["1", "♭2"]]

    def test_renders(self):
        song = transpose_parts(parse(SONG), {3: "A"})
        assert render(song, format="pdf", notation="standard")[:4] == b"%PDF"


class TestLyricsOnlySections:
    def test_keyed_section_of_lyrics(self):
        song = Song(body=[Verse(label="V", lines=[LyricLine("la")], key="D")])
        assert 'data-key="D"' in render(song)
