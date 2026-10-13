"""Chaque réponse dit de quel commit l'image a été construite.

Le déploiement attend que l'app réponde avec le commit qu'il vient de
déployer : un 200 seul peut venir de l'image précédente, qu'App Service sert
tant que la nouvelle n'a pas démarré.
"""

import asyncio

import pytest

from oceens import main


def headers_of(path):
    """Les en-têtes de la réponse de l'application à `GET path`."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"oceens.example")],
        "client": ("testclient", 50000),
        "server": ("oceens.example", 80),
    }
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    asyncio.run(main.app(scope, receive, send))
    return {name.decode().lower(): value.decode() for name, value in sent[0]["headers"]}


@pytest.mark.parametrize("path", ["/", "/no-such-page"], ids=["page", "redirect"])
def test_every_answer_names_the_commit(monkeypatch, path):
    monkeypatch.setattr(main, "REVISION", "756cefc")
    assert headers_of(path)["x-revision"] == "756cefc"
