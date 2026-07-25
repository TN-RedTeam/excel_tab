"""Point d'entrée du Calculateur TPT.

L'application est entièrement locale : aucune connexion réseau, aucun droit
administrateur, aucune dépendance à Microsoft Office. La base ``app.db`` est
créée à côté de l'exécutable, ou dans le profil de l'utilisateur si ce dossier
n'est pas accessible en écriture (partage réseau, clé USB protégée).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QApplication

from .db.repository import DepotDossiers
from .ui.main_window import FenetrePrincipale


def dossier_donnees() -> Path:
    """Emplacement inscriptible de la base locale."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path.cwd()
    try:
        temoin = base / ".ecriture"
        temoin.touch()
        temoin.unlink()
        return base
    except OSError:
        profil = Path(os.environ.get("APPDATA") or Path.home()) / "CalculateurTPT"
        profil.mkdir(parents=True, exist_ok=True)
        return profil


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("Calculateur TPT")
    application.setOrganizationName("Air France — ALYZIA")
    QLocale.setDefault(QLocale(QLocale.French, QLocale.France))

    fenetre = FenetrePrincipale(DepotDossiers(dossier_donnees() / "app.db"))
    fenetre.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
