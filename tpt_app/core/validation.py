"""Contrôles de saisie et messages d'erreur.

Chaque anomalie porte l'identifiant du champ concerné afin que l'interface
l'affiche sous ce champ plutôt que dans une boîte de dialogue modale.
"""

from __future__ import annotations

import calendar
import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Optional

from .arrondi import ZERO, dec
from .models import (
    MOTIFS_ABSENCE,
    MOTIFS_PRINCIPAUX,
    NB_LIGNES_ATTESTATION,
    NB_PERIODES_MAX,
    NB_PERIODES_MAX_ML35,
    REGIME_ML35,
    REGIME_ML36,
    REGIME_ML37,
    Dossier,
    Periode,
)

ERREUR = "erreur"
AVERTISSEMENT = "avertissement"


@dataclass(frozen=True)
class Anomalie:
    """Un message de contrôle rattaché à un champ de saisie."""

    champ: str
    message: str
    gravite: str = ERREUR

    @property
    def bloquante(self) -> bool:
        return self.gravite == ERREUR


def _champ_periode(index: int, nom: str) -> str:
    return f"periode.{index}.{nom}"


def _controler_periode(index: int, periode: Periode, regime: str,
                       mois: Optional[dt.date], nb_jours_mois: int) -> list[Anomalie]:
    anomalies: list[Anomalie] = []
    numero = index + 1

    if not periode.renseignee:
        if periode.date_fin is not None:
            anomalies.append(Anomalie(
                _champ_periode(numero, "date_debut"),
                f"Période {numero} : une date de fin est saisie sans date de début.",
            ))
        return anomalies

    if periode.date_fin is None:
        anomalies.append(Anomalie(
            _champ_periode(numero, "date_fin"),
            f"Période {numero} : la date de fin est obligatoire.",
        ))
    elif periode.date_fin < periode.date_debut:
        anomalies.append(Anomalie(
            _champ_periode(numero, "date_fin"),
            f"Période {numero} : la date de fin précède la date de début.",
        ))

    motifs_valides = MOTIFS_PRINCIPAUX.get(regime, ())
    if not periode.motif_principal:
        anomalies.append(Anomalie(
            _champ_periode(numero, "motif_principal"),
            f"Période {numero} : le motif principal est obligatoire.",
        ))
    elif periode.motif_principal not in motifs_valides:
        attendus = ", ".join(motifs_valides)
        anomalies.append(Anomalie(
            _champ_periode(numero, "motif_principal"),
            f"Période {numero} : motif principal « {periode.motif_principal} » "
            f"inconnu pour {regime} (attendu : {attendus}).",
        ))

    absences_valides = MOTIFS_ABSENCE.get(regime, ())
    if periode.motif_absence and periode.motif_absence not in absences_valides:
        anomalies.append(Anomalie(
            _champ_periode(numero, "motif_absence"),
            f"Période {numero} : motif d'absence « {periode.motif_absence} » "
            f"inconnu pour {regime}.",
        ))

    if mois is not None:
        dernier_jour = calendar.monthrange(mois.year, mois.month)[1]
        debut_mois = dt.date(mois.year, mois.month, 1)
        fin_mois = dt.date(mois.year, mois.month, dernier_jour)
        for nom, valeur in (("date_debut", periode.date_debut), ("date_fin", periode.date_fin)):
            if valeur is not None and not (debut_mois <= valeur <= fin_mois):
                anomalies.append(Anomalie(
                    _champ_periode(numero, nom),
                    f"Période {numero} : la date {valeur:%d/%m/%Y} sort du mois traité "
                    f"({debut_mois:%m/%Y}).",
                ))

    return anomalies


def _controler_chevauchements(periodes: Iterable[Periode]) -> list[Anomalie]:
    anomalies: list[Anomalie] = []
    renseignees = [
        (i + 1, p) for i, p in enumerate(periodes)
        if p.renseignee and p.date_fin is not None and p.date_fin >= p.date_debut
    ]
    for rang, (numero, periode) in enumerate(renseignees):
        for autre_numero, autre in renseignees[rang + 1:]:
            if periode.date_debut <= autre.date_fin and autre.date_debut <= periode.date_fin:
                anomalies.append(Anomalie(
                    _champ_periode(autre_numero, "date_debut"),
                    f"Période {autre_numero} : chevauchement avec la période {numero} "
                    f"({periode.date_debut:%d/%m/%Y} – {periode.date_fin:%d/%m/%Y}).",
                ))
    return anomalies


def _controler_taux(taux_initial: Decimal, taux_tpt: Decimal) -> list[Anomalie]:
    anomalies: list[Anomalie] = []
    initial = dec(taux_initial)
    tpt = dec(taux_tpt)
    if not (ZERO < initial <= Decimal(1)):
        anomalies.append(Anomalie(
            "taux_initial",
            "Le taux initial doit être compris entre 0 et 1 (1 = 100 %).",
        ))
    if not (ZERO < tpt <= Decimal(1)):
        anomalies.append(Anomalie(
            "taux_tpt",
            "Le taux TPT doit être compris entre 0 et 1 (0,4 = 40 %).",
        ))
    elif tpt > initial:
        anomalies.append(Anomalie(
            "taux_tpt",
            "Le taux TPT ne peut pas dépasser le taux initial.",
            AVERTISSEMENT,
        ))
    return anomalies


def _controler_identite(salarie, nb_jours_mois: int, mois: Optional[dt.date]) -> list[Anomalie]:
    anomalies: list[Anomalie] = []
    if not salarie.nom:
        anomalies.append(Anomalie("nom", "Le nom du salarié est obligatoire."))
    if not salarie.matricule:
        anomalies.append(Anomalie("matricule", "Le matricule est obligatoire."))
    numero = (salarie.num_secu or "").replace(" ", "")
    if numero and len(numero) != 15:
        anomalies.append(Anomalie(
            "num_secu",
            f"Le numéro de sécurité sociale doit comporter 15 caractères "
            f"({len(numero)} saisis).",
        ))
    if mois is None:
        anomalies.append(Anomalie("mois", "Le mois traité est obligatoire."))
    if not 28 <= int(nb_jours_mois or 0) <= 31:
        anomalies.append(Anomalie(
            "nb_jours_mois",
            "Le nombre de jours du mois doit être compris entre 28 et 31.",
        ))
    elif mois is not None:
        reel = calendar.monthrange(mois.year, mois.month)[1]
        if int(nb_jours_mois) != reel:
            anomalies.append(Anomalie(
                "nb_jours_mois",
                f"Le mois {mois:%m/%Y} compte {reel} jours ; "
                f"{int(nb_jours_mois)} sont saisis.",
                AVERTISSEMENT,
            ))
    return anomalies


def controler(dossier: Dossier) -> list[Anomalie]:
    """Contrôle le régime actif du dossier et renvoie toutes les anomalies."""
    matrice = dossier.matrice_active()
    regime = dossier.regime
    anomalies = _controler_identite(matrice.salarie, matrice.nb_jours_mois, matrice.mois)

    if regime != REGIME_ML35:
        anomalies += _controler_taux(matrice.taux_initial, matrice.taux_tpt)

    maximum = NB_PERIODES_MAX_ML35 if regime == REGIME_ML35 else NB_PERIODES_MAX
    periodes = list(matrice.periodes)
    if len(periodes) > maximum:
        anomalies.append(Anomalie(
            "periodes",
            f"Le régime {regime} n'accepte que {maximum} périodes ; "
            f"{len(periodes)} sont saisies.",
        ))

    for index, periode in enumerate(periodes[:maximum]):
        anomalies += _controler_periode(index, periode, regime, matrice.mois,
                                        matrice.nb_jours_mois)
    anomalies += _controler_chevauchements(periodes[:maximum])

    total_jours = sum((p.nb_jours_calendaires for p in periodes[:maximum]), ZERO)
    if matrice.nb_jours_mois and total_jours > Decimal(matrice.nb_jours_mois):
        anomalies.append(Anomalie(
            "periodes",
            f"La somme des jours des périodes ({total_jours}) dépasse le nombre de "
            f"jours du mois ({matrice.nb_jours_mois}).",
        ))

    return anomalies


def controler_export(dossier: Dossier) -> list[Anomalie]:
    """Contrôles supplémentaires bloquant l'export de l'attestation.

    Le formulaire Vivinter ne comporte que 7 lignes alors que les matrices en
    gèrent 10 : au-delà, l'export est bloqué et une attestation de continuation
    doit être générée pour les périodes restantes.
    """
    anomalies: list[Anomalie] = []
    for regime, matrice in ((REGIME_ML36, dossier.ml36), (REGIME_ML37, dossier.ml37)):
        surplus = [
            index + 1
            for index, periode in enumerate(matrice.periodes[:NB_PERIODES_MAX])
            if index >= NB_LIGNES_ATTESTATION and periode.renseignee
        ]
        if surplus:
            numeros = ", ".join(str(n) for n in surplus)
            anomalies.append(Anomalie(
                "periodes",
                f"{regime} : l'attestation Vivinter ne comporte que "
                f"{NB_LIGNES_ATTESTATION} lignes. Les périodes {numeros} ne seraient "
                f"pas déclarées. Générez une attestation de continuation.",
            ))
    return anomalies
