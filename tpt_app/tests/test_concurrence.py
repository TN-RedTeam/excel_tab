"""Robustesse en usage partagé : écrasement, écriture atomique, base personnelle."""

from __future__ import annotations

from pathlib import Path

import pytest

from tpt_app.core import moteur
from tpt_app.export import excel, pdf
from tpt_app.export.ecriture import (
    EcritureImpossible,
    chemin_disponible,
    ecrire_atomiquement,
)
from tpt_app.main import dossier_donnees


def test_nom_unique_si_le_fichier_existe(tmp_path):
    """Deux exports du même dossier ne doivent pas s'écraser l'un l'autre."""
    cible = tmp_path / "ATTESTATION.pdf"
    assert chemin_disponible(cible) == cible

    cible.write_bytes(b"premier")
    assert chemin_disponible(cible) == tmp_path / "ATTESTATION (2).pdf"

    (tmp_path / "ATTESTATION (2).pdf").write_bytes(b"deuxieme")
    assert chemin_disponible(cible) == tmp_path / "ATTESTATION (3).pdf"


def test_ecriture_atomique_ne_laisse_pas_de_fichier_tronque(tmp_path):
    """Un échec en cours d'écriture laisse la version précédente intacte."""
    cible = tmp_path / "attestation.pdf"
    cible.write_bytes(b"version valide")

    def produire_puis_echouer(temporaire: Path) -> None:
        temporaire.write_bytes(b"contenu partiel")
        raise OSError("coupure réseau")

    with pytest.raises(EcritureImpossible):
        ecrire_atomiquement(cible, produire_puis_echouer)

    assert cible.read_bytes() == b"version valide"
    # Aucun résidu temporaire n'est laissé dans le dossier.
    assert [c.name for c in tmp_path.iterdir()] == ["attestation.pdf"]


def test_ecriture_atomique_remplace_en_une_fois(tmp_path):
    cible = tmp_path / "attestation.pdf"
    cible.write_bytes(b"ancienne")

    resultat = ecrire_atomiquement(cible, lambda t: t.write_bytes(b"nouvelle"))

    assert resultat == cible
    assert cible.read_bytes() == b"nouvelle"
    assert [c.name for c in tmp_path.iterdir()] == ["attestation.pdf"]


def test_message_explicite_si_le_fichier_est_verrouille(tmp_path):
    """Un PDF ouvert dans Acrobat doit produire un message compréhensible."""
    def refuser(_temporaire: Path) -> None:
        raise PermissionError(13, "Permission denied")

    with pytest.raises(EcritureImpossible, match="ouvert dans une autre application"):
        ecrire_atomiquement(tmp_path / "occupe.pdf", refuser)


def test_exports_reels_sont_atomiques(dossier_test2, tmp_path):
    """Les deux exports passent par le mécanisme d'écriture protégée."""
    resultat = moteur.calculer(dossier_test2)

    for module, extension in ((pdf, "pdf"), (excel, "xlsx")):
        cible = tmp_path / f"attestation.{extension}"
        produit = module.exporter(dossier_test2, resultat, cible)
        assert produit == cible and cible.exists()
        # Pas de fichier temporaire résiduel.
        assert not [c for c in tmp_path.iterdir() if c.name.startswith(".")]


def test_base_toujours_dans_le_profil_utilisateur(tmp_path, monkeypatch):
    """La base ne doit jamais atterrir à côté de l'exécutable partagé.

    SQLite ne verrouille pas de manière fiable sur un partage réseau : une base
    commune serait corrompue dès la première écriture simultanée.
    """
    monkeypatch.setenv("APPDATA", str(tmp_path / "profil"))
    monkeypatch.chdir(tmp_path)

    dossier = dossier_donnees()
    assert dossier == tmp_path / "profil" / "CalculateurTPT"
    assert dossier.is_dir()
    assert dossier != tmp_path          # jamais le répertoire courant


def test_base_sans_appdata_reste_dans_le_profil(tmp_path, monkeypatch):
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "donnees"))

    assert dossier_donnees() == tmp_path / "donnees" / "CalculateurTPT"
