"""`survey_progress` : où en sont les synthèses d'un sondage, et combien de temps il reste.

Le nombre vient du Design Document #109, hypothèse D : les synthèses d'un
sondage sont prêtes en 1 h 30 au plus après le clic ; au-delà, seulement avec
un temps estimé affiché. Spec : #150.

La base est en mémoire et passée au module par sa session : ni daemon, ni LLM,
ni horloge.
"""

from datetime import timedelta

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from oceens.models import Summary
from oceens.services import survey_progress

# Hypothèses du groupe (#109).
JOBS_PER_SURVEY = 45  # A
SURVEYS_ON_THE_SAME_EVENING = 10  # C
REQUIREMENT = timedelta(hours=1, minutes=30)  # D


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def queue_pending(session, survey_id, count):
    """Dépose `count` synthèses en attente, comme le clic sur « générer »."""
    session.add_all(Summary(survey_id=survey_id, http_status=0) for _ in range(count))
    session.commit()


def test_one_survey_alone_in_the_queue_is_estimated_within_the_requirement(session):
    queue_pending(session, survey_id=1, count=JOBS_PER_SURVEY)

    assert survey_progress(session, 1).estimated_time_left <= REQUIREMENT


def test_a_campaign_evening_is_estimated_beyond_the_requirement(session):
    for survey_id in range(1, SURVEYS_ON_THE_SAME_EVENING + 1):
        queue_pending(session, survey_id=survey_id, count=JOBS_PER_SURVEY)

    assert survey_progress(session, 1).estimated_time_left > REQUIREMENT
