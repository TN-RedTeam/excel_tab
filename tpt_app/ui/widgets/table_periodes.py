"""Table de saisie des périodes.

Une période est un objet unique : un couple de dates et **un seul motif**. Le
classeur séparait le motif d'activité du motif d'absence sur deux lignes, donc
deux listes déroulantes ; l'application n'en propose qu'une, où figurent tous les
motifs du régime.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.arrondi import format_decimal
from ...core.models import (
    NB_PERIODES_MAX,
    NB_PERIODES_MAX_ML35,
    REGIME_ML35,
    Periode,
    decomposer_motif,
    motifs_proposes,
    recomposer_motif,
)
from ..theme import UNITE
from .champs import SaisieChoix, SaisieDate

COLONNES = ("N°", "Motif", "Du", "Au", "Nb jours", "30ème")


class TablePeriodes(QWidget):
    """Table éditable des périodes, avec ajout, suppression et réordonnancement."""

    modifie = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._regime = "ML36"
        self._silencieux = False

        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(0, 0, 0, 0)
        disposition.setSpacing(UNITE * 2)

        self.table = QTableWidget(0, len(COLONNES))
        self.table.setHorizontalHeaderLabels(COLONNES)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        entetes = self.table.horizontalHeader()
        entetes.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        entetes.setSectionResizeMode(1, QHeaderView.Stretch)
        for colonne in (2, 3, 4, 5):
            entetes.setSectionResizeMode(colonne, QHeaderView.ResizeToContents)
        disposition.addWidget(self.table)

        barre = QHBoxLayout()
        barre.setSpacing(UNITE * 2)
        self.bouton_ajouter = QPushButton("Ajouter une période")
        self.bouton_supprimer = QPushButton("Supprimer")
        self.bouton_monter = QPushButton("Monter")
        self.bouton_descendre = QPushButton("Descendre")
        for bouton in (self.bouton_ajouter, self.bouton_supprimer,
                       self.bouton_monter, self.bouton_descendre):
            barre.addWidget(bouton)
        barre.addStretch(1)
        disposition.addLayout(barre)

        self.bouton_ajouter.clicked.connect(self._ajouter)
        self.bouton_supprimer.clicked.connect(self._supprimer)
        self.bouton_monter.clicked.connect(lambda: self._deplacer(-1))
        self.bouton_descendre.clicked.connect(lambda: self._deplacer(1))

    # -- configuration ----------------------------------------------------

    @property
    def maximum(self) -> int:
        return NB_PERIODES_MAX_ML35 if self._regime == REGIME_ML35 else NB_PERIODES_MAX

    def definir_regime(self, regime: str) -> None:
        """Change le régime : les listes de motifs et le maximum s'adaptent."""
        if regime == self._regime:
            return
        self._regime = regime
        periodes = self.periodes()[: self.maximum]
        self.definir_periodes(periodes)

    # -- lecture / écriture -----------------------------------------------

    def definir_periodes(self, periodes: list[Periode]) -> None:
        self._silencieux = True
        try:
            self.table.setRowCount(0)
            for periode in periodes[: self.maximum]:
                self._inserer_ligne(periode)
        finally:
            self._silencieux = False
        self._renumeroter()

    def periodes(self) -> list[Periode]:
        resultat = []
        for ligne in range(self.table.rowCount()):
            motif = self.table.cellWidget(ligne, 1)
            debut = self.table.cellWidget(ligne, 2)
            fin = self.table.cellWidget(ligne, 3)
            principal, absence = decomposer_motif(
                self._regime, motif.valeur() if motif else "")
            resultat.append(Periode(
                motif_principal=principal,
                motif_absence=absence,
                date_debut=debut.valeur() if debut else None,
                date_fin=fin.valeur() if fin else None,
            ))
        return resultat

    def actualiser_calculs(self, resultats) -> None:
        """Renseigne les colonnes calculées « Nb jours » et « 30ème »."""
        for ligne in range(self.table.rowCount()):
            if ligne >= len(resultats):
                break
            resultat = resultats[ligne]
            self._definir_cellule(ligne, 4, format_decimal(resultat.nb_jours, 0))
            self._definir_cellule(ligne, 5, format_decimal(resultat.trentieme, 4))

    def signaler_anomalie(self, index: int, colonne: str, message: str,
                          gravite: str) -> None:
        """Colore la ligne concernée et place le message en infobulle."""
        correspondance = {"motif_principal": 1, "motif_absence": 1,
                          "date_debut": 2, "date_fin": 3}
        numero = correspondance.get(colonne)
        if numero is None or index - 1 >= self.table.rowCount():
            return
        widget = self.table.cellWidget(index - 1, numero)
        if widget is None:
            return
        widget.setToolTip(message)
        widget.setProperty("etat", "erreur" if gravite == "erreur" else "")
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def effacer_anomalies(self) -> None:
        for ligne in range(self.table.rowCount()):
            for colonne in (1, 2, 3):
                widget = self.table.cellWidget(ligne, colonne)
                if widget is None:
                    continue
                widget.setToolTip("")
                widget.setProperty("etat", "")
                widget.style().unpolish(widget)
                widget.style().polish(widget)

    # -- édition ----------------------------------------------------------

    def _inserer_ligne(self, periode: Periode) -> None:
        ligne = self.table.rowCount()
        self.table.insertRow(ligne)

        # Un seul menu déroulant : activité et absences y figurent ensemble.
        motif = SaisieChoix(motifs_proposes(self._regime), autorise_vide=True)
        motif.definir_valeur(recomposer_motif(periode.motif_principal,
                                              periode.motif_absence))
        debut = SaisieDate()
        debut.definir_valeur(periode.date_debut)
        fin = SaisieDate()
        fin.definir_valeur(periode.date_fin)

        for colonne, widget in ((1, motif), (2, debut), (3, fin)):
            self.table.setCellWidget(ligne, colonne, widget)
        for colonne in (0, 4, 5):
            self._definir_cellule(ligne, colonne, "")

        motif.currentIndexChanged.connect(self._ligne_modifiee)
        debut.dateChanged.connect(self._ligne_modifiee)
        fin.dateChanged.connect(self._ligne_modifiee)

    def _ligne_modifiee(self, *_) -> None:
        self._signaler()

    def _definir_cellule(self, ligne: int, colonne: int, texte: str) -> None:
        element = self.table.item(ligne, colonne)
        if element is None:
            element = QTableWidgetItem()
            element.setFlags(Qt.ItemIsEnabled)
            element.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(ligne, colonne, element)
        element.setText(texte)

    def _renumeroter(self) -> None:
        for ligne in range(self.table.rowCount()):
            self._definir_cellule(ligne, 0, str(ligne + 1))
        self.bouton_ajouter.setEnabled(self.table.rowCount() < self.maximum)

    def _ajouter(self) -> None:
        """Ajoute une période vierge : motif et dates restent à renseigner."""
        if self.table.rowCount() >= self.maximum:
            return
        self._inserer_ligne(Periode())
        self._renumeroter()
        self._signaler()

    def _supprimer(self) -> None:
        ligne = self.table.currentRow()
        if ligne < 0:
            return
        self.table.removeRow(ligne)
        self._renumeroter()
        self._signaler()

    def _deplacer(self, sens: int) -> None:
        ligne = self.table.currentRow()
        cible = ligne + sens
        if ligne < 0 or not 0 <= cible < self.table.rowCount():
            return
        periodes = self.periodes()
        periodes[ligne], periodes[cible] = periodes[cible], periodes[ligne]
        self.definir_periodes(periodes)
        self.table.selectRow(cible)
        self._signaler()

    def _signaler(self, *_) -> None:
        if not self._silencieux:
            self.modifie.emit()
