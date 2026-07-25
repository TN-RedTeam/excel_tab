"""Table de saisie des périodes.

Une période est un objet unique : un couple de dates, un motif principal et un
motif d'absence. L'ambiguïté du tableur — dates saisies tantôt sur la ligne
« période », tantôt sur la ligne « motif » — n'est pas reproduite ici (§5.3).
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
    MOTIFS_ABSENCE,
    MOTIFS_PRINCIPAUX,
    NB_PERIODES_MAX,
    NB_PERIODES_MAX_ML35,
    REGIME_ML35,
    Periode,
)
from ..theme import UNITE
from .champs import SaisieChoix, SaisieDate

COLONNES = ("N°", "Motif principal", "Motif d'absence", "Du", "Au", "Nb jours", "30ème")


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
        for colonne in (1, 2):
            entetes.setSectionResizeMode(colonne, QHeaderView.Stretch)
        for colonne in (3, 4, 5, 6):
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
            absence = self.table.cellWidget(ligne, 2)
            debut = self.table.cellWidget(ligne, 3)
            fin = self.table.cellWidget(ligne, 4)
            numero = self.table.item(ligne, 0)
            resultat.append(Periode(
                motif_principal=motif.valeur() if motif else "",
                motif_absence=absence.valeur() if absence else "",
                date_debut=debut.valeur() if debut else None,
                date_fin=fin.valeur() if fin else None,
                # Conserve la ligne de saisie d'origine d'un dossier importé : la
                # table ne doit pas la réécrire au premier recalcul (§9.4).
                dates_sur_ligne_periode=numero.data(Qt.UserRole) if numero else None,
            ))
        return resultat

    def actualiser_calculs(self, resultats) -> None:
        """Renseigne les colonnes calculées « Nb jours » et « 30ème »."""
        for ligne in range(self.table.rowCount()):
            if ligne >= len(resultats):
                break
            resultat = resultats[ligne]
            self._definir_cellule(ligne, 5, format_decimal(resultat.nb_jours, 0))
            self._definir_cellule(ligne, 6, format_decimal(resultat.trentieme, 4))

    def signaler_anomalie(self, index: int, colonne: str, message: str,
                          gravite: str) -> None:
        """Colore la ligne concernée et place le message en infobulle."""
        correspondance = {"motif_principal": 1, "motif_absence": 2,
                          "date_debut": 3, "date_fin": 4}
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
            for colonne in (1, 2, 3, 4):
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

        motif = SaisieChoix(MOTIFS_PRINCIPAUX.get(self._regime, ()), autorise_vide=True)
        motif.definir_valeur(periode.motif_principal)
        absence = SaisieChoix(MOTIFS_ABSENCE.get(self._regime, ()), autorise_vide=True)
        absence.definir_valeur(periode.motif_absence)
        debut = SaisieDate()
        debut.definir_valeur(periode.date_debut)
        fin = SaisieDate()
        fin.definir_valeur(periode.date_fin)

        for colonne, widget in ((1, motif), (2, absence), (3, debut), (4, fin)):
            self.table.setCellWidget(ligne, colonne, widget)
        for colonne in (0, 5, 6):
            self._definir_cellule(ligne, colonne, "")
        self.table.item(ligne, 0).setData(Qt.UserRole, periode.dates_sur_ligne_periode)

        motif.currentIndexChanged.connect(self._ligne_modifiee)
        absence.currentIndexChanged.connect(self._ligne_modifiee)
        debut.dateChanged.connect(self._ligne_modifiee)
        fin.dateChanged.connect(self._ligne_modifiee)

    def _ligne_modifiee(self, *_) -> None:
        """Une modification manuelle lève l'ambiguïté héritée d'un classeur importé."""
        emetteur = self.sender()
        for ligne in range(self.table.rowCount()):
            if any(self.table.cellWidget(ligne, colonne) is emetteur
                   for colonne in (1, 2, 3, 4)):
                numero = self.table.item(ligne, 0)
                if numero is not None:
                    numero.setData(Qt.UserRole, None)
                break
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
        if self.table.rowCount() >= self.maximum:
            return
        defaut = MOTIFS_PRINCIPAUX.get(self._regime, ("",))[0]
        self._inserer_ligne(Periode(motif_principal=defaut))
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
