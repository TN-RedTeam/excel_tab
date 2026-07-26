"""Moteur ML35 — valeurs vérifiées formule à formule sur l'onglet d'origine."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import openpyxl
import pytest

from tpt_app.core import ml35, moteur
from tpt_app.core.arrondi import ZERO, arrondi_centime
from tpt_app.core.attestation import LIBELLE_CONGES
from tpt_app.core.models import Dossier, DossierML35, Periode, REGIME_ML35
from tpt_app.export.excel import CHEMIN_TEMPLATE
from tpt_app.mapping_classeur import FEUILLE_ML35

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


def test_lignes_libres_dans_les_totaux(dossier):
    """Les lignes libres gonflent F4 (base) et F7 (total), pas les I_r."""
    dossier.bases_libres = [Decimal(500), ZERO, ZERO]         # → F4
    dossier.majorations_libres = [Decimal(300), ZERO, ZERO]   # → F7 seulement
    resultat = ml35.calculer(dossier)

    # F4 = 3000 + 500 ; F7 = F4 + 200 + 100 + 300.
    assert resultat.fixe_plus_transfert == Decimal(3500)
    assert resultat.total_remuneration == Decimal(4100)

    # H_r suit F4 (ligne de base incluse) : (3500/30)×(10/30×30) = 1166,67.
    p1 = resultat.periodes[0]
    assert arrondi_centime(p1.fixe) == Decimal("1166.67")
    # I_r ne prend que F5 + F6 : la ligne de majoration libre n'y entre pas.
    assert arrondi_centime(p1.majo_paniers) == Decimal("150.00")


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


def test_attestation_ml35_branche_les_periodes():
    """§4.4 — un dossier ML35 alimente l'attestation depuis le bloc Perçu CPAM.

    3 périodes, dont une CA : les dates sont reportées, les périodes ML35
    affichent leur montant « À DÉCLARER », la période CA affiche « Congés
    annuels », et les colonnes PUA/PFA, autres primes et taux restent vides.
    """
    ml35_dossier = DossierML35(
        salarie=salarie(),
        mois=dt.date(2025, 7, 1),
        nb_jours_mois=30,
        fixe_100=Decimal(3000),
        majo=Decimal(200),
        paniers=Decimal(100),
        ij_total_tpt=Decimal(900),
        periodes=[
            periode(1, 10, "ML35"),
            periode(11, 20, "CA"),
            periode(21, 30, "ML35"),
        ],
    )
    resultat = moteur.calculer(Dossier(regime=REGIME_ML35, ml35=ml35_dossier))
    lignes = resultat.attestation.lignes

    assert [l.source for l in lignes[:3]] == [REGIME_ML35] * 3
    # Dates reportées.
    assert lignes[0].date_debut == dt.date(2025, 7, 1)
    assert lignes[1].date_fin == dt.date(2025, 7, 20)
    # Périodes ML35 : montant A DÉCLARER (700 €), pas de libellé.
    assert lignes[0].libelle is None
    assert arrondi_centime(lignes[0].montant) == Decimal("700.00")
    assert arrondi_centime(lignes[2].montant) == Decimal("700.00")
    # Période CA : « Congés annuels », montant masqué.
    assert lignes[1].libelle == LIBELLE_CONGES
    assert lignes[1].montant is None
    # Colonnes E/F, G et H vides sur toutes les lignes ML35.
    for ligne in lignes[:3]:
        assert ligne.dont_pua_pfa is None
        assert ligne.autres_primes is None
        assert ligne.taux is None
    # Identité reprise du régime ML35.
    assert resultat.attestation.nom == "DUPONT"
    # Au-delà des 3 périodes, les lignes restent vides.
    assert all(l.vide for l in lignes[3:])


def _recalcul_classeur(dossier_ml35: DossierML35, chemin) -> dict[str, float]:
    """Remplit les *entrées* du gabarit puis recalcule ses formules ML35.

    On n'écrit que les cellules de saisie et on laisse les formules du classeur
    d'origine ; ``formulas`` les évalue comme le ferait Excel. C'est la source
    de vérité du test d'acceptation §1.7.
    """
    formulas = pytest.importorskip("formulas")
    import warnings

    classeur = openpyxl.load_workbook(CHEMIN_TEMPLATE)
    feuille = classeur[FEUILLE_ML35]
    feuille["B1"] = dossier_ml35.nb_jours_mois
    feuille["C17"] = float(dossier_ml35.ij_total_tpt)
    feuille["D17"] = float(dossier_ml35.igr)
    feuille["F2"] = float(dossier_ml35.fixe_100)
    feuille["F3"] = float(dossier_ml35.p_transfert)
    feuille["F5"] = float(dossier_ml35.majo)
    feuille["F6"] = float(dossier_ml35.paniers)
    for i, p in enumerate(dossier_ml35.periodes):
        r = 3 + i
        feuille[f"I{r}"] = p.date_debut
        feuille[f"K{r}"] = p.date_fin
        feuille[f"M{r}"] = p.motif_principal
    classeur.save(chemin)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        modele = formulas.ExcelModel().loads(str(chemin)).finish()
        solution = modele.calculate()

    valeurs: dict[str, float] = {}
    for cle, plage in solution.items():
        if "MATRICE ML35 VIERGE" not in cle:
            continue
        cellule = cle.rsplit("!", 1)[-1]
        try:
            brut = plage.value[0][0]
        except (TypeError, IndexError):
            continue
        if isinstance(brut, (int, float)):
            valeurs[cellule] = float(brut)
    return valeurs


def test_acceptation_au_centime_contre_le_classeur(tmp_path):
    """§1.7 — le moteur retombe au centime sur le classeur recalculé."""
    dossier_ml35 = DossierML35(
        salarie=salarie(),
        mois=dt.date(2025, 7, 1),
        nb_jours_mois=31,
        fixe_100=Decimal("2875.40"),
        p_transfert=Decimal("120.00"),
        majo=Decimal("210.30"),
        paniers=Decimal("95.50"),
        ij_total_tpt=Decimal("1234.56"),
        igr=Decimal("78.90"),
        periodes=[
            periode(1, 8, "ML35"),
            periode(9, 15, "CA"),
            periode(16, 27, "ML35"),
            periode(28, 31, "ML35"),
        ],
    )
    attendu = _recalcul_classeur(dossier_ml35, tmp_path / "scenario_ml35.xlsx")
    resultat = ml35.calculer(dossier_ml35)

    def egal(cellule: str, valeur: Decimal) -> None:
        ref = attendu.get(cellule)
        assert ref is not None, f"cellule {cellule} absente du classeur recalculé"
        assert arrondi_centime(valeur) == arrondi_centime(Decimal(str(ref))), cellule

    egal("B14", resultat.ij_par_jour)
    # Seules les lignes renseignées sont comparées : le classeur renvoie #VALEUR!
    # sur une ligne vide, là où le moteur renvoie 0 (divergence documentée).
    remplies = [i for i, p in enumerate(resultat.periodes) if p.date_debut is not None]
    assert len(remplies) == 4
    for i in remplies:
        p = resultat.periodes[i]
        egal(f"K{14 + i}", p.ij_a_retirer)   # bloc « IJ à retirer »
        egal(f"K{24 + i}", p.a_declarer)      # bloc « Perçu CPAM » : A DÉCLARER
        egal(f"L{24 + i}", p.a_declarer_taxe)  # taxé


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
