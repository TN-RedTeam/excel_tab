"""Interface : cycle saisie → recalcul → aperçu, sans afficher de fenêtre.

Les tests s'exécutent sur la plateforme Qt « offscreen » ; ils sont ignorés si
PySide6 n'est pas installé (le moteur, lui, n'en dépend pas).
"""

from __future__ import annotations

import datetime as dt
import os
from decimal import Decimal

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication          # noqa: E402

from tpt_app.core.arrondi import arrondi_centime    # noqa: E402
from tpt_app.core.models import (                   # noqa: E402
    Dossier,
    Periode,
    REGIME_ML36,
    REGIME_ML37,
)
from tpt_app.db.repository import DepotDossiers     # noqa: E402
from tpt_app.ui.main_window import FenetrePrincipale  # noqa: E402


@pytest.fixture(scope="session")
def application():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def fenetre(application, tmp_path):
    fenetre = FenetrePrincipale(DepotDossiers(tmp_path / "app.db"))
    # Qt ne considère un widget visible que si sa fenêtre l'est : la plateforme
    # « offscreen » l'affiche sans rien peindre à l'écran.
    fenetre.show()
    yield fenetre
    fenetre.close()


def test_fenetre_demarre_sur_un_dossier_vierge(fenetre):
    assert fenetre.rail.count() == 6
    assert fenetre.dossier.regime == REGIME_ML36
    assert fenetre.case_compatibilite.isChecked()
    assert all(ligne.vide for ligne in fenetre.resultat.attestation.lignes)


def test_saisie_déclenche_le_recalcul(fenetre, dossier_test1):
    fenetre.charger_dossier(dossier_test1)
    assert fenetre.etat_periodes.text() == "Périodes : 3"

    ligne = fenetre.resultat.attestation.lignes[0]
    assert arrondi_centime(ligne.montant) == Decimal("391.67")

    # Une frappe dans la page Rémunération suffit à tout recalculer.
    bloc = fenetre.page_remuneration.blocs[REGIME_ML36]
    bloc.champs["tmf_100"].definir_valeur(Decimal(5000))
    fenetre.recalculer()

    assert fenetre.dossier.ml36.tmf_100 == Decimal(5000)
    nouvelle = fenetre.resultat.attestation.lignes[0]
    assert arrondi_centime(nouvelle.montant) == Decimal("658.33")


def test_changement_de_regime_bascule_la_saisie(fenetre, dossier_test2):
    fenetre.charger_dossier(dossier_test2)
    assert fenetre.dossier.regime == REGIME_ML37
    assert fenetre.page_salarie.regime_selectionne() == REGIME_ML37
    assert fenetre.etat_regime.text() == "Régime : ML37"
    # La table propose les motifs du régime actif.
    motif = fenetre.page_periodes.table.table.cellWidget(1, 1)
    assert motif.valeur() == "CA"


def test_anomalies_affichees_sous_les_champs(fenetre):
    dossier = Dossier(regime=REGIME_ML36)
    dossier.ml36.mois = dt.date(2025, 7, 1)
    dossier.ml36.nb_jours_mois = 31
    dossier.ml36.periodes = [
        Periode(motif_principal=REGIME_ML36, date_debut=dt.date(2025, 7, 1),
                date_fin=dt.date(2025, 7, 10)),
        Periode(motif_principal=REGIME_ML36, date_debut=dt.date(2025, 7, 8),
                date_fin=dt.date(2025, 7, 15)),
    ]
    fenetre.charger_dossier(dossier)

    # Nom et matricule manquants : message sous le champ concerné.
    # Les pages vivent dans un QStackedWidget : on teste l'état propre du
    # widget (isHidden) plutôt que sa visibilité effective à l'écran.
    assert not fenetre.page_salarie.champ_nom.message.isHidden()
    assert "obligatoire" in fenetre.page_salarie.champ_nom.message.text()
    # Chevauchement : message global sur la page Périodes.
    assert not fenetre.page_periodes.messages.isHidden()
    assert "chevauchement" in fenetre.page_periodes.messages.text().lower()
    assert "erreur" in fenetre.etat_validite.text()
    # Export interdit tant que la saisie est invalide.
    assert not fenetre.page_attestation.bouton_pdf.isEnabled()


def test_bandeau_ecart_de_compatibilite(fenetre):
    """Le bandeau n'apparaît que lorsque les deux modes divergent (§9.1)."""
    dossier = Dossier(regime=REGIME_ML36)
    dossier.ml36.mois = dt.date(2025, 7, 1)
    dossier.ml36.nb_jours_mois = 30
    dossier.ml36.tmf_100 = Decimal(2500)
    dossier.ml36.salarie.nom = "DUPONT"
    dossier.ml36.salarie.matricule = "A12345"
    dossier.ml36.periodes = [Periode(
        motif_principal=REGIME_ML36, motif_absence="Maladie",
        date_debut=dt.date(2025, 7, 1), date_fin=dt.date(2025, 7, 5),
        dates_sur_ligne_periode=True,      # cas d'un classeur importé
    )]
    fenetre.charger_dossier(dossier)

    assert fenetre.resultat.ecarts_compatibilite
    assert not fenetre.page_resultats.bandeau.isHidden()
    assert "service paie" in fenetre.page_resultats.bandeau.text()

    # Sans ambiguïté de saisie, les deux modes concordent : pas de bandeau.
    dossier.ml36.periodes[0].dates_sur_ligne_periode = None
    fenetre.charger_dossier(dossier)
    assert not fenetre.resultat.ecarts_compatibilite
    assert fenetre.page_resultats.bandeau.isHidden()


def test_bouton_continuation_au_dela_de_sept_periodes(fenetre, dossier_test1):
    dossier_test1.ml36.periodes = [
        Periode(motif_principal=REGIME_ML36,
                date_debut=dt.date(2025, 7, 1 + 3 * i),
                date_fin=dt.date(2025, 7, 3 + 3 * i))
        for i in range(9)
    ]
    fenetre.charger_dossier(dossier_test1)

    assert not fenetre.page_attestation.bouton_continuation.isHidden()
    assert not fenetre.page_attestation.bouton_pdf.isEnabled()
    assert not fenetre.page_attestation.avertissement.isHidden()


def test_enregistrement_et_reouverture(fenetre, dossier_test1):
    fenetre.charger_dossier(dossier_test1)
    fenetre.enregistrer_dossier()

    listes = fenetre.depot.lister()
    assert len(listes) == 1
    identifiant = listes[0]["id"]

    fenetre.nouveau_dossier()
    assert fenetre.dossier.ml36.tmf_100 == 0

    fenetre.ouvrir_dossier(identifiant)
    assert fenetre.dossier.ml36.tmf_100 == Decimal(2500)
    assert arrondi_centime(
        fenetre.resultat.attestation.lignes[0].montant) == Decimal("391.67")


def test_bascule_de_theme(fenetre):
    clair = fenetre.styleSheet()
    fenetre.action_theme.setChecked(True)
    sombre = fenetre.styleSheet()
    assert clair != sombre
    assert fenetre.action_theme.text() == "Thème clair"


def test_apercu_se_dessine_sans_erreur(fenetre, dossier_test2):
    from PySide6.QtGui import QPixmap

    fenetre.charger_dossier(dossier_test2)
    apercu = fenetre.page_attestation.apercu
    apercu.resize(600, 850)

    image = QPixmap(600, 850)
    apercu.render(image)
    assert not image.isNull()
