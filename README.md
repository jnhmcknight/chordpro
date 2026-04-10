# chordpro

A library that renders [ChordPro](https://www.chordpro.org/)-formatted song content as HTML, plain text, PDF, or Quill Delta, with support for multiple chord notations.

It was originally designed as a [Flask](https://flask.palletsprojects.com/) extension, but can be installed without Flask to use the command-line conversion tool or the Python API directly.

## Installation

```bash
# Command-line tool and Python API only:
pip install chordpro-renderer

# Flask extension (also installs Flask):
pip install chordpro-renderer[flask]

# PDF rendering (also installs reportlab):
pip install chordpro-renderer[pdf]
```

If you use [flask-babel](https://flask-babel.tkte.ch/) for i18n, install the optional extra so section labels are translatable (also installs Flask):

```bash
pip install chordpro-renderer[babel]
```

See [Internationalization](#internationalization) for setup details.

## Flask extension

### Initialization

**Direct:**

```python
from flask import Flask
from chordpro import ChordPro

app = Flask(__name__)
ChordPro(app)
```

**Application factory:**

```python
from chordpro import ChordPro

chordpro = ChordPro()

def create_app():
    app = Flask(__name__)
    chordpro.init_app(app)
    return app
```

### Template filters

The extension registers two Jinja2 filters: `chordpro` and `format_key`.

#### `chordpro`

Converts a ChordPro string to the requested format. Chord roots are translated to the active notation (see [Chord notation](#chord-notation)).

```jinja2
{{ song.content | chordpro }}                  {# HTML (default) #}
{{ song.content | chordpro("text") }}          {# plain text #}
{{ song.content | chordpro("quill-delta") }}   {# Quill Delta dict #}
{{ song.content | chordpro("pdf") }}           {# PDF bytes (requires chordpro[pdf]) #}
```

**Example input:**

```
{start_of_verse}
[G]Amazing [D]grace, how [Em]sweet the [C]sound
{end_of_verse}
```

**Example output (HTML, simplified):**

```html
<div class="cp-section" data-section="verse">
  <div class="cp-section-label">Verse</div>
  <div class="cp-line">
    <span class="cp-unit">
      <span class="cp-chord" data-chord="G">G</span>
      <span class="cp-lyric">Amazing </span>
    </span>
    <span class="cp-unit">
      <span class="cp-chord" data-chord="D">D</span>
      <span class="cp-lyric">grace, how </span>
    </span>
    ...
  </div>
</div>
```

#### `format_key`

Formats a key integer (0–23) as a human-readable key name in the active notation. Keys 0–11 are major; keys 12–23 are minor.

```jinja2
{{ song.key | format_key }}   {# e.g. "C", "F#m" #}
```

Key integer mapping (standard notation):

| `key_int` | Major | `key_int` | Minor |
|-----------|-------|-----------|-------|
| 0 | A | 12 | F#m |
| 1 | Bb | 13 | Gm |
| 2 | B | 14 | G#m |
| 3 | C | 15 | Am |
| 4 | C# | 16 | Bbm |
| 5 | D | 17 | Bm |
| 6 | D# | 18 | Cm |
| 7 | E | 19 | C#m |
| 8 | F | 20 | Dm |
| 9 | F# | 21 | D#m |
| 10 | G | 22 | Em |
| 11 | Ab | 23 | Fm |

### Flask CLI

The extension also registers a `flask chordpro` command group:

```bash
flask chordpro convert song.cho
flask chordpro convert song.cho --format text --notation german
```

## Chord notation

Both filters read `flask.g.notation` at render time. Set it in a `before_request` hook to change how chord roots and key names are displayed.

```python
from flask import g

@app.before_request
def set_notation():
    g.notation = current_user.notation_preference  # e.g. "standard", "german", "latin", "nashville"
```

If `g.notation` is not set, `"standard"` is used.

### Supported notations

| Value | Description | C major becomes |
|-------|-------------|-----------------|
| `"standard"` | English letter names | C |
| `"german"` | German convention (B♭ → B, B → H) | C |
| `"latin"` | Solfège (Do Re Mi…) | Do |
| `"nashville"` | Nashville Number System (relative to key) | 1 |

### Nashville notation

When `g.notation` is `"nashville"`, the filter also reads `g.key` to determine the root. If `g.key` is not set, the song's first `{key:}` metadata value is used, falling back to `"C"`.

```python
@app.before_request
def set_notation():
    g.notation = "nashville"
    g.key = current_user.key_preference  # e.g. "G", "Bb", "Am"
```

## Command-line tool

```bash
# Convert to HTML (default)
chordpro song.cho

# Convert to plain text
chordpro song.cho --format text

# Convert to Quill Delta JSON
chordpro song.cho --format quill-delta

# Use German notation
chordpro song.cho --notation german

# Use Nashville notation (key defaults to song metadata or C)
chordpro song.cho --notation nashville --key G

# Read from stdin
cat song.cho | chordpro -
```

### Multiple files

Pass multiple files to combine them into a single output. For PDF, each song starts on a new page.

```bash
# Combine into a single HTML document
chordpro song1.cho song2.cho song3.cho

# Build a multi-song PDF songbook
chordpro *.cho --format pdf > songbook.pdf

# Combine from stdin
cat song1.cho song2.cho | chordpro -
```

**Options:**

| Option | Short | Choices | Default |
|--------|-------|---------|---------|
| `--format` | `-f` | `html`, `text`, `quill-delta`, `pdf` | `html` |
| `--notation` | `-n` | `standard`, `german`, `latin`, `nashville` | `standard` |
| `--key` | `-k` | any key string (e.g. `C`, `G`, `Bb`) | song metadata or `C` |

> **Nashville + multiple files:** when `--notation nashville` is used with multiple files, pass `--key` explicitly. Without it, the key defaults to the first song's metadata.

## Supported ChordPro directives

### Metadata directives

These populate the `SongMeta` object and produce no output in the body.

| Directive | Short form | Field |
|-----------|------------|-------|
| `{title: …}` | `{t: …}` | `meta.title` |
| `{subtitle: …}` | `{st: …}` | `meta.subtitle` |
| `{artist: …}` | | `meta.artist` |
| `{album: …}` | | `meta.album` |
| `{composer: …}` | | `meta.composer` |
| `{lyricist: …}` | | `meta.lyricist` |
| `{copyright: …}` | | `meta.copyright` |
| `{year: …}` | | `meta.year` |
| `{key: …}` | | `meta.key` |
| `{time: …}` | | `meta.time` |
| `{tempo: …}` | | `meta.tempo` |
| `{duration: …}` | | `meta.duration` |
| `{capo: …}` | | `meta.capo` |
| `{meta: name value}` | | `meta.meta[name]` |
| `{tag: …}` | | `meta.meta["tag"]` |

Fields that may appear multiple times (`subtitle`, `artist`, `key`, etc.) are stored as `list[str]`. Singular fields (`title`, `year`, `duration`, `capo`) are `str | None`.

### Section directives

All section directives accept an optional label override: `{start_of_verse: Verse 2}`.

| Directive | Short form | Section type |
|-----------|------------|--------------|
| `{start_of_verse}` / `{end_of_verse}` | `{sov}` / `{eov}` | `Verse` |
| `{start_of_chorus}` / `{end_of_chorus}` | `{soc}` / `{eoc}` | `Chorus` |
| `{start_of_bridge}` / `{end_of_bridge}` | `{sob}` / `{eob}` | `Bridge` |
| `{start_of_prechorus}` / `{end_of_prechorus}` | | `PreChorus` |
| `{start_of_outro}` / `{end_of_outro}` | | `Outro` |
| `{start_of_intro}` / `{end_of_intro}` | | `Intro` |
| `{start_of_tab}` / `{end_of_tab}` | `{sot}` / `{eot}` | `Tab` |
| `{start_of_grid}` / `{end_of_grid}` | `{sog}` / `{eog}` | `Grid` |
| `{start_of_tag}` / `{end_of_tag}` | | `Tag` |
| `{start_of_interlude}` / `{end_of_interlude}` | | `Interlude` |
| `{start_of_solo}` / `{end_of_solo}` | | `Solo` |
| `{start_of_instrumental}` / `{end_of_instrumental}` | | `Instrumental` |
| `{start_of_abc}` / `{end_of_abc}` | | `Abc` |
| `{start_of_ly}` / `{end_of_ly}` | | `Lilypond` |
| `{start_of_svg}` / `{end_of_svg}` | | `Svg` |
| `{start_of_textblock}` / `{end_of_textblock}` | | `TextBlock` |
| `{start_of_*}` / `{end_of_*}` | | `Section` (generic) |

All sections render as `<div class="cp-section" data-section="<kind>">` in HTML.

### Content directives

| Directive | Short form | HTML output |
|-----------|------------|-------------|
| `{comment: text}` | `{c: text}` | `<div class="cp-comment">` |
| `{comment_italic: text}` | `{ci: text}` | `<div class="cp-comment cp-comment-italic">` |
| `{comment_box: text}` | | `<div class="cp-comment cp-comment-box">` |
| `{highlight: text}` | | `<div class="cp-highlight">` |
| `{chorus}` / `{chorus: label}` | | `<div class="cp-chorus-ref">` |
| `{image: …}` | | `<div class="cp-image" data-raw="…">` |
| `{chord: name}` | | `<div class="cp-chord-diagram" data-chord="…">` |
| `{define: name …}` | | Parsed; no visual output |
| `{transpose: N}` | | `<span class="cp-transpose" data-semitones="N" hidden>` |

### Layout directives

| Directive | Short form | HTML output |
|-----------|------------|-------------|
| `{new_page}` | `{np}` | `<div class="cp-new-page">` |
| `{new_physical_page}` | `{npp}` | `<div class="cp-new-physical-page">` |
| `{column_break}` | `{cb}` | `<div class="cp-column-break">` |
| `{columns: N}` | `{col: N}` | `<div class="cp-columns" data-count="N">` |
| `{grid}` | `{g}` | `<span class="cp-grid-on" hidden>` |
| `{no_grid}` | `{ng}` | `<span class="cp-grid-off" hidden>` |
| `{new_song}` | `{ns}` | `<hr class="cp-new-song">` |

All other directives are silently ignored.

## CSS classes

Style the rendered HTML output with these classes:

| Class | Element |
|-------|---------|
| `cp-song` | Wrapper for a single song in multi-song `render_many()` HTML output (`div`) |
| `cp-section` | Section wrapper (`div`); `data-section` holds the kind |
| `cp-section-label` | Section heading (`div`) |
| `cp-line` | A line containing chords and lyrics (`div`) |
| `cp-unit` | A chord+lyric pair (`span`) |
| `cp-chord` | Chord name (`span`); `data-chord` holds the standard-notation root |
| `cp-lyric` | Lyric beneath a chord (`span`) |
| `cp-lyric-only` | Lyric with no chord above it (`span`) |
| `cp-lyric-line` | A plain lyric line with no chords (`div`) |
| `cp-break` | An empty line between paragraphs (`div`) |
| `cp-comment` | A comment directive (`div`) |
| `cp-comment-italic` | Added alongside `cp-comment` for `{comment_italic}` |
| `cp-comment-box` | Added alongside `cp-comment` for `{comment_box}` |
| `cp-highlight` | A `{highlight}` directive (`div`) |
| `cp-chorus-ref` | A `{chorus}` reference directive (`div`) |
| `cp-chorus-ref-label` | Label inside a chorus reference (`span`) |
| `cp-image` | An `{image}` directive (`div`); `data-raw` holds the full value |
| `cp-chord-diagram` | A `{chord}` directive (`div`); `data-chord` holds the chord name |
| `cp-transpose` | A `{transpose}` directive (`span`, `hidden`); `data-semitones` holds the offset |
| `cp-new-page` | A `{new_page}` directive (`div`) |
| `cp-new-physical-page` | A `{new_physical_page}` directive (`div`) |
| `cp-column-break` | A `{column_break}` directive (`div`) |
| `cp-columns` | A `{columns}` directive (`div`); `data-count` holds the count |
| `cp-grid-on` | A `{grid}` directive (`span`, `hidden`) |
| `cp-grid-off` | A `{no_grid}` directive (`span`, `hidden`) |
| `cp-new-song` | A `{new_song}` directive (`hr`) |

## Public API

All public symbols are importable directly from `chordpro`.

### Parsing

```python
from chordpro import parse, Song, SongMeta

song = parse(content)   # returns a Song dataclass
song.meta.title         # str | None
song.meta.artist        # list[str]
song.meta.key           # list[str]
song.body               # list of SongItem (sections and lines)
```

### Rendering a single song

```python
from chordpro import render, build_chord_semi_to_name, build_nashville_semi_to_name, key_to_semitone

semi_to_name = build_chord_semi_to_name("latin")
html  = render(song, semi_to_name, format="html")
text  = render(song, semi_to_name, format="text")
delta = render(song, semi_to_name, format="quill-delta")
pdf   = render(song, semi_to_name, format="pdf")   # bytes; requires chordpro[pdf]

# Nashville
semi_to_name = build_nashville_semi_to_name(key_to_semitone("G"))
html = render(song, semi_to_name)
```

Backward-compatible one-shot helpers are also available:

```python
from chordpro import chordpro_to_html, render_html

html = chordpro_to_html(content, semi_to_name)   # parse + render in one call
html = render_html(song, semi_to_name)
```

### Rendering multiple songs

Use `render_many()` to combine a list of `Song` objects into a single output. Songs are merged in order with format-appropriate separators.

```python
from chordpro import parse, render_many, build_chord_semi_to_name

songs = [parse(open(f).read()) for f in ["song1.cho", "song2.cho", "song3.cho"]]
semi_to_name = build_chord_semi_to_name("standard")

html  = render_many(songs, semi_to_name, format="html")         # each song in <div class="cp-song">
text  = render_many(songs, semi_to_name, format="text")         # songs joined by form-feed (\f)
delta = render_many(songs, semi_to_name, format="quill-delta")  # page_break op between songs
pdf   = render_many(songs, semi_to_name, format="pdf")          # new page per song (bytes)

with open("songbook.pdf", "wb") as f:
    f.write(pdf)
```

| Format | Separator |
|--------|-----------|
| `"html"` | Each song wrapped in `<div class="cp-song">` |
| `"text"` | Songs joined by a form-feed character (`\f`) |
| `"quill-delta"` | A `{"insert": "\n", "attributes": {"page_break": true}}` op between songs |
| `"pdf"` | A hard page break (`PageBreak`) between songs |

Custom renderers that do not override `render_many()` receive a `list` of individual `render()` results.

### PDF rendering

`PdfRenderer` is built in and registered as `"pdf"`. It requires the `reportlab` package (`pip install chordpro[pdf]`).

```python
from chordpro import parse, render, render_many

# Single song
song = parse(open("song.cho").read())
pdf_bytes = render(song, format="pdf")

# Multiple songs — each starts on a new page
songs = [parse(open(f).read()) for f in ["song1.cho", "song2.cho"]]
pdf_bytes = render_many(songs, format="pdf")

with open("songbook.pdf", "wb") as f:
    f.write(pdf_bytes)
```

The rendered PDF includes a header with title, subtitle, artist, and key metadata. Each section is labelled. Chord lines use the classic two-row layout — chords printed in blue directly above the corresponding lyric syllables, columns aligned by segment width. `{new_page}` emits a hard page break within a song; `render_many()` inserts a page break between songs.

You can subclass `PdfRenderer` to adjust fonts, sizes, margins, or page size:

```python
from reportlab.lib.pagesizes import A4
from chordpro import PdfRenderer

class MyRenderer(PdfRenderer):
    PAGE_SIZE = A4
    MARGIN = 1.5        # inches
    LYRIC_SIZE = 12
    CHORD_SIZE = 10
```

#### Unicode font support

The built-in Helvetica fonts used by reportlab are Latin-1 only and cannot render Unicode musical symbols such as ♭, ♯, and ♮. `PdfRenderer` automatically searches common system locations for a Unicode-capable TTF font at render time (DejaVu Sans, Arial Unicode MS, Noto Sans) and uses it when found. If no suitable font is detected, rendering falls back to Helvetica silently.

To use a specific font, set `UNICODE_FONT_PATH` on a subclass:

```python
from chordpro import PdfRenderer

class MyRenderer(PdfRenderer):
    UNICODE_FONT_PATH = "/path/to/DejaVuSans.ttf"
    UNICODE_BOLD_FONT_PATH = "/path/to/DejaVuSans-Bold.ttf"       # optional
    UNICODE_ITALIC_FONT_PATH = "/path/to/DejaVuSans-Oblique.ttf"  # optional
```

`UNICODE_BOLD_FONT_PATH` and `UNICODE_ITALIC_FONT_PATH` are inferred automatically from the regular font path when not set — for example, `DejaVuSans.ttf` → `DejaVuSans-Bold.ttf` and `DejaVuSans-Oblique.ttf`. Set them explicitly if auto-inference does not match your font's naming convention.

Fonts searched automatically (in order):

| Platform | Font |
|----------|------|
| Linux | DejaVu Sans (`/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf` and common variants) |
| macOS (Homebrew) | DejaVu Sans (`/opt/homebrew/opt/font-dejavu/…`) |
| macOS | Arial Unicode MS (`/Library/Fonts/` or `/System/Library/Fonts/Supplemental/`) |
| Windows | Arial (`C:\Windows\Fonts\arial.ttf`) |
| Linux (Noto) | Noto Sans (`/usr/share/fonts/noto/NotoSans-Regular.ttf` and common variants) |

> **Note:** The double-sharp (𝄪) and double-flat (𝄫) symbols sit in the Supplementary Multilingual Plane (U+1D12A / U+1D12B). DejaVu Sans does not cover these glyphs; Noto Music or GNU FreeFont do.

### Custom renderers

Subclass `BaseRenderer`, implement `render()`, and register the class under a name. Once registered, the name works as the `format` argument to `render()`, `render_many()`, and the `chordpro` Jinja2 filter.

```python
from chordpro import BaseRenderer, register_renderer

class SvgRenderer(BaseRenderer):
    def render(self, song, semi_to_name=None):
        ...  # return SVG string

    def render_many(self, songs, semi_to_name=None):
        ...  # return combined output; omit to get list of render() results

register_renderer("svg", SvgRenderer)
```

```jinja2
{{ song.content | chordpro("svg") }}
```

You can also pass a renderer instance directly to the filter:

```jinja2
{{ song.content | chordpro(my_renderer_instance) }}
```

## Internationalization

Section labels (Verse, Chorus, Bridge, etc.) are marked for translation using `flask-babel`'s `lazy_gettext`. The package ships compiled translations for **German** (`de`), **French** (`fr`), and **Spanish** (`es`).

### Enabling translations in your app

Tell flask-babel where to find the chordpro translation catalog by including the package's `translations/` directory alongside your own:

```python
import chordpro
import os

app = Flask(__name__)
babel = Babel(app)

# Merge chordpro's translations with your app's own catalog
chordpro_translations = os.path.join(os.path.dirname(chordpro.__file__), "translations")
app.config["BABEL_TRANSLATION_DIRECTORIES"] = f"{chordpro_translations};translations"
```

With that in place, flask-babel resolves the active locale automatically (via `get_locale`) and the section labels rendered by the `chordpro` Jinja2 filter will be translated accordingly.

### Adding a new language

```bash
# 1. Re-extract strings (keeps existing translations)
pybabel extract -F babel.cfg -o messages.pot .

# 2. Initialize a new locale (e.g. Portuguese)
pybabel init -i messages.pot -d chordpro/translations -l pt

# 3. Fill in the msgstr values in chordpro/translations/pt/LC_MESSAGES/messages.po

# 4. Compile
pybabel compile -d chordpro/translations
```

### Updating after source changes

```bash
pybabel extract -F babel.cfg -o messages.pot .
pybabel update -i messages.pot -d chordpro/translations
pybabel compile -d chordpro/translations
```

## Development

```bash
# Install with dev dependencies
uv sync --group dev

# Run the test suite
uv run pytest
```

## License

MIT
