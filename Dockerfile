FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.10.2 /uv /uvx /bin/
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# uv utilise le Python de l'image, sans en télécharger un autre
ENV UV_PYTHON_DOWNLOADS=0 UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

# Dépendances seules d'abord (couche mise en cache tant que uv.lock ne change pas)
COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --locked --no-install-project

# Package oceens (src/oceens/ : code, templates, static, import)
COPY ./src src
RUN uv sync --locked

ENV PATH="/app/.venv/bin:$PATH"

# Le package est installé, pas exécuté depuis un clone : la base reste dans
# /app/database, à monter comme volume pour persister la base SQLite entre les
# redémarrages. Le dossier est créé automatiquement par database.py au démarrage.
# Le fichier .env ne doit PAS être copié dans l'image : fournir les secrets via
# --env-file .env au lancement (docker run) ou via les variables d'environnement.
ENV LOCAL_DATABASE_DIR=/app/database

CMD ["oceens"]
