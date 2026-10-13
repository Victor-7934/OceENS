"""Les fichiers que lit le seed entrent dans le contexte de build Docker.

Une image lancée sans volume, comme sur App Service, ne voit que ce que
`.dockerignore` laisse passer : un fichier du seed écarté y manque à chaque
démarrage.
"""

from fnmatch import fnmatch
from pathlib import Path

import pytest

from oceens.core.seed import SEEDED_SURVEYS
from oceens.seed_data import DATA_DIR

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SEED_FILES = [DATA_DIR / "Program_list.csv"] + [
    DATA_DIR / survey["answers_file"] for survey in SEEDED_SURVEYS
]


def is_excluded(path):
    """Le chemin, relatif à la racine, est-il écarté par `.dockerignore` ?

    Comme Docker : la dernière règle qui correspond l'emporte, `!` réintègre, et
    écarter un dossier écarte tout ce qu'il contient.
    """
    lines = (PROJECT_ROOT / ".dockerignore").read_text().splitlines()
    patterns = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
    parts = path.split("/")
    candidates = ["/".join(parts[: i + 1]) for i in range(len(parts))]
    excluded = False
    for pattern in patterns:
        negated = pattern.startswith("!")
        pattern = pattern.removeprefix("!").strip("/")
        if any(fnmatch(candidate, pattern) for candidate in candidates):
            excluded = not negated
    return excluded


@pytest.mark.parametrize("seed_file", SEED_FILES, ids=lambda path: path.name)
def test_seed_file_is_in_the_image(seed_file):
    assert seed_file.exists()
    assert not is_excluded(seed_file.relative_to(PROJECT_ROOT).as_posix())
