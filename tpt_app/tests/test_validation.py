"""Contrôles de saisie et messages d'erreur (§7)."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from tpt_app.core import moteur
from tpt_app.core.models import (
    Dossier,
    DossierML35,
    DossierML36,
    Periode,
    REGIME_ML35,
    REGIME_ML36,
    Salarie,
)
from tpt_app.core.validation import AVERTISSEMENT, controler

from .conftest import periode, salarie


def _dossier(**remplacements) -> Dossier:
    defauts = dict(
        salarie=salarie(),
        mois=dt.date(2025, 7, 1),
        nb_jours_mois=31,
        taux_initial=Decimal(1),
        taux_tpt=Decimal("0.4"),
        tmf_100=Decimal(2500),
        periodes=[periode(1, 8, REGIME_ML36)],
    )
    defauts.update(remplacements)
    return Dossier(regime=REGIME_ML36, ml36=DossierML36(**defauts))


def champs(anomalies) -> set[str]:
    return {a.champ for a in anomalies}


def test_dossier_valide_ne_produit_aucune_anomalie():
    assert controler(_dossier()) == []


def test_chevauchement_de_periodes():
    anomalies = controler(_dossier(periodes=[
        periode(1, 10, REGIME_ML36),
        periode(8, 15, REGIME_ML36),
    ]))
    assert any("chevauchement" in a.message.lower() for a in anomalies)
    assert "periode.2.date_debut" in champs(anomalies)


def test_dates_hors_du_mois_traite():
    anomalies = controler(_dossier(periodes=[periode(1, 8, REGIME_ML36, mois=8)]))
    assert any("sort du mois traité" in a.message for a in anomalies)


def test_date_de_fin_avant_date_de_debut():
    anomalies = controler(_dossier(periodes=[
        Periode(motif_principal=REGIME_ML36, date_debut=dt.date(2025, 7, 10),
                date_fin=dt.date(2025, 7, 2)),
    ]))
    assert any("précède la date de début" in a.message for a in anomalies)


def test_date_de_fin_manquante():
    anomalies = controler(_dossier(periodes=[
        Periode(motif_principal=REGIME_ML36, date_debut=dt.date(2025, 7, 10)),
    ]))
    assert "periode.1.date_fin" in champs(anomalies)


def test_date_de_debut_manquante():
    anomalies = controler(_dossier(periodes=[
        Periode(motif_principal=REGIME_ML36, date_fin=dt.date(2025, 7, 10)),
    ]))
    assert "periode.1.date_debut" in champs(anomalies)


def test_motif_principal_manquant_ou_inconnu():
    assert "periode.1.motif_principal" in champs(controler(_dossier(
        periodes=[periode(1, 8, "")])))
    anomalies = controler(_dossier(periodes=[periode(1, 8, "ML37")]))
    assert any("inconnu pour ML36" in a.message for a in anomalies)


def test_motif_d_absence_inconnu():
    anomalies = controler(_dossier(periodes=[periode(1, 8, REGIME_ML36, "JEM")]))
    assert any("motif d'absence" in a.message for a in anomalies)


def test_somme_des_jours_superieure_au_mois():
    anomalies = controler(_dossier(nb_jours_mois=30, periodes=[
        periode(1, 20, REGIME_ML36),
        periode(21, 31, REGIME_ML36),
    ]))
    assert any("dépasse le nombre de jours du mois" in a.message for a in anomalies)


def test_taux_incoherents():
    assert "taux_tpt" in champs(controler(_dossier(taux_tpt=Decimal("1.4"))))
    assert "taux_initial" in champs(controler(_dossier(taux_initial=Decimal(0))))

    anomalies = controler(_dossier(taux_initial=Decimal("0.5"), taux_tpt=Decimal("0.8")))
    depassement = [a for a in anomalies if a.champ == "taux_tpt"]
    assert depassement and depassement[0].gravite == AVERTISSEMENT
    assert not depassement[0].bloquante


def test_identite_incomplete():
    anomalies = controler(_dossier(salarie=Salarie(num_secu="1800775")))
    assert {"nom", "matricule", "num_secu"} <= champs(anomalies)
    assert any("15 caractères" in a.message for a in anomalies)


def test_mois_et_nombre_de_jours():
    assert "mois" in champs(controler(_dossier(mois=None)))
    assert "nb_jours_mois" in champs(controler(_dossier(nb_jours_mois=45)))

    # Juillet compte 31 jours : en saisir 30 est un avertissement, pas un blocage.
    anomalies = [a for a in controler(_dossier(nb_jours_mois=30))
                 if a.champ == "nb_jours_mois"]
    assert anomalies and anomalies[0].gravite == AVERTISSEMENT


def test_nombre_de_periodes_superieur_au_maximum():
    anomalies = controler(_dossier(periodes=[
        Periode(motif_principal=REGIME_ML36) for _ in range(11)
    ]))
    assert any("n'accepte que 10 périodes" in a.message for a in anomalies)


def test_ml35_limite_a_huit_periodes():
    dossier = Dossier(regime=REGIME_ML35, ml35=DossierML35(
        salarie=salarie(), mois=dt.date(2025, 7, 1), nb_jours_mois=31,
        periodes=[Periode(motif_principal="ML35") for _ in range(9)],
    ))
    assert any("n'accepte que 8 périodes" in a.message for a in controler(dossier))


def test_resultat_dossier_expose_la_validite():
    valide = moteur.calculer(_dossier())
    assert valide.valide and valide.exportable

    invalide = moteur.calculer(_dossier(salarie=Salarie()))
    assert not invalide.valide and not invalide.exportable
