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
    """Emplacement de la base locale, **toujours dans le profil utilisateur**.

    L'exécutable est destiné à être posé sur un partage réseau et lancé par
    plusieurs personnes en même temps. Écrire la base à côté de lui les ferait
    toutes pointer sur le même fichier SQLite via SMB, où le verrouillage n'est
    pas fiable : corruption assurée à la première écriture simultanée. Chaque
    utilisateur dispose donc de son propre historique, dans son profil Windows.
    """
    racine = os.environ.get("APPDATA") or os.environ.get("XDG_DATA_HOME")
    base = Path(racine) if racine else Path.home() / ".local" / "share"
    dossier = base / "CalculateurTPT"
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("Calculateur TPT")
    application.setOrganizationName("Air France")
    QLocale.setDefault(QLocale(QLocale.French, QLocale.France))

    fenetre = FenetrePrincipale(DepotDossiers(dossier_donnees() / "app.db"))
    fenetre.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
