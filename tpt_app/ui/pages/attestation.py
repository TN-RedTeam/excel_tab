"""Étape 6 — Attestation : champs manuels, aperçu temps réel et exports."""

from __future__ import annotations

import datetime as dt

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, Signal

from ...core.models import (
    MAIL_VIVINTER,
    QUALIFICATIONS,
    RISQUES,
    Dossier,
)
from ..theme import UNITE
from ..widgets.apercu_attestation import ApercuAttestation
from ..widgets.champs import Formulaire, SaisieChoix, SaisieDate, SaisieTexte
from .base import Page


class PageAttestation(Page):
    titre = "Attestation"
    soustitre = ("Les colonnes « Dont PUA / PFA » et « Autres primes » sont calculées "
                 "et non modifiables. L'aperçu se met à jour à chaque frappe.")

    #: Émis quand l'utilisateur demande un export.
    export_demande = Signal(str)

    def construire(self) -> None:
        self._chargement = False

        separateur = QSplitter(Qt.Horizontal)

        gauche = QWidget()
        disposition = QVBoxLayout(gauche)
        disposition.setContentsMargins(0, 0, UNITE * 3, 0)
        disposition.setSpacing(UNITE * 3)

        groupe = QGroupBox("Champs de l'attestation")
        formulaire = Formulaire(groupe)
        self.num_dossier = SaisieTexte()
        self.qualification = SaisieChoix(QUALIFICATIONS)
        self.risque = SaisieChoix(RISQUES)
        self.fait_a = SaisieTexte()
        self.fait_le = SaisieDate(autorise_vide=False)
        self.nom_redacteur = SaisieTexte()
        self.telephone = SaisieTexte()
        self.mail = SaisieTexte()
        formulaire.ajouter("N° dossier", self.num_dossier)
        formulaire.ajouter("Qualification", self.qualification)
        formulaire.ajouter("Risques", self.risque)
        formulaire.ajouter("Fait à", self.fait_a)
        formulaire.ajouter("Le", self.fait_le)
        formulaire.ajouter("Nom du rédacteur", self.nom_redacteur)
        formulaire.ajouter("Téléphone", self.telephone)
        formulaire.ajouter("Mail", self.mail, "Constante Vivinter, modifiable.")
        disposition.addWidget(groupe)

        self.avertissement = QLabel()
        self.avertissement.setWordWrap(True)
        self.avertissement.setProperty("role", "erreur")
        self.avertissement.setVisible(False)
        disposition.addWidget(self.avertissement)

        boutons = QHBoxLayout()
        boutons.setSpacing(UNITE * 2)
        self.bouton_excel = QPushButton("Exporter en Excel  (Ctrl+E)")
        self.bouton_pdf = QPushButton("Exporter en PDF  (Ctrl+P)")
        self.bouton_pdf.setProperty("role", "primaire")
        self.bouton_continuation = QPushButton("Attestation de continuation")
        self.bouton_continuation.setVisible(False)
        for bouton in (self.bouton_pdf, self.bouton_excel, self.bouton_continuation):
            boutons.addWidget(bouton)
        boutons.addStretch(1)
        disposition.addLayout(boutons)
        disposition.addStretch(1)

        self.bouton_excel.clicked.connect(lambda: self.export_demande.emit("xlsx"))
        self.bouton_pdf.clicked.connect(lambda: self.export_demande.emit("pdf"))
        self.bouton_continuation.clicked.connect(
            lambda: self.export_demande.emit("continuation"))

        self.apercu = ApercuAttestation()

        separateur.addWidget(gauche)
        separateur.addWidget(self.apercu)
        separateur.setStretchFactor(0, 0)
        separateur.setStretchFactor(1, 1)
        separateur.setSizes([420, 560])
        self.contenu.addWidget(separateur, 1)

        for editeur in (self.num_dossier, self.fait_a, self.nom_redacteur,
                        self.telephone, self.mail):
            editeur.textEdited.connect(self._signaler)
        for editeur in (self.qualification, self.risque):
            editeur.currentIndexChanged.connect(self._signaler)
        self.fait_le.dateChanged.connect(self._signaler)

    def charger(self, dossier: Dossier) -> None:
        self._chargement = True
        try:
            attestation = dossier.attestation
            self.num_dossier.setText(attestation.num_dossier)
            self.qualification.definir_valeur(attestation.qualification)
            self.risque.definir_valeur(attestation.risque)
            self.fait_a.setText(attestation.fait_a)
            self.fait_le.definir_valeur(attestation.fait_le or dt.date.today())
            self.nom_redacteur.setText(attestation.nom_redacteur)
            self.telephone.setText(attestation.telephone)
            self.mail.setText(attestation.mail or MAIL_VIVINTER)
        finally:
            self._chargement = False

    def appliquer(self, dossier: Dossier) -> None:
        attestation = dossier.attestation
        attestation.num_dossier = self.num_dossier.text().strip()
        attestation.qualification = self.qualification.valeur()
        attestation.risque = self.risque.valeur()
        attestation.fait_a = self.fait_a.text().strip()
        attestation.fait_le = self.fait_le.valeur()
        attestation.nom_redacteur = self.nom_redacteur.text().strip()
        attestation.telephone = self.telephone.text().strip()
        attestation.mail = self.mail.text().strip()

    def actualiser(self, dossier: Dossier, resultat) -> None:
        self.apercu.definir_attestation(resultat.attestation)

        bloquantes = [a.message for a in resultat.anomalies_export if a.bloquante]
        if not resultat.valide:
            bloquantes.insert(0, "Le dossier comporte des erreurs de saisie : "
                                 "corrigez-les avant d'exporter.")
        self.avertissement.setText("\n".join(bloquantes))
        self.avertissement.setVisible(bool(bloquantes))

        exportable = resultat.exportable
        self.bouton_excel.setEnabled(exportable)
        self.bouton_pdf.setEnabled(exportable)
        self.bouton_continuation.setVisible(
            bool(resultat.attestation.periodes_non_declarees))

    def _signaler(self, *_) -> None:
        if not self._chargement:
            self.modifie.emit()
