try:
    from flask_babel import lazy_gettext as _l
except ImportError:

    def _l(s):
        return s


FLAT = "♭"
SHARP = "♯"
NATURAL = "♮"
DOUBLE_SHARP = "𝄪"
DOUBLE_FLAT = "𝄫"

_CP_SECTION_LABELS = {
    "verse": _l("Verse"),
    "chorus": _l("Chorus"),
    "bridge": _l("Bridge"),
    "prechorus": _l("Pre-Chorus"),
    "pre_chorus": _l("Pre-Chorus"),
    "outro": _l("Outro"),
    "intro": _l("Intro"),
    "tab": _l("Tab"),
    "grid": _l("Grid"),
    "tag": _l("Tag"),
    "interlude": _l("Interlude"),
    "solo": _l("Solo"),
    "instrumental": _l("Instrumental"),
    "abc": _l("ABC Notation"),
    "ly": _l("Lilypond"),
    "svg": _l("SVG"),
    "textblock": _l("Text"),
}

# Official ChordPro spec short-form aliases for section directives.
# Each key is the short directive name; the value is the canonical long form.
# Short forms are expanded before any other parsing logic runs, so start/end
# tags can be any mix of short and long forms.
#
# Spec: https://www.chordpro.org/chordpro/directives-env_verse/
_SHORT_FORM_DIRECTIVES: dict[str, str] = {
    # Section start/end short forms (official spec)
    "sov": "start_of_verse",
    "eov": "end_of_verse",
    "soc": "start_of_chorus",
    "eoc": "end_of_chorus",
    "sob": "start_of_bridge",
    "eob": "end_of_bridge",
    "sot": "start_of_tab",
    "eot": "end_of_tab",
    "sog": "start_of_grid",
    "eog": "end_of_grid",
    # Metadata short forms
    "t": "title",
    "st": "subtitle",
    # Comment short forms
    "ci": "comment_italic",
    # comment_box had "cb" but that conflicts with column_break; cb → column_break wins
    # as comment_box is a legacy directive
    # Layout short forms
    "np": "new_page",
    "npp": "new_physical_page",
    "cb": "column_break",
    "col": "columns",
    "ns": "new_song",
    # Appearance short forms
    "g": "grid",
    "ng": "no_grid",
}

# Nashville Number System: semitone offset from the key tonic → number string.
#
# Diatonic major scale degrees are assigned the plain number (1–7).
# Chromatic (non-diatonic) semitones use the flat/sharp of the nearest
# diatonic degree following common Nashville convention (♯4 for the tritone,
# ♭-prefixes elsewhere).
_NASHVILLE_CHROMATIC: dict[int, str] = {
    0: "1",
    1: "♭2",
    2: "2",
    3: "♭3",
    4: "3",
    5: "4",
    6: "♯4",
    7: "5",
    8: "♭6",
    9: "6",
    10: "♭7",
    11: "7",
}

# Semitone → root name, always using sharps for chromatic notes.
_SHARP_SEMI_TO_NAME: dict[int, str] = {
    0: "C", 1: "C♯", 2: "D", 3: "D♯", 4: "E",
    5: "F", 6: "F♯", 7: "G", 8: "G♯", 9: "A", 10: "A♯", 11: "B",
}

# Semitone → root name, always using flats for chromatic notes.
_FLAT_SEMI_TO_NAME: dict[int, str] = {
    0: "C", 1: "D♭", 2: "D", 3: "E♭", 4: "E",
    5: "F", 6: "G♭", 7: "G", 8: "A♭", 9: "A", 10: "B♭", 11: "B",
}

# Keys (by root name) whose chromatic chords should use flat accidentals.
# Major flat keys: F, B♭, E♭, A♭, D♭, G♭, C♭
# Their relative minors: Dm, Gm, Cm, Fm, B♭m, E♭m, A♭m
_FLAT_PREFERENCE_KEYS: frozenset[str] = frozenset({
    "F", "B♭", "E♭", "A♭", "D♭", "G♭", "C♭",
    "Dm", "Gm", "Cm", "Fm", "B♭m", "E♭m", "A♭m",
})

# Standard notation root names → chromatic semitone (C=0 … B=11)
_STANDARD_NOTE_TO_SEMI = {
    "C": 0,
    "C♯": 1,
    "D♭": 1,
    "D": 2,
    "D♯": 3,
    "E♭": 3,
    "E": 4,
    "F": 5,
    "F♯": 6,
    "G♭": 6,
    "G": 7,
    "G♯": 8,
    "A♭": 8,
    "A": 9,
    "A♯": 10,
    "B♭": 10,
    "B": 11,
}

# Key lookup tables indexed by MajorKey/MinorKey enum integer value.
#
# MajorKey values : A=0  B♭=1  B=2  C=3  C♯=4  D=5  D♯=6  E=7  F=8  F♯=9  G=10  A♭=11
# MinorKey values : F♯m=0  Gm=1  G♯m=2  Am=3  B♭m=4  Bm=5  Cm=6  C♯m=7  Dm=8  D♯m=9  Em=10  Fm=11
#
# key_int 0-11  → major  (index = key_int)
# key_int 12-23 → minor  (index = key_int - 12)
KEY_NAMES = {
    "standard": {
        "major": {
            0: "A",
            1: "B♭",
            2: "B",
            3: "C",
            4: "C♯",
            5: "D",
            6: "D♯",
            7: "E",
            8: "F",
            9: "F♯",
            10: "G",
            11: "A♭",
        },
        "minor": {
            0: "F♯m",
            1: "Gm",
            2: "G♯m",
            3: "Am",
            4: "B♭m",
            5: "Bm",
            6: "Cm",
            7: "C♯m",
            8: "Dm",
            9: "D♯m",
            10: "Em",
            11: "Fm",
        },
    },
    "german": {
        "major": {
            0: "A",
            1: "B",
            2: "H",
            3: "C",
            4: "Cis",
            5: "D",
            6: "Dis",
            7: "E",
            8: "F",
            9: "Fis",
            10: "G",
            11: "As",
        },
        "minor": {
            0: "Fism",
            1: "Gm",
            2: "Gism",
            3: "Am",
            4: "Bm",
            5: "Hm",
            6: "Cm",
            7: "Cism",
            8: "Dm",
            9: "Dism",
            10: "Em",
            11: "Fm",
        },
    },
    "latin": {
        "major": {
            0: "La",
            1: "Si♭",
            2: "Si",
            3: "Do",
            4: "Do♯",
            5: "Re",
            6: "Re♯",
            7: "Mi",
            8: "Fa",
            9: "Fa♯",
            10: "Sol",
            11: "La♭",
        },
        "minor": {
            0: "Fa♯m",
            1: "Solm",
            2: "Sol♯m",
            3: "Lam",
            4: "Si♭m",
            5: "Sim",
            6: "Dom",
            7: "Do♯m",
            8: "Rem",
            9: "Re♯m",
            10: "Mim",
            11: "Fam",
        },
    },
}


def sbp_key_int_to_str(key_int: int | None) -> str | None:
    """Convert a SongbookPro integer key (0-23) to a standard key name string.

    SBP major key ordering: A=0, B♭=1, B=2, C=3, …, G=10, A♭=11
    SBP minor key ordering: F♯m=12, Gm=13, G♯m=14, Am=15, …, Fm=23
    """
    if key_int is None:
        return None
    table = KEY_NAMES["standard"]
    try:
        if key_int >= 12:
            return table["minor"][key_int - 12]
        return table["major"][key_int]
    except (KeyError, TypeError):
        return None


def str_key_to_sbp_int(key_str: str | None) -> int | None:
    """Convert a standard key name string to a SongbookPro integer key (0-23).

    Returns None if the key string is not recognised.
    """
    if not key_str:
        return None
    table = KEY_NAMES["standard"]
    for idx, name in table["major"].items():
        if name == key_str:
            return idx
    for idx, name in table["minor"].items():
        if name == key_str:
            return idx + 12
    return None
