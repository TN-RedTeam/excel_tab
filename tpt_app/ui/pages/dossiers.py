"""Étape 1 — Dossiers : liste des dossiers enregistrés, recherche et filtres."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from ...core.models import REGIMES
from ..theme import UNITE
from ..widgets.champs import SaisieChoix
from .base import Page

COLONNES = ("Nom", "Prénom", "Matricule", "Régime", "Mois", "Modifié le")


class PageDossiers(Page):
    titre = "Dossiers"
    soustitre = "Dossiers enregistrés localement, du plus récemment modifié au plus ancien."

    nouveau_demande = Signal()
    import_demande = Signal()
    ouverture_demandee = Signal(int)
    suppression_demandee = Signal(int)

    def construire(self) -> None:
        barre = QHBoxLayout()
        barre.setSpacing(UNITE * 2)

        self.recherche = QLineEdit()
        self.recherche.setPlaceholderText("Rechercher un nom, un prénom, un matricule…")
        self.recherche.setClearButtonEnabled(True)
        barre.addWidget(self.recherche, 2)

        self.filtre_regime = SaisieChoix(REGIMES, autorise_vide=True)
        self.filtre_regime.setItemText(0, "Tous les régimes")
        barre.addWidget(self.filtre_regime)

        self.filtre_mois = QLineEdit()
        self.filtre_mois.setPlaceholderText("Mois (AAAA-MM)")
        self.filtre_mois.setMaximumWidth(160)
        barre.addWidget(self.filtre_mois)
        barre.addStretch(1)

        self.bouton_nouveau = QPushButton("Nouveau  (Ctrl+N)")
        self.bouton_nouveau.setProperty("role", "primaire")
        self.bouton_importer = QPushButton("Importer un classeur…")
        barre.addWidget(self.bouton_nouveau)
        barre.addWidget(self.bouton_importer)
        self.contenu.addLayout(barre)

        self.table = QTableWidget(0, len(COLONNES))
        self.table.setHorizontalHeaderLabels(COLONNES)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.contenu.addWidget(self.table, 1)

        self.message = QLabel("Aucun dossier enregistré pour le moment.")
        self.message.setProperty("role", "soustitre")
        self.contenu.addWidget(self.message)

        actions = QHBoxLayout()
        actions.setSpacing(UNITE * 2)
        self.bouton_ouvrir = QPushButton("Ouvrir")
        self.bouton_supprimer = QPushButton("Supprimer")
        actions.addWidget(self.bouton_ouvrir)
        actions.addWidget(self.bouton_supprimer)
        actions.addStretch(1)
        self.contenu.addLayout(actions)

        self.bouton_nouveau.clicked.connect(self.nouveau_demande)
        self.bouton_importer.clicked.connect(self.import_demande)
        self.bouton_ouvrir.clicked.connect(self._ouvrir)
        self.bouton_supprimer.clicked.connect(self._supprimer)
        self.table.doubleClicked.connect(self._ouvrir)

    # -- affichage --------------------------------------------------------

    def afficher(self, dossiers: list[dict]) -> None:
        self.table.setRowCount(len(dossiers))
        for ligne, dossier in enumerate(dossiers):
            valeurs = (
                dossier.get("nom", ""),
                dossier.get("prenom", ""),
                dossier.get("matricule", ""),
                dossier.get("regime", ""),
                dossier.get("mois") or "",
                (dossier.get("modifie_le") or "")[:16].replace("T", " "),
            )
            for colonne, valeur in enumerate(valeurs):
                element = QTableWidgetItem(str(valeur))
                if colonne == 0:
                    element.setData(Qt.UserRole, dossier["id"])
                self.table.setItem(ligne, colonne, element)

        vide = not dossiers
        self.message.setVisible(vide)
        self.bouton_ouvrir.setEnabled(not vide)
        self.bouton_supprimer.setEnabled(not vide)

    def identifiant_selectionne(self) -> int | None:
        ligne = self.table.currentRow()
        if ligne < 0:
            return None
        element = self.table.item(ligne, 0)
        return element.data(Qt.UserRole) if element else None

    def criteres(self) -> dict:
        return {
            "recherche": self.recherche.text().strip(),
            "regime": self.filtre_regime.valeur(),
            "mois": self.filtre_mois.text().strip(),
        }

    def _ouvrir(self, *_) -> None:
        identifiant = self.identifiant_selectionne()
        if identifiant is not None:
            self.ouverture_demandee.emit(int(identifiant))

    def _supprimer(self) -> None:
        identifiant = self.identifiant_selectionne()
        if identifiant is not None:
            self.suppression_demandee.emit(int(identifiant))
