"""Derrière un proxy qui termine TLS, les pages lient leurs CSS en HTTPS.

Les templates lient leurs CSS par `url_for('static', …)`, une URL absolue
construite avec le schéma que voit l'application. Derrière le proxy d'App
Service, ce schéma est `http`, sauf si uvicorn croit `X-Forwarded-Proto`, ce
qu'il ne fait que pour les adresses de `FORWARDED_ALLOW_IPS`. Les requêtes de
test viennent de `testclient` : comme le proxy vu du conteneur, jamais de
`127.0.0.1`.
"""

import asyncio
import re
from pathlib import Path

import uvicorn

from oceens import main

DOCKERFILE = Path(__file__).resolve().parents[1] / "Dockerfile"

BEHIND_TLS = {"x-forwarded-proto": "https", "x-forwarded-for": "203.0.113.7"}


def served_by_run(monkeypatch, forwarded_allow_ips):
    """L'application telle que `run()` la sert, avec ce FORWARDED_ALLOW_IPS."""
    if forwarded_allow_ips is None:
        monkeypatch.delenv("FORWARDED_ALLOW_IPS", raising=False)
    else:
        monkeypatch.setenv("FORWARDED_ALLOW_IPS", forwarded_allow_ips)
    config = uvicorn.Config("oceens.main:app", **main.SERVER_OPTIONS)
    config.load()
    return config.loaded_app


def stylesheets(app, headers):
    """Les CSS que lie la page d'accueil, servie à `testclient`."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"oceens.example")]
        + [(name.encode(), value.encode()) for name, value in headers.items()],
        "client": ("testclient", 50000),
        "server": ("oceens.example", 80),
    }
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    asyncio.run(app(scope, receive, send))
    assert sent[0]["status"] == 200
    page = b"".join(message.get("body", b"") for message in sent[1:]).decode()
    links = re.findall(r'href="([^"]*\.css)"', page)
    assert links
    return links


def image_forwarded_allow_ips():
    """La valeur de FORWARDED_ALLOW_IPS que fixe l'image."""
    match = re.search(r'FORWARDED_ALLOW_IPS="([^"]*)"', DOCKERFILE.read_text())
    assert match, "le Dockerfile ne fixe pas FORWARDED_ALLOW_IPS"
    return match.group(1)


def test_the_image_links_its_css_over_https_behind_a_tls_proxy(monkeypatch):
    app = served_by_run(monkeypatch, image_forwarded_allow_ips())
    for link in stylesheets(app, BEHIND_TLS):
        assert link.startswith("https://"), link


def test_an_untrusted_proxy_is_not_believed(monkeypatch):
    app = served_by_run(monkeypatch, None)
    for link in stylesheets(app, BEHIND_TLS):
        assert link.startswith("http://"), link


def test_a_plain_http_request_still_links_over_http(monkeypatch):
    app = served_by_run(monkeypatch, image_forwarded_allow_ips())
    for link in stylesheets(app, {}):
        assert link.startswith("http://"), link
