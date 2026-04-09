from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import Song


class BaseRenderer(ABC):
    """Base class for all ChordPro renderers.

    Subclass and implement ``render()`` to support a new output format, then
    register the subclass with ``register_renderer(name, cls)``.
    """

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
