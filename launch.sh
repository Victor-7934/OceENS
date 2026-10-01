#!/bin/bash

cd /home/mde-admin/OceENS

if ! command -v uv > /dev/null; then
	echo "uv not found. Install it: https://docs.astral.sh/uv/getting-started/installation/"
	exit 1
fi

# Crée ou met à jour .venv/ depuis uv.lock, avec l'interpréteur de .python-version
uv sync --locked

# Les points d'entrée installés (.venv/bin/oceens, .venv/bin/oceens-summaries)
# ne dépendent pas du dossier courant ; PYTHONUNBUFFERED remplace `python -u`.
if pgrep -f "\.venv/bin/oceens$" > /dev/null; then
	echo "Website already launched"
else

	echo "Launching Website with screen"
	screen -d -m bash -c "PYTHONUNBUFFERED=1 .venv/bin/oceens 2> >(tee -a app.error) | tee -a app.log"
fi

if pgrep -f "\.venv/bin/oceens-summaries$" > /dev/null; then
	echo "Summaries generator already launched"
else

	echo "Launching Summaries generator with screen"
	screen -d -m bash -c "PYTHONUNBUFFERED=1 .venv/bin/oceens-summaries 2> >(tee -a summaries.error) | tee -a summaries.log"
fi




