from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..constants import FLAT, SHARP
from ..models import Song
from ..parser import build_key_semi_to_name, format_key


class BaseRenderer(ABC):
    """Base class for all ChordPro renderers.

    Subclass and implement ``render()`` to support a new output format, then
    register the subclass with ``register_renderer(name, cls)``.

    Parameters
    ----------
    ascii_accidentals:
        When ``True``, sharp and flat symbols in chord names are output as
        ASCII ``#`` and ``b`` respectively.  When ``False`` (the default),
        the proper Unicode symbols ``♯`` and ``♭`` are used.
    notation:
        When given (``"standard"``, ``"nashville"``, ``"german"``,
        ``"latin"``), the renderer names chords itself, for each song's key
        and for each section played in a key of its own (see
        ``transpose_parts``), instead of using the ``semi_to_name`` it is
        passed: Nashville numbers from each one's root, or standard names
        with the accidentals each key prefers.  Section keys are named in it.
    """

    def __init__(
        self, ascii_accidentals: bool = False, notation: str | None = None
    ) -> None:
        self.ascii_accidentals = ascii_accidentals
        self.notation = notation

    def _finalize_chord(self, chord: str) -> str:
        """Apply the accidental style to a fully-converted chord string."""
        if self.ascii_accidentals:
            return chord.replace(SHARP, "#").replace(FLAT, "b")
        return chord

    def _notation(self) -> str | None:
        # A subclass that doesn't call __init__ has none
        return getattr(self, "notation", None)

    def _song_names(self, song: Song, semi_to_name: dict | None) -> dict | None:
        """The chord names for *song*: with a ``notation``, built for its key;
        else *semi_to_name*, as given."""
        notation = self._notation()
        if notation is None:
            return semi_to_name
        return build_key_semi_to_name(
            notation, song.meta.key[0] if song.meta.key else None
        )

    def _section_names(self, section, semi_to_name: dict | None) -> dict | None:
        """The chord names for *section*, given its song's *semi_to_name*:
        with a ``notation``, built for the section's own key if it has one."""
        notation = self._notation()
        key = getattr(section, "key", None)
        if notation is None or not key:
            return semi_to_name
        return build_key_semi_to_name(notation, key)

    def _section_key(self, section) -> str | None:
        """The key *section* is played in, if it is one of its own, named in
        the ``notation`` (standard names in Nashville notation)."""
        key = getattr(section, "key", None)
        if not key:
            return None
        return format_key(key, self._notation() or "standard")

    def _section_label(self, section) -> str:
        """*section*'s label, followed by its own key if it has one:
        ``"Chorus – A"``."""
        key = self._section_key(section)
        if key is None:
            return section.label
        return f"{section.label} – {key}" if section.label else key

    @abstractmethod
    def render(self, song: Song, semi_to_name: dict | None = None) -> Any:
        """Render *song* to the target format.

        ``semi_to_name`` is a semitone→chord-name dict produced by
        ``build_chord_semi_to_name`` or ``build_nashville_semi_to_name``;
        pass ``None`` to keep standard notation.
        """

    def render_many(self, songs: list[Song], semi_to_name: dict | None = None) -> Any:
        """Render multiple *songs* as a single combined output.

        The default implementation returns a list of individual ``render()``
        results.  Built-in renderers override this to produce a single merged
        document — for example a single PDF with page breaks between songs.
        """
        return [self.render(song, semi_to_name) for song in songs]

    @classmethod
    def _make(
        cls, ascii_accidentals: bool | None, notation: str | None = None
    ) -> "BaseRenderer":
        """Instantiate this renderer, optionally overriding ``ascii_accidentals``
        and giving it a ``notation``.

        When *ascii_accidentals* is ``None`` the class default is used.  The
        notation is set after the renderer is made, so that renderers whose
        ``__init__`` doesn't take one can be given one too.
        """
        if ascii_accidentals is None:
            renderer = cls()
        else:
            renderer = cls(ascii_accidentals=ascii_accidentals)
        if notation is not None:
            renderer.notation = notation
        return renderer
