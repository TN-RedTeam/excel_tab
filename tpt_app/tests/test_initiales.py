"""Initiales du rédacteur reportées dans la case « Cachet et Signature »."""

from __future__ import annotations

import pytest

from tpt_app.core import moteur
from tpt_app.core.attestation import initiales
from tpt_app.export import excel, pdf
from tpt_app.mapping_classeur import ATTESTATION_CHAMPS, FEUILLE_ATTESTATION


@pytest.mark.parametrize("saisie, attendu", [
    ("Jean MARTIN", "J.M."),
    ("M. MARTIN", "M."),                    # la civilité est écartée
    ("Mme Sophie BERNARD", "S.B."),
    ("Anne-Marie DUPONT", "A.M.D."),        # prénom composé
    ("jean-pierre le guen", "J.P.L.G."),
    ("  MARTIN  ", "M."),
    ("", ""),
    (None, ""),
    ("M.", ""),                             # rien d'autre qu'une civilité
])
def test_initiales(saisie, attendu):
    assert initiales(saisie) == attendu


def test_initiales_dans_le_resultat(dossier_test1):
    dossier_test1.attestation.nom_redacteur = "Sophie BERNARD"
    resultat = moteur.calculer(dossier_test1)
    assert resultat.attestation.initiales_redacteur == "S.B."


def test_initiales_dans_l_export_excel(dossier_test1, tmp_path):
    import openpyxl

    dossier_test1.attestation.nom_redacteur = "Sophie BERNARD"
    resultat = moteur.calculer(dossier_test1)
    chemin = excel.exporter(dossier_test1, resultat, tmp_path / "attestation.xlsx")

    feuille = openpyxl.load_workbook(chemin)[FEUILLE_ATTESTATION]
    assert feuille[ATTESTATION_CHAMPS["initiales_redacteur"]].value == "S.B."
    assert feuille[ATTESTATION_CHAMPS["nom_redacteur"]].value == "Sophie BERNARD"


def test_initiales_dans_l_export_pdf(dossier_test1, tmp_path):
    pypdfium2 = pytest.importorskip("pypdfium2")

    dossier_test1.attestation.nom_redacteur = "Sophie BERNARD"
    resultat = moteur.calculer(dossier_test1)
    chemin = pdf.exporter(dossier_test1, resultat, tmp_path / "attestation.pdf")

    texte = pypdfium2.PdfDocument(chemin)[0].get_textpage().get_text_range()
    assert "Cachet et Signature" in texte
    assert "S.B." in texte
