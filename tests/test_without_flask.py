"""The parser and renderers work without Flask, which only the "flask" extra installs."""

import subprocess
import sys


def test_imports_without_flask():
    code = (
        "import sys; sys.modules['flask'] = None\n"
        "import chordpro, chordpro.chordsheet\n"
        "assert chordpro.parse('[G]Hello').body\n"
        "try:\n"
        "    chordpro.ChordPro\n"
        "except ImportError:\n"
        "    pass\n"
        "else:\n"
        "    raise AssertionError('ChordPro imported without Flask')\n"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_extension_with_flask():
    from chordpro import ChordPro
    from chordpro.extensions.flask import ChordPro as Extension

    assert ChordPro is Extension
