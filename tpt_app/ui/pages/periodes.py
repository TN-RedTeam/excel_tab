"""Étape 4 — Périodes : table éditable, 10 lignes au maximum."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel

from ...core.models import REGIME_ML35, REGIME_ML36, REGIME_ML37, Dossier
from ..widgets.table_periodes import TablePeriodes
from .base import Page


class PagePeriodes(Page):
    titre = "Périodes"
    soustitre = ("Une période porte un couple de dates, un motif principal et, le cas "
                 "échéant, un motif d'absence. Les colonnes « Nb jours » et « 30ème » "
                 "sont calculées.")

    def construire(self) -> None:
        self._chargement = False
        self.table = TablePeriodes()
        self.table.modifie.connect(self._signaler)
        self.contenu.addWidget(self.table, 1)

        self.messages = QLabel()
        self.messages.setWordWrap(True)
        self.messages.setProperty("role", "erreur")
        self.messages.setVisible(False)
        self.contenu.addWidget(self.messages)

    def charger(self, dossier: Dossier) -> None:
        self._chargement = True
        try:
            self.table.definir_regime(dossier.regime)
            self.table.definir_periodes(list(dossier.matrice_active().periodes))
        finally:
            self._chargement = False

    def appliquer(self, dossier: Dossier) -> None:
        self.table.definir_regime(dossier.regime)
        dossier.matrice_active().periodes = self.table.periodes()

    def actualiser(self, dossier: Dossier, resultat) -> None:
        matrice = resultat.matrice_active(dossier.regime)
        if matrice is not None:
            self.table.actualiser_calculs(matrice.periodes)

        self.table.effacer_anomalies()
        globales = []
        for anomalie in resultat.anomalies:
            if anomalie.champ.startswith("periode."):
                _, index, colonne = anomalie.champ.split(".", 2)
                self.table.signaler_anomalie(int(index), colonne, anomalie.message,
                                             anomalie.gravite)
                globales.append(anomalie.message)
            elif anomalie.champ == "periodes":
                globales.append(anomalie.message)
        for anomalie in resultat.anomalies_export:
            globales.append(anomalie.message)

        self.messages.setText("\n".join(globales))
        self.messages.setVisible(bool(globales))

    def _signaler(self) -> None:
        if not self._chargement:
            self.modifie.emit()
