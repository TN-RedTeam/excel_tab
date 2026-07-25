"""Tests d'acceptation obligatoires — §8 du cahier des charges.

Tous les montants sont vérifiés au centime. Les valeurs attendues proviennent du
classeur ``CALCULATEUR_TPT_V6_9_attest_Vivinter.xlsx``.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from tpt_app.core import ml36 as moteur_ml36
from tpt_app.core import moteur
from tpt_app.core.arrondi import ZERO, arrondi_centime, format_euro, format_pourcent
from tpt_app.core.attestation import LIBELLE_CONGES, LIBELLE_MALADIE, LIBELLE_SANS_SOLDE
from tpt_app.core.models import (
    Dossier,
    DossierML36,
    DossierML37,
    Periode,
    REGIME_ML36,
    REGIME_ML37,
)

from .conftest import periode, salarie


def centimes(valeurs):
    return [arrondi_centime(v) for v in valeurs]


# --------------------------------------------------------------------------
# Test 1 — ML36, ventilation des primes
# --------------------------------------------------------------------------


def test1_ventilation_autres_primes(dossier_test1):
    resultat = moteur.calculer(dossier_test1)
    quotes = [p.quote_autres_primes for p in resultat.ml36.periodes]

    assert centimes(quotes[:3]) == [Decimal("90.00"), Decimal("0.00"), Decimal("90.00")]
    assert centimes(quotes[3:]) == [Decimal("0.00")] * 7
    assert arrondi_centime(sum(quotes, ZERO)) == Decimal("180.00")


def test1_attestation(dossier_test1):
    lignes = moteur.calculer(dossier_test1).attestation.lignes

    for index in (0, 2):
        ligne = lignes[index]
        assert ligne.source == REGIME_ML36
        assert ligne.libelle is None
        assert arrondi_centime(ligne.montant) == Decimal("391.67")
        assert arrondi_centime(ligne.dont_pua_pfa) == Decimal("125.00")
        assert arrondi_centime(ligne.autres_primes) == Decimal("90.00")
        assert format_pourcent(ligne.taux) == "40,00 %"

    maladie = lignes[1]
    assert maladie.libelle == LIBELLE_MALADIE
    assert maladie.montant is None
    assert maladie.dont_pua_pfa is None
    assert maladie.autres_primes is None
    assert maladie.taux is None

    assert all(ligne.vide for ligne in lignes[3:])


# --------------------------------------------------------------------------
# Test 2 — ML37, ventilation et libellés
# --------------------------------------------------------------------------


def test2_ventilation_pua_percue(dossier_test2):
    resultat = moteur.calculer(dossier_test2)
    quotes = [p.quote_pua_percue for p in resultat.ml37.periodes]
    non_nulles = [q for q in quotes if q != ZERO]

    assert centimes(non_nulles) == [Decimal("78.13"), Decimal("171.87")]
    assert arrondi_centime(sum(quotes, ZERO)) == Decimal("250.00")


def test2_ventilation_autres_primes(dossier_test2):
    resultat = moteur.calculer(dossier_test2)
    quotes = [p.quote_autres_primes for p in resultat.ml37.periodes]
    non_nulles = [q for q in quotes if q != ZERO]

    assert centimes(non_nulles) == [Decimal("56.25"), Decimal("123.75")]
    assert arrondi_centime(sum(quotes, ZERO)) == Decimal("180.00")


def test2_colonne_d(dossier_test2):
    lignes = moteur.calculer(dossier_test2).attestation.lignes
    libelles = [ligne.libelle for ligne in lignes[:6]]

    assert libelles == [
        None,               # période ML37 → un montant
        LIBELLE_CONGES,     # CA
        LIBELLE_MALADIE,    # MALADIE
        LIBELLE_CONGES,     # JEM
        LIBELLE_SANS_SOLDE,  # Abs sans solde
        None,               # période ML37 → un montant
    ]
    assert lignes[0].montant is not None
    assert lignes[5].montant is not None


def test2_colonne_h(dossier_test2):
    lignes = moteur.calculer(dossier_test2).attestation.lignes
    taux = [format_pourcent(ligne.taux) for ligne in lignes]

    assert taux[0] == "50,00 %"
    assert taux[5] == "50,00 %"
    assert [taux[i] for i in (1, 2, 3, 4, 6)] == [""] * 5


# --------------------------------------------------------------------------
# Test 3 — priorité du motif sur le montant
# --------------------------------------------------------------------------


def test3_motif_prime_sur_le_montant():
    """Une période ML36 « Maladie » au montant non nul doit afficher « Maladie ».

    Le cas se produit sur un dossier importé où les dates avaient été saisies sur
    la ligne « période » plutôt que sur la ligne « motif » : la matrice calcule
    alors un montant, que l'attestation doit malgré tout masquer.
    """
    ml36 = DossierML36(
        salarie=salarie(),
        mois=dt.date(2025, 7, 1),
        nb_jours_mois=30,
        taux_tpt=Decimal("0.4"),
        tmf_100=Decimal(2500),
        periodes=[
            Periode(
                motif_principal=REGIME_ML36,
                motif_absence="Maladie",
                date_debut=dt.date(2025, 7, 1),
                date_fin=dt.date(2025, 7, 5),
                dates_sur_ligne_periode=True,
            )
        ],
    )
    dossier = Dossier(regime=REGIME_ML36, ml36=ml36, mode_compatibilite=True)
    resultat = moteur.calculer(dossier)

    montant = resultat.ml36.periodes[0].montant_declare
    assert arrondi_centime(montant) == Decimal("166.67")

    ligne = resultat.attestation.lignes[0]
    assert ligne.libelle == LIBELLE_MALADIE
    assert ligne.montant is None


# --------------------------------------------------------------------------
# Test 4 — sélection ligne par ligne
# --------------------------------------------------------------------------


def test4_selection_ligne_par_ligne():
    """Périodes 1 et 3 dans ML36, période 2 dans ML37 : aucune contamination."""
    ml36 = DossierML36(
        salarie=salarie(),
        mois=dt.date(2025, 7, 1),
        nb_jours_mois=30,
        taux_tpt=Decimal("0.4"),
        tmf_100=Decimal(2500),
        periodes=[
            periode(1, 8, REGIME_ML36),
            Periode(motif_principal=REGIME_ML36),          # période 2 laissée vide
            periode(21, 28, REGIME_ML36),
        ],
    )
    ml37 = DossierML37(
        salarie=salarie(),
        mois=dt.date(2025, 7, 1),
        nb_jours_mois=30,
        taux_tpt=Decimal("0.5"),
        tmf_100=Decimal(3000),
        periodes=[
            Periode(motif_principal=REGIME_ML37),          # période 1 laissée vide
            periode(11, 18, REGIME_ML37),
        ],
    )
    dossier = Dossier(regime=REGIME_ML36, ml36=ml36, ml37=ml37)
    resultat = moteur.calculer(dossier)
    lignes = resultat.attestation.lignes

    assert [ligne.source for ligne in lignes[:3]] == [REGIME_ML36, REGIME_ML37, REGIME_ML36]
    assert [format_pourcent(ligne.taux) for ligne in lignes[:3]] == [
        "40,00 %", "50,00 %", "40,00 %",
    ]

    # Chaque montant provient bien de sa propre matrice.
    assert arrondi_centime(lignes[0].montant) == arrondi_centime(
        resultat.ml36.periodes[0].montant_declare
    )
    assert arrondi_centime(lignes[1].montant) == arrondi_centime(
        resultat.ml37.periodes[1].montant_declare
    )
    assert arrondi_centime(lignes[2].montant) == arrondi_centime(
        resultat.ml36.periodes[2].montant_declare
    )
    assert lignes[1].montant != lignes[0].montant


# --------------------------------------------------------------------------
# Test 5 — masquage des zéros
# --------------------------------------------------------------------------


def test5_masquage_des_zeros():
    ml36 = DossierML36(
        salarie=salarie(),
        mois=dt.date(2025, 7, 1),
        nb_jours_mois=30,
        taux_tpt=Decimal("0.4"),
        tmf_100=Decimal(2500),
        pua_percue=ZERO,
        autres_primes=ZERO,
        periodes=[periode(1, 8, REGIME_ML36)],
    )
    resultat = moteur.calculer(Dossier(regime=REGIME_ML36, ml36=ml36))
    ligne = resultat.attestation.lignes[0]

    assert ligne.dont_pua_pfa is None
    assert ligne.autres_primes is None
    assert format_euro(ligne.dont_pua_pfa, vide_si_zero=True) == ""
    assert format_euro(ligne.autres_primes, vide_si_zero=True) == ""

    # La colonne D affiche bien 0,00 € si le montant est nul sans motif d'absence.
    ml36_vide = DossierML36(
        salarie=salarie(),
        mois=dt.date(2025, 7, 1),
        nb_jours_mois=30,
        taux_tpt=Decimal("0.4"),
        tmf_100=ZERO,
        periodes=[periode(1, 8, REGIME_ML36)],
    )
    ligne_zero = moteur.calculer(
        Dossier(regime=REGIME_ML36, ml36=ml36_vide)
    ).attestation.lignes[0]
    assert ligne_zero.libelle is None
    assert arrondi_centime(ligne_zero.montant) == ZERO
    assert format_euro(ligne_zero.montant) == "0,00 €"


# --------------------------------------------------------------------------
# Test 7 — bornes
# --------------------------------------------------------------------------


def test7_dix_periodes_sont_toutes_declarees():
    """§8 — Test 7, revu : plus aucune période n'est écartée de l'attestation.

    Le gabarit Vivinter n'offrait que 7 lignes ; le tableau est désormais étendu
    au nombre de périodes du dossier, et l'export n'est plus bloqué.
    """
    periodes = [periode(1 + 3 * i, 3 + 3 * i, REGIME_ML36) for i in range(10)]
    ml36 = DossierML36(
        salarie=salarie(),
        mois=dt.date(2025, 7, 1),
        nb_jours_mois=31,
        taux_tpt=Decimal("0.4"),
        tmf_100=Decimal(2500),
        periodes=periodes,
    )
    resultat = moteur.calculer(Dossier(regime=REGIME_ML36, ml36=ml36))
    attestation = resultat.attestation

    assert attestation.nb_lignes_utiles == 10
    assert all(not ligne.vide for ligne in attestation.lignes[:10])
    assert [ligne.index for ligne in attestation.lignes[:10]] == list(range(1, 11))
    assert resultat.exportable
    assert resultat.anomalies_export == []


def test7_gabarit_conserve_sept_lignes_au_minimum():
    """Un dossier de 2 périodes garde les 7 lignes du formulaire d'origine."""
    ml36 = DossierML36(
        salarie=salarie(), mois=dt.date(2025, 7, 1), nb_jours_mois=31,
        taux_tpt=Decimal("0.4"), tmf_100=Decimal(2500),
        periodes=[periode(1, 8, REGIME_ML36), periode(11, 18, REGIME_ML36)],
    )
    attestation = moteur.calculer(Dossier(regime=REGIME_ML36, ml36=ml36)).attestation
    assert attestation.nb_lignes_utiles == 7


@pytest.mark.parametrize(
    "nb_jours_mois, nb_jours_periode, correctif_attendu",
    [
        (30, 8, False),   # mois de 30 jours → pas de correctif
        (30, 30, False),
        (31, 31, False),  # période couvrant le mois entier → pas de correctif
        (31, 8, True),
        (28, 8, True),
        (29, 8, True),
        (28, 28, False),
        (29, 29, False),
    ],
)
def test7_correctif_arrondi(nb_jours_mois, nb_jours_periode, correctif_attendu):
    valeur = moteur_ml36.trentieme(Decimal(nb_jours_periode), nb_jours_mois)
    brut = Decimal(nb_jours_periode) * 30 / Decimal(nb_jours_mois)
    attendu = brut + (Decimal("0.0005") if correctif_attendu else ZERO)
    assert valeur == attendu


def test7_aucune_periode_ne_plante_pas():
    for dossier in (
        Dossier(regime=REGIME_ML36, ml36=DossierML36(salarie=salarie(),
                                                     mois=dt.date(2025, 7, 1))),
        Dossier(regime=REGIME_ML37, ml37=DossierML37(salarie=salarie(),
                                                     mois=dt.date(2025, 7, 1))),
    ):
        resultat = moteur.calculer(dossier)
        assert resultat.ml36.somme_trentiemes == ZERO
        assert resultat.ml37.somme_trentiemes == ZERO
        assert resultat.ml36.perte_cpam == ZERO
        assert resultat.ml37.perte_cpam == ZERO
        assert all(ligne.vide for ligne in resultat.attestation.lignes)


def test7_division_par_zero_sur_les_quotes_parts():
    """Sans période, les ventilations valent 0 au lieu de propager #DIV/0!."""
    ml36 = DossierML36(salarie=salarie(), mois=dt.date(2025, 7, 1),
                       tmf_100=Decimal(2500), pua=Decimal(400),
                       autres_primes=Decimal(180))
    resultat = moteur_ml36.calculer(ml36)
    assert all(p.quote_pua == ZERO for p in resultat.periodes)
    assert all(p.quote_autres_primes == ZERO for p in resultat.periodes)
