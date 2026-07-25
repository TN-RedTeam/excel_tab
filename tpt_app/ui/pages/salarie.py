"""Étape 2 — Salarié : identité, mois traité et choix du régime."""

from __future__ import annotations

from PySide6.QtWidgets import QButtonGroup, QGroupBox, QHBoxLayout, QRadioButton

from ...core.models import REGIME_ML36, REGIMES, Dossier
from ..theme import UNITE
from ..widgets.champs import (
    Formulaire,
    SaisieDate,
    SaisieEntier,
    SaisieMois,
    SaisieTexte,
)
from .base import Page

DESCRIPTIONS_REGIME = {
    "ML35": "Perte d'indemnités journalières — jusqu'à 8 périodes.",
    "ML36": "Temps partiel thérapeutique — jusqu'à 10 périodes, alimente l'attestation.",
    "ML37": "Accident du travail — jusqu'à 10 périodes, alimente l'attestation.",
}


class PageSalarie(Page):
    titre = "Salarié"
    soustitre = ("Identité du salarié, mois traité et régime de prise en charge. "
                 "Un dossier relève d'un seul régime à la fois.")

    def construire(self) -> None:
        self._chargement = False

        groupe_regime = QGroupBox("Régime")
        disposition = QHBoxLayout(groupe_regime)
        disposition.setSpacing(UNITE * 6)
        self.groupe_boutons = QButtonGroup(self)
        for regime in REGIMES:
            bouton = QRadioButton(regime)
            bouton.setToolTip(DESCRIPTIONS_REGIME[regime])
            self.groupe_boutons.addButton(bouton)
            bouton.setProperty("regime", regime)
            disposition.addWidget(bouton)
        disposition.addStretch(1)
        self.groupe_boutons.buttonClicked.connect(self._signaler)
        self.contenu.addWidget(groupe_regime)

        groupe_identite = QGroupBox("Identité")
        identite = Formulaire(groupe_identite)
        self.siret = SaisieTexte("14 chiffres")
        self.num_secu = SaisieTexte("15 caractères")
        self.matricule = SaisieTexte()
        self.nom = SaisieTexte()
        self.prenom = SaisieTexte()
        self.champ_siret = identite.ajouter("SIRET", self.siret)
        self.champ_num_secu = identite.ajouter("N° Sécurité Sociale", self.num_secu)
        self.champ_matricule = identite.ajouter("Matricule", self.matricule)
        self.champ_nom = identite.ajouter("Nom", self.nom)
        self.champ_prenom = identite.ajouter("Prénom", self.prenom)
        self.contenu.addWidget(groupe_identite)

        groupe_periode = QGroupBox("Arrêt et mois traité")
        periode = Formulaire(groupe_periode)
        self._formulaire_periode = periode
        self.date_at = SaisieDate()
        self.djt = SaisieDate()
        self.mois = SaisieMois()
        self.nb_jours_mois = SaisieEntier(28, 31)
        self.champ_date_at = periode.ajouter(
            "Date AT", self.date_at, "Renseignée pour les dossiers ML35 et ML37.")
        self.champ_djt = periode.ajouter(
            "DJT", self.djt, "Date de début du temps partiel.")
        self.champ_mois = periode.ajouter("Mois traité", self.mois)
        self.champ_nb_jours = periode.ajouter(
            "Nb de jours dans le mois", self.nb_jours_mois,
            "Sert de diviseur au calcul des 30èmes.")
        self.contenu.addWidget(groupe_periode)
        self.contenu.addStretch(1)

        for editeur in (self.siret, self.num_secu, self.matricule, self.nom,
                        self.prenom):
            editeur.textEdited.connect(self._signaler)
        for editeur in (self.date_at, self.djt, self.mois):
            editeur.dateChanged.connect(self._signaler)
        self.nb_jours_mois.valueChanged.connect(self._signaler)

    # -- synchronisation --------------------------------------------------

    def _adapter_au_regime(self, regime: str) -> None:
        """ML36 ne comporte pas de date d'accident du travail : on masque le champ.

        Le classeur n'expose « DATE AT » que sur les onglets ML35 (`B7`) et ML37
        (`B6`) ; la matrice ML36 n'a pas de cellule correspondante.
        """
        self._formulaire_periode.definir_ligne_visible(
            self.champ_date_at, regime != REGIME_ML36)

    def charger(self, dossier: Dossier) -> None:
        self._chargement = True
        try:
            for bouton in self.groupe_boutons.buttons():
                bouton.setChecked(bouton.property("regime") == dossier.regime)
            self._adapter_au_regime(dossier.regime)
            matrice = dossier.matrice_active()
            salarie = matrice.salarie
            self.siret.setText(salarie.siret)
            self.num_secu.setText(salarie.num_secu)
            self.matricule.setText(salarie.matricule)
            self.nom.setText(salarie.nom)
            self.prenom.setText(salarie.prenom)
            self.date_at.definir_valeur(salarie.date_at)
            self.djt.definir_valeur(salarie.djt)
            self.mois.definir_valeur(matrice.mois)
            self.nb_jours_mois.setValue(int(matrice.nb_jours_mois or 30))
        finally:
            self._chargement = False

    def regime_selectionne(self) -> str:
        bouton = self.groupe_boutons.checkedButton()
        return bouton.property("regime") if bouton else "ML36"

    def appliquer(self, dossier: Dossier) -> None:
        dossier.regime = self.regime_selectionne()
        self._adapter_au_regime(dossier.regime)
        # L'identité est commune aux trois régimes : on la recopie partout, afin
        # que l'attestation la retrouve quel que soit le régime saisi.
        for matrice in (dossier.ml35, dossier.ml36, dossier.ml37):
            salarie = matrice.salarie
            salarie.siret = self.siret.text().strip()
            salarie.num_secu = self.num_secu.text().strip()
            salarie.matricule = self.matricule.text().strip()
            salarie.nom = self.nom.text().strip()
            salarie.prenom = self.prenom.text().strip()
            salarie.date_at = self.date_at.valeur()
            salarie.djt = self.djt.valeur()
            matrice.mois = self.mois.valeur()
            matrice.nb_jours_mois = self.nb_jours_mois.value()

    def actualiser(self, dossier: Dossier, resultat) -> None:
        champs = {
            "siret": self.champ_siret,
            "num_secu": self.champ_num_secu,
            "matricule": self.champ_matricule,
            "nom": self.champ_nom,
            "prenom": self.champ_prenom,
            "mois": self.champ_mois,
            "nb_jours_mois": self.champ_nb_jours,
        }
        for champ in champs.values():
            champ.afficher_anomalie()
        for anomalie in resultat.anomalies:
            champ = champs.get(anomalie.champ)
            if champ is not None:
                champ.afficher_anomalie(anomalie.message, anomalie.gravite)

    def _signaler(self, *_) -> None:
        if not self._chargement:
            self.modifie.emit()
