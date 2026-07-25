"""Fabriques de dossiers pour les tests d'acceptation."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from tpt_app.core.models import (
    Dossier,
    DossierML36,
    DossierML37,
    Periode,
    Salarie,
    REGIME_ML36,
    REGIME_ML37,
)


def d(jour: int, mois: int = 7, annee: int = 2025) -> dt.date:
    return dt.date(annee, mois, jour)


def periode(debut: int, fin: int, motif_principal: str = "", motif_absence: str = "",
            mois: int = 7, annee: int = 2025) -> Periode:
    return Periode(
        motif_principal=motif_principal,
        motif_absence=motif_absence,
        date_debut=d(debut, mois, annee),
        date_fin=d(fin, mois, annee),
    )


def salarie() -> Salarie:
    return Salarie(
        siret="12345678900011",
        num_secu="180077512345678",
        matricule="A12345",
        nom="DUPONT",
        prenom="Jean",
        djt=d(1),
    )


@pytest.fixture
def dossier_test1() -> Dossier:
    """§8 — Test 1 : ML36, ventilation des primes, mois de 30 jours."""
    ml36 = DossierML36(
        salarie=salarie(),
        mois=dt.date(2025, 7, 1),
        nb_jours_mois=30,
        taux_initial=Decimal(1),
        taux_tpt=Decimal("0.4"),
        tmf_100=Decimal(2500),
        pua=Decimal(400),
        pua_percue=Decimal(250),
        autres_primes=Decimal(180),
        periodes=[
            periode(1, 8, REGIME_ML36),
            periode(11, 18, REGIME_ML36, "Maladie"),
            periode(21, 28, REGIME_ML36),
        ],
    )
    return Dossier(regime=REGIME_ML36, ml36=ml36)


@pytest.fixture
def dossier_test2() -> Dossier:
    """§8 — Test 2 : ML37, ventilation et libellés, mois de 31 jours."""
    ml37 = DossierML37(
        salarie=salarie(),
        mois=dt.date(2025, 7, 1),
        nb_jours_mois=31,
        taux_initial=Decimal(1),
        taux_tpt=Decimal("0.5"),
        tmf_100=Decimal(3000),
        pua=Decimal(400),
        pua_percue=Decimal(250),
        autres_primes=Decimal(180),
        periodes=[
            periode(1, 5, REGIME_ML37),
            periode(6, 10, "CA"),
            periode(11, 15, REGIME_ML37, "MALADIE"),
            periode(16, 16, REGIME_ML37, "JEM"),
            periode(17, 20, REGIME_ML37, "Abs sans solde"),
            periode(21, 31, REGIME_ML37),
        ],
    )
    return Dossier(regime=REGIME_ML37, ml37=ml37)
