"""Fenêtre principale : rail de navigation, recalcul instantané, exports."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QStackedWidget,
    QToolBar,
    QWidget,
)

from ..core import moteur
from ..core.attestation import nom_fichier
from ..core.models import Dossier, REGIME_ML35
from ..db.repository import DepotDossiers
from ..export import excel as export_excel
from ..export import pdf as export_pdf
from ..export.excel import ExportBloque
from ..importer.classeur import ImportImpossible, importer
from .pages.attestation import PageAttestation
from .pages.dossiers import PageDossiers
from .pages.periodes import PagePeriodes
from .pages.remuneration import PageRemuneration
from .pages.resultats import PageResultats
from .pages.salarie import PageSalarie
from .theme import CLAIR, SOMBRE, feuille_de_style

ETAPES = (
    ("1  Dossiers", PageDossiers),
    ("2  Salarié", PageSalarie),
    ("3  Rémunération", PageRemuneration),
    ("4  Périodes", PagePeriodes),
    ("5  Résultats", PageResultats),
    ("6  Attestation", PageAttestation),
)


class FenetrePrincipale(QMainWindow):
    """Fenêtre unique, navigation par étapes dans un rail latéral gauche."""

    def __init__(self, depot: Optional[DepotDossiers] = None):
        super().__init__()
        self.setWindowTitle("Calculateur TPT — Attestation Vivinter")
        self.resize(1280, 860)

        self.depot = depot or DepotDossiers()
        self.dossier = Dossier()
        self.resultat = moteur.calculer(self.dossier)
        self._sombre = False
        self._synchronisation = False

        self._construire_barre_outils()
        self._construire_corps()
        self._construire_barre_etat()
        self._construire_raccourcis()

        self.appliquer_theme()
        self.charger_dossier(Dossier())
        self.rafraichir_liste()

    # -- construction -----------------------------------------------------

    def _construire_barre_outils(self) -> None:
        barre = QToolBar("Actions")
        barre.setMovable(False)
        self.addToolBar(barre)

        self.action_nouveau = QAction("Nouveau", self)
        self.action_enregistrer = QAction("Enregistrer", self)
        self.action_excel = QAction("Export Excel", self)
        self.action_pdf = QAction("Export PDF", self)
        self.action_recalcul = QAction("Recalculer", self)
        for action in (self.action_nouveau, self.action_enregistrer,
                       self.action_excel, self.action_pdf, self.action_recalcul):
            barre.addAction(action)

        barre.addSeparator()
        self.case_compatibilite = QCheckBox("Mode de compatibilité classeur v6")
        self.case_compatibilite.setChecked(True)
        self.case_compatibilite.setToolTip(
            "Reproduit les formules du classeur d'origine, y compris les garde-fous "
            "qui ne s'y déclenchent jamais (cf. docs/ANOMALIES.md, §9.1)."
        )
        self.case_compatibilite.toggled.connect(self._changer_mode)
        barre.addWidget(self.case_compatibilite)

        vide = QWidget()
        vide.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        barre.addWidget(vide)

        self.action_theme = QAction("Thème sombre", self)
        self.action_theme.setCheckable(True)
        self.action_theme.toggled.connect(self._basculer_theme)
        barre.addAction(self.action_theme)

        self.action_nouveau.triggered.connect(self.nouveau_dossier)
        self.action_enregistrer.triggered.connect(self.enregistrer_dossier)
        self.action_excel.triggered.connect(lambda: self.exporter("xlsx"))
        self.action_pdf.triggered.connect(lambda: self.exporter("pdf"))
        self.action_recalcul.triggered.connect(self.recalculer)

    def _construire_corps(self) -> None:
        central = QWidget()
        disposition = QHBoxLayout(central)
        disposition.setContentsMargins(0, 0, 0, 0)
        disposition.setSpacing(0)

        self.rail = QListWidget()
        self.rail.setObjectName("rail")
        self.rail.setFixedWidth(210)
        self.rail.setFocusPolicy(Qt.StrongFocus)
        disposition.addWidget(self.rail)

        self.pile = QStackedWidget()
        disposition.addWidget(self.pile, 1)

        self.pages = {}
        for libelle, classe in ETAPES:
            page = classe()
            self.pages[classe.__name__] = page
            self.pile.addWidget(page)
            self.rail.addItem(QListWidgetItem(libelle))
            if hasattr(page, "modifie"):
                page.modifie.connect(self.recalculer)

        self.rail.currentRowChanged.connect(self.pile.setCurrentIndex)
        self.rail.setCurrentRow(0)

        self.page_dossiers: PageDossiers = self.pages["PageDossiers"]
        self.page_salarie: PageSalarie = self.pages["PageSalarie"]
        self.page_remuneration: PageRemuneration = self.pages["PageRemuneration"]
        self.page_periodes: PagePeriodes = self.pages["PagePeriodes"]
        self.page_resultats: PageResultats = self.pages["PageResultats"]
        self.page_attestation: PageAttestation = self.pages["PageAttestation"]

        self.page_dossiers.nouveau_demande.connect(self.nouveau_dossier)
        self.page_dossiers.import_demande.connect(self.importer_classeur)
        self.page_dossiers.ouverture_demandee.connect(self.ouvrir_dossier)
        self.page_dossiers.suppression_demandee.connect(self.supprimer_dossier)
        self.page_dossiers.recherche.textChanged.connect(self.rafraichir_liste)
        self.page_dossiers.filtre_regime.currentIndexChanged.connect(
            self.rafraichir_liste)
        self.page_dossiers.filtre_mois.textChanged.connect(self.rafraichir_liste)
        self.page_attestation.export_demande.connect(self.exporter)

        self.setCentralWidget(central)

    def _construire_barre_etat(self) -> None:
        self.etat_regime = QLabel()
        self.etat_mois = QLabel()
        self.etat_periodes = QLabel()
        self.etat_validite = QLabel()
        for etiquette in (self.etat_regime, self.etat_mois, self.etat_periodes):
            self.statusBar().addWidget(etiquette)
        self.statusBar().addPermanentWidget(self.etat_validite)

    def _construire_raccourcis(self) -> None:
        for action, sequence in (
            (self.action_nouveau, QKeySequence.New),
            (self.action_enregistrer, QKeySequence.Save),
            (self.action_excel, QKeySequence("Ctrl+E")),
            (self.action_pdf, QKeySequence("Ctrl+P")),
            (self.action_recalcul, QKeySequence("F5")),
        ):
            action.setShortcut(sequence)
            action.setShortcutContext(Qt.ApplicationShortcut)

    # -- thème ------------------------------------------------------------

    def appliquer_theme(self) -> None:
        palette = SOMBRE if self._sombre else CLAIR
        self.setStyleSheet(feuille_de_style(palette))

    def _basculer_theme(self, sombre: bool) -> None:
        self._sombre = sombre
        self.action_theme.setText("Thème clair" if sombre else "Thème sombre")
        self.appliquer_theme()

    def _changer_mode(self, actif: bool) -> None:
        self.dossier.mode_compatibilite = actif
        self.recalculer()

    # -- cycle de calcul --------------------------------------------------

    def charger_dossier(self, dossier: Dossier) -> None:
        """Remplace le dossier courant et recharge toutes les étapes."""
        self._synchronisation = True
        try:
            self.dossier = dossier
            self.case_compatibilite.setChecked(dossier.mode_compatibilite)
            for page in self.pages.values():
                page.charger(dossier)
        finally:
            self._synchronisation = False
        self.recalculer()

    def recalculer(self) -> None:
        """Relit les saisies, recalcule et diffuse les résultats."""
        if self._synchronisation:
            return
        self._synchronisation = True
        try:
            for page in self.pages.values():
                page.appliquer(self.dossier)
            self.dossier.mode_compatibilite = self.case_compatibilite.isChecked()
            self.resultat = moteur.calculer(self.dossier)
            for page in self.pages.values():
                page.actualiser(self.dossier, self.resultat)
            self._actualiser_barre_etat()
        finally:
            self._synchronisation = False

    def _actualiser_barre_etat(self) -> None:
        matrice = self.dossier.matrice_active()
        periodes = sum(1 for p in matrice.periodes if p.renseignee)
        self.etat_regime.setText(f"Régime : {self.dossier.regime}")
        self.etat_mois.setText(
            "Mois : " + (matrice.mois.strftime("%m/%Y") if matrice.mois else "—"))
        self.etat_periodes.setText(f"Périodes : {periodes}")

        erreurs = [a for a in self.resultat.anomalies if a.bloquante]
        if erreurs:
            self.etat_validite.setText(f"{len(erreurs)} erreur(s) de saisie")
            self.etat_validite.setProperty("role", "erreur")
        elif self.resultat.anomalies:
            self.etat_validite.setText("Dossier valide — avertissements")
            self.etat_validite.setProperty("role", "avertissement")
        else:
            self.etat_validite.setText("Dossier valide")
            self.etat_validite.setProperty("role", "succes")
        self.etat_validite.style().unpolish(self.etat_validite)
        self.etat_validite.style().polish(self.etat_validite)

    # -- actions ----------------------------------------------------------

    def nouveau_dossier(self) -> None:
        self.charger_dossier(Dossier())
        self.rail.setCurrentRow(1)

    def enregistrer_dossier(self) -> None:
        self.recalculer()
        matrice = self.dossier.matrice_active()
        if not self.dossier.libelle:
            self.dossier.libelle = " ".join(filter(None, (
                matrice.salarie.nom, matrice.salarie.prenom,
                matrice.mois.strftime("%m/%Y") if matrice.mois else "",
            ))) or "Dossier sans nom"
        self.depot.enregistrer(self.dossier)
        self.rafraichir_liste()
        self.statusBar().showMessage("Dossier enregistré.", 4000)

    def rafraichir_liste(self) -> None:
        self.page_dossiers.afficher(self.depot.lister(**self.page_dossiers.criteres()))

    def ouvrir_dossier(self, identifiant: int) -> None:
        dossier = self.depot.charger(identifiant)
        if dossier is None:
            self._alerter("Ce dossier n'existe plus dans la base locale.")
            self.rafraichir_liste()
            return
        self.charger_dossier(dossier)
        self.rail.setCurrentRow(1)

    def supprimer_dossier(self, identifiant: int) -> None:
        reponse = QMessageBox.question(
            self, "Supprimer le dossier",
            "Supprimer définitivement ce dossier de la base locale ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reponse != QMessageBox.Yes:
            return
        self.depot.supprimer(identifiant)
        if self.dossier.identifiant == identifiant:
            self.dossier.identifiant = None
        self.rafraichir_liste()

    def importer_classeur(self) -> None:
        chemin, _ = QFileDialog.getOpenFileName(
            self, "Importer un classeur TPT", "", "Classeurs Excel (*.xlsx)")
        if not chemin:
            return
        try:
            dossier = importer(chemin)
        except ImportImpossible as erreur:
            self._alerter(str(erreur))
            return
        self.charger_dossier(dossier)
        self.rail.setCurrentRow(1)
        self.statusBar().showMessage(
            f"Classeur « {Path(chemin).name} » importé.", 6000)

    def exporter(self, format_demande: str) -> None:
        """Produit l'attestation ; ``continuation`` déclare les périodes 8 à 10."""
        self.recalculer()
        continuation = format_demande == "continuation"
        extension = "pdf" if continuation else format_demande

        matrice = self.dossier.matrice_active()
        propose = nom_fichier(self.resultat.attestation, matrice.mois, extension)
        if continuation:
            propose = propose.replace(f".{extension}", f"_SUITE.{extension}")

        filtres = {"pdf": "Document PDF (*.pdf)", "xlsx": "Classeur Excel (*.xlsx)"}
        chemin, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer l'attestation", propose, filtres[extension])
        if not chemin:
            return

        module = export_pdf if extension == "pdf" else export_excel
        try:
            module.exporter(self.dossier, self.resultat, chemin,
                            ignorer_controles=continuation)
        except ExportBloque as erreur:
            self._alerter(str(erreur))
            return
        except OSError as erreur:
            self._alerter(f"Le fichier n'a pas pu être écrit : {erreur}")
            return
        self.statusBar().showMessage(f"Attestation enregistrée : {chemin}", 8000)

    def _alerter(self, message: str) -> None:
        QMessageBox.warning(self, "Calculateur TPT", message)

    def closeEvent(self, evenement):      # noqa: N802 (API Qt)
        self.depot.fermer()
        super().closeEvent(evenement)
