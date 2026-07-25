"""Étape 3 — Rémunération : bases, majorations, paniers, SIACI, PUA, autres primes.

Les libellés suivent le régime actif : ML36 et ML37 ne portent pas les mêmes
lignes, et ML35 relève d'une saisie entièrement distincte.
"""

from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QStackedWidget, QWidget

from ...core.arrondi import ZERO
from ...core.models import REGIME_ML35, REGIME_ML36, REGIME_ML37, Dossier
from ..widgets.champs import Formulaire, SaisieMontant, SaisieTaux, ValeurCalculee
from .base import Page


class _BlocRegime(QWidget):
    """Base commune : trois lignes libres, un total calculé."""

    def __init__(self, page: "PageRemuneration"):
        super().__init__()
        self.page = page
        self.champs: dict[str, SaisieMontant] = {}

    def _montant(self, formulaire: Formulaire, clef: str, libelle: str,
                 aide: str = "") -> SaisieMontant:
        editeur = SaisieMontant()
        editeur.valeur_modifiee.connect(self.page.signaler)
        formulaire.ajouter(libelle, editeur, aide)
        self.champs[clef] = editeur
        return editeur

    def _taux(self, formulaire: Formulaire, libelle: str, aide: str = "") -> SaisieTaux:
        editeur = SaisieTaux()
        editeur.valeur_modifiee.connect(self.page.signaler)
        formulaire.ajouter(libelle, editeur, aide)
        return editeur


class BlocML36ML37(_BlocRegime):
    """Saisie ML36 ou ML37, dont les structures sont parallèles."""

    def __init__(self, page: "PageRemuneration", regime: str):
        super().__init__(page)
        self.regime = regime
        from PySide6.QtWidgets import QVBoxLayout

        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(0, 0, 0, 0)

        groupe_taux = QGroupBox("Taux")
        formulaire = Formulaire(groupe_taux)
        self.taux_initial = self._taux(formulaire, "Taux initial", "100 % en principe.")
        self.taux_tpt = self._taux(formulaire, "Taux TPT",
                                   "Quotité travaillée pendant le temps partiel.")
        disposition.addWidget(groupe_taux)

        groupe_base = QGroupBox("Base salariale")
        base = Formulaire(groupe_base)
        self._montant(base, "tmf_100", "TMF à 100 %")
        self._montant(base, "p_transfert_100", "P. TRANSFERT à 100 %")
        for index in range(3):
            self._montant(base, f"base_libre_{index}", f"Ligne libre {index + 1}")
        self.total_base = ValeurCalculee()
        base.ajouter("Base salariale", self.total_base,
                     "Somme des lignes ci-dessus.")
        disposition.addWidget(groupe_base)

        groupe_majorations = QGroupBox("Majorations et paniers")
        majorations = Formulaire(groupe_majorations)
        if regime == REGIME_ML36:
            self._montant(majorations, "maj_nuit", "MAJ NUIT")
            self._montant(majorations, "maj_ferie", "Maj férié")
        else:
            self._montant(majorations, "remu_ca", "REMU CA")
            self._montant(majorations, "maj_nuit", "MAJ NUIT")
        for index in range(3):
            self._montant(majorations, f"majoration_libre_{index}",
                          f"Ligne libre {index + 1}")
        self.total_majorations = ValeurCalculee()
        majorations.ajouter("Total majorations", self.total_majorations)
        self._montant(majorations, "paniers_r226", "PANIERS + R226")
        disposition.addWidget(groupe_majorations)

        groupe_primes = QGroupBox("SIACI et primes")
        primes = Formulaire(groupe_primes)
        self._montant(primes, "montant_siaci", "Montant SIACI")
        self.montant_reintegre = ValeurCalculee()
        primes.ajouter("Montant réintégré", self.montant_reintegre,
                       "Montant SIACI taxé à 24,5 %.")
        self._montant(primes, "pua", "PUA")
        self._montant(primes, "pua_percue", "PUA perçue")
        self.perte_pua = ValeurCalculee()
        primes.ajouter("Perte PUA", self.perte_pua)
        self._montant(primes, "autres_primes", "Autres primes",
                      "Ventilée au prorata des 30èmes sur l'attestation.")
        disposition.addWidget(groupe_primes)
        disposition.addStretch(1)

    def charger(self, matrice) -> None:
        self.taux_initial.definir_valeur(matrice.taux_initial)
        self.taux_tpt.definir_valeur(matrice.taux_tpt)
        for clef, editeur in self.champs.items():
            if clef.startswith("base_libre_"):
                index = int(clef.rsplit("_", 1)[1])
                valeur = (matrice.bases_libres + [ZERO] * 3)[index]
            elif clef.startswith("majoration_libre_"):
                index = int(clef.rsplit("_", 1)[1])
                valeur = (matrice.majorations_libres + [ZERO] * 3)[index]
            else:
                valeur = getattr(matrice, clef, ZERO)
            editeur.definir_valeur(valeur)

    def appliquer(self, matrice) -> None:
        matrice.taux_initial = self.taux_initial.valeur()
        matrice.taux_tpt = self.taux_tpt.valeur()
        bases, majorations = [ZERO] * 3, [ZERO] * 3
        for clef, editeur in self.champs.items():
            if clef.startswith("base_libre_"):
                bases[int(clef.rsplit("_", 1)[1])] = editeur.valeur()
            elif clef.startswith("majoration_libre_"):
                majorations[int(clef.rsplit("_", 1)[1])] = editeur.valeur()
            else:
                setattr(matrice, clef, editeur.valeur())
        matrice.bases_libres = bases
        matrice.majorations_libres = majorations

    def actualiser(self, resultat) -> None:
        self.total_base.definir_valeur(resultat.base_salariale)
        self.total_majorations.definir_valeur(resultat.total_majorations)
        self.montant_reintegre.definir_valeur(resultat.montant_reintegre)
        self.perte_pua.definir_valeur(resultat.perte_pua)


class BlocML35(_BlocRegime):
    """Saisie ML35 : rémunération de référence et indemnités journalières."""

    def __init__(self, page: "PageRemuneration"):
        super().__init__(page)
        from PySide6.QtWidgets import QVBoxLayout

        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(0, 0, 0, 0)

        groupe = QGroupBox("Rémunération de référence")
        formulaire = Formulaire(groupe)
        self._montant(formulaire, "fixe_100", "FIXE 100 %")
        self._montant(formulaire, "p_transfert", "P. TRANS")
        self.fixe_transfert = ValeurCalculee()
        formulaire.ajouter("FIXE + P. TRANS", self.fixe_transfert)
        self._montant(formulaire, "majo", "MAJO")
        self._montant(formulaire, "paniers", "PANIERS")
        self.total = ValeurCalculee()
        formulaire.ajouter("TOTAL", self.total)
        disposition.addWidget(groupe)

        groupe_ij = QGroupBox("Indemnités journalières")
        ij = Formulaire(groupe_ij)
        self._montant(ij, "ij_total_tpt", "IJ TOTAL TPT")
        self._montant(ij, "igr", "IGR")
        self.total_ij = ValeurCalculee()
        ij.ajouter("TOTAL IJ", self.total_ij)
        self.taux_perte = self._taux(ij, "Taux de perte", "21 % par défaut.")
        self.perte_declaree = ValeurCalculee()
        ij.ajouter("Perte déclarée", self.perte_declaree)
        self.ij_par_jour = ValeurCalculee()
        ij.ajouter("IJ / jour", self.ij_par_jour)
        disposition.addWidget(groupe_ij)
        disposition.addStretch(1)

    def charger(self, matrice) -> None:
        for clef, editeur in self.champs.items():
            editeur.definir_valeur(getattr(matrice, clef, ZERO))
        self.taux_perte.definir_valeur(matrice.taux_perte)

    def appliquer(self, matrice) -> None:
        for clef, editeur in self.champs.items():
            setattr(matrice, clef, editeur.valeur())
        matrice.taux_perte = self.taux_perte.valeur()
        matrice.taux_declaration = self.taux_perte.valeur()

    def actualiser(self, resultat) -> None:
        if resultat is None:
            return
        self.fixe_transfert.definir_valeur(resultat.fixe_plus_transfert)
        self.total.definir_valeur(resultat.total_remuneration)
        self.total_ij.definir_valeur(resultat.total_ij)
        self.perte_declaree.definir_valeur(resultat.perte_declaree)
        self.ij_par_jour.definir_valeur(resultat.ij_par_jour)


class PageRemuneration(Page):
    titre = "Rémunération"
    soustitre = ("Les montants sont saisis à 100 %. Les champs grisés sont calculés "
                 "et ne peuvent pas être modifiés.")

    def construire(self) -> None:
        self._chargement = False
        self.pile = QStackedWidget()
        self.blocs = {
            REGIME_ML35: BlocML35(self),
            REGIME_ML36: BlocML36ML37(self, REGIME_ML36),
            REGIME_ML37: BlocML36ML37(self, REGIME_ML37),
        }
        self._index = {}
        for regime, bloc in self.blocs.items():
            self._index[regime] = self.pile.addWidget(bloc)
        self.contenu.addWidget(self.pile)

    def signaler(self, *_) -> None:
        if not self._chargement:
            self.modifie.emit()

    def charger(self, dossier: Dossier) -> None:
        self._chargement = True
        try:
            self.pile.setCurrentIndex(self._index[dossier.regime])
            self.blocs[REGIME_ML35].charger(dossier.ml35)
            self.blocs[REGIME_ML36].charger(dossier.ml36)
            self.blocs[REGIME_ML37].charger(dossier.ml37)
        finally:
            self._chargement = False

    def appliquer(self, dossier: Dossier) -> None:
        self.pile.setCurrentIndex(self._index[dossier.regime])
        self.blocs[REGIME_ML35].appliquer(dossier.ml35)
        self.blocs[REGIME_ML36].appliquer(dossier.ml36)
        self.blocs[REGIME_ML37].appliquer(dossier.ml37)

    def actualiser(self, dossier: Dossier, resultat) -> None:
        self.blocs[REGIME_ML35].actualiser(resultat.ml35)
        self.blocs[REGIME_ML36].actualiser(resultat.ml36)
        self.blocs[REGIME_ML37].actualiser(resultat.ml37)
