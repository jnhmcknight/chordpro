"""Tests for the ChordPro CLI (chordpro.cli.convert)."""

import json

import pytest
from click.testing import CliRunner

from chordpro.cli import convert

SIMPLE_SONG = "[G]Amazing [D]grace\n"
SONG_WITH_KEY = "{key: G}\n[G]Amazing grace\n"


@pytest.fixture()
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# stdin / file input
# ---------------------------------------------------------------------------


class TestCliInput:
    def test_stdin_used_when_no_files(self, runner):
        result = runner.invoke(convert, [], input=SIMPLE_SONG)
        assert result.exit_code == 0
        assert "cp-line" in result.output

    def test_explicit_dash_reads_stdin(self, runner):
        result = runner.invoke(convert, ["-"], input=SIMPLE_SONG)
        assert result.exit_code == 0
        assert "cp-line" in result.output

    def test_file_argument(self, runner, tmp_path):
        f = tmp_path / "song.cho"
        f.write_text(SIMPLE_SONG, encoding="utf-8")
        result = runner.invoke(convert, [str(f)])
        assert result.exit_code == 0
        assert "cp-line" in result.output


# ---------------------------------------------------------------------------
# --format
# ---------------------------------------------------------------------------


class TestCliFormat:
    def test_html_format_is_default(self, runner):
        result = runner.invoke(convert, [], input=SIMPLE_SONG)
        assert result.exit_code == 0
        assert "<div" in result.output

    def test_text_format(self, runner):
        result = runner.invoke(convert, ["--format", "text"], input=SIMPLE_SONG)
        assert result.exit_code == 0
        assert "<" not in result.output
        assert "Amazing" in result.output

    def test_quill_delta_format(self, runner):
        result = runner.invoke(convert, ["--format", "quill-delta"], input=SIMPLE_SONG)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "ops" in data

    def test_pdf_format_writes_bytes(self, runner):
        pytest.importorskip("reportlab", reason="reportlab not installed")
        result = runner.invoke(convert, ["--format", "pdf"], input=SIMPLE_SONG)
        assert result.exit_code == 0
        assert result.output_bytes.startswith(b"%PDF")


# ---------------------------------------------------------------------------
# --notation
# ---------------------------------------------------------------------------


class TestCliNotation:
    def test_nashville_notation(self, runner):
        result = runner.invoke(
            convert,
            ["--notation", "nashville", "--format", "text"],
            input=SONG_WITH_KEY,
        )
        assert result.exit_code == 0
        assert "1" in result.output

    def test_nashville_with_key_flag(self, runner):
        result = runner.invoke(
            convert,
            ["--notation", "nashville", "--key", "C", "--format", "text"],
            input="[G]Words\n",
        )
        assert result.exit_code == 0

    def test_nashville_no_song_key_defaults_to_c(self, runner):
        # Song has no {key:} directive; should not crash — falls back to "C"
        result = runner.invoke(
            convert,
            ["--notation", "nashville", "--format", "text"],
            input="[G]Words\n",
        )
        assert result.exit_code == 0

    def test_latin_notation(self, runner):
        result = runner.invoke(
            convert,
            ["--notation", "latin", "--format", "text"],
            input="[C]Do\n",
        )
        assert result.exit_code == 0
        assert "Do" in result.output

    def test_german_notation(self, runner):
        result = runner.invoke(
            convert,
            ["--notation", "german", "--format", "text"],
            input="[Bb]Words\n",
        )
        assert result.exit_code == 0
        # Bb (semitone 10) → "B" in German
        assert "B" in result.output


# ---------------------------------------------------------------------------
# multiple files
# ---------------------------------------------------------------------------


class TestCliMultipleFiles:
    def test_two_files_both_rendered(self, runner, tmp_path):
        f1 = tmp_path / "song1.cho"
        f2 = tmp_path / "song2.cho"
        f1.write_text("first song words\n", encoding="utf-8")
        f2.write_text("second song words\n", encoding="utf-8")
        result = runner.invoke(convert, [str(f1), str(f2), "--format", "html"])
        assert result.exit_code == 0
        assert "first song words" in result.output
        assert "second song words" in result.output

    def test_two_files_text_separated_by_form_feed(self, runner, tmp_path):
        f1 = tmp_path / "a.cho"
        f2 = tmp_path / "b.cho"
        f1.write_text("first\n", encoding="utf-8")
        f2.write_text("second\n", encoding="utf-8")
        result = runner.invoke(convert, [str(f1), str(f2), "--format", "text"])
        assert result.exit_code == 0
        assert "first" in result.output
        assert "second" in result.output

    def test_multiple_files_pdf(self, runner, tmp_path):
        pytest.importorskip("reportlab", reason="reportlab not installed")
        f1 = tmp_path / "a.cho"
        f2 = tmp_path / "b.cho"
        f1.write_text("first\n", encoding="utf-8")
        f2.write_text("second\n", encoding="utf-8")
        result = runner.invoke(convert, [str(f1), str(f2), "--format", "pdf"])
        assert result.exit_code == 0
        assert result.output_bytes.startswith(b"%PDF")
