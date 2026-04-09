import pytest
from flask import Flask
from chordpro import ChordPro


@pytest.fixture()
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    ChordPro(app)
    return app


@pytest.fixture()
def app_ctx(app):
    with app.app_context():
        yield app


@pytest.fixture()
def req_ctx(app):
    """Request context with default (standard) notation."""
    with app.test_request_context("/"):
        yield app
