from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..constants import FLAT, SHARP
from ..models import Song


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
    """

    def __init__(self, ascii_accidentals: bool = False) -> None:
        self.ascii_accidentals = ascii_accidentals

    def _finalize_chord(self, chord: str) -> str:
        """Apply the accidental style to a fully-converted chord string."""
        if self.ascii_accidentals:
            return chord.replace(SHARP, "#").replace(FLAT, "b")
        return chord

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
    def _make(cls, ascii_accidentals: bool | None) -> "BaseRenderer":
        """Instantiate this renderer, optionally overriding ``ascii_accidentals``.

        When *ascii_accidentals* is ``None`` the class default is used.
        """
        if ascii_accidentals is None:
            return cls()
        return cls(ascii_accidentals=ascii_accidentals)
