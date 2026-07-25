"""Ossature commune aux étapes de l'application."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..theme import UNITE


class Page(QWidget):
    """Une étape : un titre, un sous-titre et un contenu défilant."""

    #: Émis dès que l'utilisateur modifie une valeur de saisie.
    modifie = Signal()

    titre = ""
    soustitre = ""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        exterieur = QVBoxLayout(self)
        exterieur.setContentsMargins(UNITE * 6, UNITE * 5, UNITE * 6, UNITE * 4)
        exterieur.setSpacing(UNITE * 2)

        etiquette = QLabel(self.titre)
        etiquette.setProperty("role", "titre")
        exterieur.addWidget(etiquette)

        if self.soustitre:
            sous = QLabel(self.soustitre)
            sous.setProperty("role", "soustitre")
            sous.setWordWrap(True)
            exterieur.addWidget(sous)

        separateur = QFrame()
        separateur.setProperty("role", "separateur")
        separateur.setFixedHeight(1)
        exterieur.addWidget(separateur)

        zone = QScrollArea()
        zone.setWidgetResizable(True)
        contenu = QWidget()
        self.contenu = QVBoxLayout(contenu)
        self.contenu.setContentsMargins(0, UNITE * 2, 0, 0)
        self.contenu.setSpacing(UNITE * 3)
        zone.setWidget(contenu)
        exterieur.addWidget(zone, 1)

        self.construire()

    # -- à implémenter par les sous-classes -------------------------------

    def construire(self) -> None:
        """Construit le contenu de la page."""

    def charger(self, dossier) -> None:
        """Recopie le dossier dans les champs de saisie."""

    def appliquer(self, dossier) -> None:
        """Reporte les champs de saisie dans le dossier."""

    def actualiser(self, dossier, resultat) -> None:
        """Met à jour les valeurs calculées et les messages de contrôle."""
