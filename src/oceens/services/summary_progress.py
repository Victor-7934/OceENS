"""Progression des synthèses d'un sondage, comptée une seule fois pour toute l'application.

La table `summaries` sert de file d'attente au daemon. Ce module est le seul à
dire ce que vaut chacune de ses lignes pour un sondage :

- **en attente** : `http_status = 0` ;
- **faite** : pas en attente, et `summary_text` renseigné ;
- **en erreur** : tout le reste, y compris un 200 au texte vide et un
  `http_status` NULL. Ainsi `faites + erreurs + en attente = total`, toujours.

Un sondage est **terminé** quand il a au moins une ligne et plus aucune en
attente, que certaines aient échoué ou non.

Le **temps restant estimé** compte toutes les lignes en attente de la file,
tous sondages confondus, multipliées par la durée typique d'une synthèse. Le
daemon prend les lignes sans ordre : rien ne garantit que celles d'un sondage
passent avant celles des autres, donc l'estimation est un majorant assumé. Elle
ne lit pas l'horloge.

Spec : EPF-MDE/OceENS#150, depuis le Design Document EPF-MDE/OceENS#109.
"""

from dataclasses import dataclass
from datetime import timedelta

from sqlmodel import func, select

from oceens.models import Summary

# Hypothèse B de #109 : durée typique d'une synthèse, *mesurée* sur le
# `metadata_text` d'un job de taille médiane de la base de démo, le
# 25 septembre 2026 (« gemma4:26b … en 18.6s »).
SECONDS_PER_SUMMARY = 20

# Valeur de `Summary.http_status` d'une ligne encore à générer.
PENDING_STATUS = 0


@dataclass(frozen=True)
class SurveyProgress:
    """Où en sont les synthèses d'un sondage."""

    done: int
    total: int
    errors: int
    estimated_time_left: timedelta
    finished: bool


def survey_progress(session, survey_id):
    """Progression des synthèses du sondage `survey_id`.

    Un sondage inconnu ou sans synthèse n'est pas une erreur : total à 0, rien
    à attendre, et pas terminé. Une erreur de base n'est pas rattrapée : elle
    remonte à l'appelant.
    """
    is_pending = Summary.http_status == PENDING_STATUS
    # Un `http_status` NULL n'est pas « en attente » : `coalesce` l'écarte du
    # 0, là où `!= 0` le laisserait à NULL et la ligne hors de tout compte.
    is_not_pending = func.coalesce(Summary.http_status, -1) != PENDING_STATUS
    is_done = is_not_pending & Summary.summary_text.is_not(None)

    total, pending, done = session.exec(
        select(
            func.count(Summary.summary_id),
            func.count(Summary.summary_id).filter(is_pending),
            func.count(Summary.summary_id).filter(is_done),
        ).where(Summary.survey_id == survey_id)
    ).one()

    if pending:
        queued = session.exec(
            select(func.count(Summary.summary_id)).where(is_pending)
        ).one()
    else:
        queued = 0

    return SurveyProgress(
        done=done,
        total=total,
        errors=total - pending - done,
        estimated_time_left=timedelta(seconds=queued * SECONDS_PER_SUMMARY),
        finished=total > 0 and pending == 0,
    )
