"""Étape 5 — Résultats : synthèse, détail par période, totaux CPAM et Vivinter."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from ...core.arrondi import format_date, format_decimal, format_euro
from ...core.models import REGIME_ML35, REGIME_ML37, Dossier
from ..theme import UNITE
from ..widgets.champs import Formulaire, ValeurCalculee
from .base import Page

COLONNES_ML36 = ("N°", "Du", "Au", "Motif", "30ème", "Rétabli", "Perçu", "Perte",
                 "Déclaré Vivinter", "Dont PUA/PFA", "Autres primes")
#: ML37 ajoute les cotisations à 21 % (F19) sur le perçu et sur la perte.
COLONNES_ML37 = ("N°", "Du", "Au", "Motif", "30ème", "Rétabli", "Perçu",
                 "Cotis. perçu 21%", "Perte", "Cotis. perte 21%",
                 "Déclaré Vivinter", "Dont PUA/PFA", "Autres primes")
COLONNES_ML35 = ("N°", "Du", "Au", "Motif", "Nb jours", "FIXE", "MAJO + PAN",
                 "IJ à retirer", "Cotis. IJ 21%", "À déclarer",
                 "Cotis. à déclarer 21%")


def _table(colonnes) -> QTableWidget:
    table = QTableWidget(0, len(colonnes))
    table.setHorizontalHeaderLabels(colonnes)
    table.verticalHeader().setVisible(False)
    table.setAlternatingRowColors(True)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    _dimensionner(table)
    return table


def _dimensionner(table: QTableWidget) -> None:
    """Les colonnes de montants gardent leur largeur ; « Motif » absorbe le reste."""
    entetes = table.horizontalHeader()
    entetes.setSectionResizeMode(QHeaderView.ResizeToContents)
    if table.columnCount() > 3:
        entetes.setSectionResizeMode(3, QHeaderView.Stretch)


class PageResultats(Page):
    titre = "Résultats"
    soustitre = ""

    def construire(self) -> None:
        groupe_totaux = QGroupBox("Totaux")
        colonnes = QHBoxLayout(groupe_totaux)
        colonnes.setSpacing(UNITE * 8)

        gauche = QWidget()
        formulaire_gauche = Formulaire(gauche)
        self.salaire_retabli = ValeurCalculee()
        self.perte_cpam = ValeurCalculee()
        self.percu_cpam = ValeurCalculee()
        formulaire_gauche.ajouter("SALAIRE RETABLI 3201", self.salaire_retabli)
        formulaire_gauche.ajouter("PERTE CPAM", self.perte_cpam)
        formulaire_gauche.ajouter("PERÇU CPAM", self.percu_cpam)
        colonnes.addWidget(gauche, 1)

        droite = QWidget()
        formulaire_droite = Formulaire(droite)
        self.vivinter = ValeurCalculee()
        self.somme_trentiemes = ValeurCalculee()
        self.absences_sans_solde = ValeurCalculee()
        formulaire_droite.ajouter("VIVINTER — perçu déclaré", self.vivinter)
        formulaire_droite.ajouter("Somme des 30èmes", self.somme_trentiemes)
        formulaire_droite.ajouter("Absences sans solde", self.absences_sans_solde)
        colonnes.addWidget(droite, 1)
        self.contenu.addWidget(groupe_totaux)

        groupe_detail = QGroupBox("Détail par période")
        detail = QVBoxLayout(groupe_detail)
        self.table = _table(COLONNES_ML36)
        detail.addWidget(self.table)
        self.contenu.addWidget(groupe_detail, 1)

    # -- affichage --------------------------------------------------------

    def actualiser(self, dossier: Dossier, resultat) -> None:
        if dossier.regime == REGIME_ML35:
            self._afficher_ml35(resultat.ml35)
        elif dossier.regime == REGIME_ML37:
            self._afficher_ml37(resultat.ml37)
        else:
            self._afficher_matrice(resultat.matrice_active(dossier.regime))

    def _afficher_ml37(self, matrice) -> None:
        """Comme ML36, avec en plus les cotisations à 21 % perçu et perte."""
        self.salaire_retabli.definir_valeur(matrice.salaire_retabli_3201)
        self.perte_cpam.definir_valeur(matrice.perte_cpam)
        self.percu_cpam.definir_valeur(matrice.percu_cpam)
        self.vivinter.definir_valeur(matrice.vivinter_percu)
        self.somme_trentiemes.definir_valeur(matrice.somme_trentiemes, monetaire=False)
        self.absences_sans_solde.definir_valeur(matrice.total_absences_sans_solde)

        renseignees = [p for p in matrice.periodes if p.renseignee]
        self._remplir(COLONNES_ML37, [
            (
                str(p.index),
                format_date(p.date_debut),
                format_date(p.date_fin),
                " / ".join(m for m in (p.motif_principal, p.motif_absence) if m),
                format_decimal(p.trentieme, 4),
                format_euro(p.retabli_total),
                format_euro(p.percu_total),
                format_euro(p.taxation_percu),
                format_euro(p.perte),
                format_euro(p.taxation_perte),
                format_euro(p.montant_declare),
                format_euro(p.dont_pua_pfa, vide_si_zero=True),
                format_euro(p.autres_primes, vide_si_zero=True),
            )
            for p in renseignees
        ])

    def _afficher_matrice(self, matrice) -> None:
        self.salaire_retabli.definir_valeur(matrice.salaire_retabli_3201)
        self.perte_cpam.definir_valeur(matrice.perte_cpam)
        self.percu_cpam.definir_valeur(matrice.percu_cpam)
        self.vivinter.definir_valeur(matrice.vivinter_percu)
        self.somme_trentiemes.definir_valeur(matrice.somme_trentiemes, monetaire=False)
        self.absences_sans_solde.definir_valeur(matrice.total_absences_sans_solde)

        renseignees = [p for p in matrice.periodes if p.renseignee]
        self._remplir(COLONNES_ML36, [
            (
                str(p.index),
                format_date(p.date_debut),
                format_date(p.date_fin),
                " / ".join(m for m in (p.motif_principal, p.motif_absence) if m),
                format_decimal(p.trentieme, 4),
                format_euro(p.retabli_total),
                format_euro(p.percu_total),
                format_euro(p.perte),
                format_euro(p.montant_declare),
                format_euro(p.dont_pua_pfa, vide_si_zero=True),
                format_euro(p.autres_primes, vide_si_zero=True),
            )
            for p in renseignees
        ])

    def _afficher_ml35(self, resultat) -> None:
        if resultat is None:
            return
        self.salaire_retabli.definir_valeur(resultat.total_remuneration)
        self.perte_cpam.definir_valeur(resultat.perte_declaree)
        self.percu_cpam.definir_valeur(resultat.total_ij)
        self.vivinter.definir_valeur(resultat.total_a_declarer)
        self.somme_trentiemes.definir_valeur(resultat.jours_ml35, monetaire=False)
        self.absences_sans_solde.definir_valeur(resultat.total_a_declarer_taxe)

        renseignees = [p for p in resultat.periodes if p.date_debut is not None]
        self._remplir(COLONNES_ML35, [
            (
                str(p.index),
                format_date(p.date_debut),
                format_date(p.date_fin),
                p.motif,
                format_decimal(p.nb_jours, 0),
                format_euro(p.fixe),
                format_euro(p.majo_paniers),
                format_euro(p.ij_a_retirer),
                format_euro(p.ij_taxees),
                format_euro(p.a_declarer),
                format_euro(p.a_declarer_taxe),
            )
            for p in renseignees
        ])

    def _remplir(self, colonnes, lignes) -> None:
        if self.table.columnCount() != len(colonnes):
            self.table.setColumnCount(len(colonnes))
            _dimensionner(self.table)
        self.table.setHorizontalHeaderLabels(colonnes)
        self.table.setRowCount(len(lignes))
        for index, valeurs in enumerate(lignes):
            for colonne, valeur in enumerate(valeurs):
                element = QTableWidgetItem(valeur)
                if colonne >= 4:
                    element.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(index, colonne, element)
