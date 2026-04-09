"""Tests for the ChordPro Flask extension registration."""

from flask import Flask
from chordpro import ChordPro


def test_init_app_registers_extension(app):
    assert "chordpro" in app.extensions
    assert isinstance(app.extensions["chordpro"], ChordPro)


def test_chordpro_filter_registered(app):
    assert "chordpro" in app.jinja_env.filters


def test_format_key_filter_registered(app):
    assert "format_key" in app.jinja_env.filters


def test_factory_pattern():
    ext = ChordPro()
    app = Flask(__name__)
    ext.init_app(app)
    assert "chordpro" in app.extensions


def test_multiple_apps_independent():
    ext = ChordPro()
    app1 = Flask(__name__)
    app2 = Flask(__name__)
    ext.init_app(app1)
    ext.init_app(app2)
    assert "chordpro" in app1.extensions
    assert "chordpro" in app2.extensions
