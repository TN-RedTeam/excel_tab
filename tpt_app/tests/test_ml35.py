"""Moteur ML35 — valeurs vérifiées formule à formule sur l'onglet d'origine."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from tpt_app.core import ml35
from tpt_app.core.arrondi import ZERO, arrondi_centime
from tpt_app.core.models import DossierML35, Periode

from .conftest import periode, salarie


@pytest.fixture
def dossier() -> DossierML35:
    """3 périodes de 10 jours : ML35, CA, ML35, sur un mois de 30 jours."""
    return DossierML35(
        salarie=salarie(),
        mois=dt.date(2025, 7, 1),
        nb_jours_mois=30,
        fixe_100=Decimal(3000),
        p_transfert=ZERO,
        majo=Decimal(200),
        paniers=Decimal(100),
        ij_total_tpt=Decimal(900),
        igr=ZERO,
        periodes=[
            periode(1, 10, "ML35"),
            periode(11, 20, "CA"),
            periode(21, 30, "ML35"),
        ],
    )


def test_totaux_d_entree(dossier):
    resultat = ml35.calculer(dossier)
    assert resultat.fixe_plus_transfert == Decimal(3000)      # F4 = SUM(F2:F3)
    assert resultat.total_remuneration == Decimal(3300)       # F7 = SUM(F4:F6)


def test_jours_et_ij(dossier):
    resultat = ml35.calculer(dossier)
    assert resultat.jours_ml35 == Decimal(20)                 # B17 = SUMIF(…,"ML35",…)
    assert resultat.ij_par_jour == Decimal(45)                # B14 = C17/B17
    assert resultat.total_ij == Decimal(900)                  # E17 = C17+D17
    assert resultat.perte_declaree == Decimal(189)            # F17 = E17*F16


def test_ij_a_retirer_par_periode(dossier):
    """``K_(11+n) = IF(M_n="ML35"; E17*L_n/B17; 0)`` puis ``L = K × F16``."""
    resultat = ml35.calculer(dossier)
    ij = [p.ij_a_retirer for p in resultat.periodes[:3]]
    assert ij == [Decimal(450), ZERO, Decimal(450)]
    assert [arrondi_centime(p.ij_taxees) for p in resultat.periodes[:3]] == [
        Decimal("94.50"), Decimal("0.00"), Decimal("94.50"),
    ]


def test_percu_cpam(dossier):
    """Bloc « Perçu CPAM » : FIXE + MAJO/PANIERS − IJ, puis taxation."""
    resultat = ml35.calculer(dossier)
    p1, p2, p3 = resultat.periodes[:3]

    assert arrondi_centime(p1.fixe) == Decimal("1000.00")      # H_r
    assert arrondi_centime(p1.majo_paniers) == Decimal("150.00")  # I_r
    assert arrondi_centime(p1.a_declarer) == Decimal("700.00")    # K_r
    assert arrondi_centime(p1.a_declarer_taxe) == Decimal("147.00")  # L_r

    # Une période de congés annuels ne reçoit ni majorations ni retenue d'IJ.
    assert arrondi_centime(p2.fixe) == Decimal("1000.00")
    assert p2.majo_paniers == ZERO
    assert p2.ij_a_retirer == ZERO
    assert arrondi_centime(p2.a_declarer) == Decimal("1000.00")

    assert arrondi_centime(p3.a_declarer) == Decimal("700.00")
    assert arrondi_centime(resultat.total_a_declarer) == Decimal("2400.00")


def test_huit_periodes_maximum(dossier):
    resultat = ml35.calculer(dossier)
    assert len(resultat.periodes) == 8
    assert all(p.nb_jours == ZERO for p in resultat.periodes[3:])


def test_aucune_periode_ne_divise_pas_par_zero():
    """Sans période ML35, le classeur renvoie #DIV/0! ; l'application renvoie 0."""
    resultat = ml35.calculer(DossierML35(salarie=salarie(), fixe_100=Decimal(3000),
                                         ij_total_tpt=Decimal(900)))
    assert resultat.jours_ml35 == ZERO
    assert resultat.ij_par_jour == ZERO
    assert all(p.a_declarer == ZERO for p in resultat.periodes)


def test_motif_insensible_a_la_casse_et_aux_espaces():
    """La liste déroulante du classeur contient « CA » avec une espace finale."""
    dossier = DossierML35(
        salarie=salarie(), nb_jours_mois=30, fixe_100=Decimal(3000),
        ij_total_tpt=Decimal(900),
        periodes=[
            Periode(motif_principal=" ml35 ", date_debut=dt.date(2025, 7, 1),
                    date_fin=dt.date(2025, 7, 10)),
            Periode(motif_principal="CA ", date_debut=dt.date(2025, 7, 11),
                    date_fin=dt.date(2025, 7, 20)),
        ],
    )
    resultat = ml35.calculer(dossier)
    assert resultat.jours_ml35 == Decimal(10)
    assert resultat.periodes[1].ij_a_retirer == ZERO
