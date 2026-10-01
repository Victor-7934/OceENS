"""Socle applicatif : base de données, authentification, sécurité, seed."""

from oceens.core.security import check_survey_access_and_status

__all__ = ["check_survey_access_and_status"]
