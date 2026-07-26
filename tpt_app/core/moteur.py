"""Orchestration : calcule un dossier complet et assemble l'attestation."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Optional

from . import attestation as attestation_module
from . import ml35 as moteur_ml35
from . import ml36 as moteur_ml36
from . import ml37 as moteur_ml37
from .models import (
    REGIME_ML35,
    REGIME_ML36,
    REGIME_ML37,
    Dossier,
    ResultatAttestation,
    ResultatMatrice,
    ResultatML35,
)
from .validation import Anomalie, controler, controler_export


@dataclass
class ResultatDossier:
    """Tous les résultats d'un dossier, prêts pour l'affichage et l'export."""

    ml35: Optional[ResultatML35] = None
    ml36: Optional[ResultatMatrice] = None
    ml37: Optional[ResultatMatrice] = None
    attestation: Optional[ResultatAttestation] = None
    anomalies: list[Anomalie] = field(default_factory=list)
    anomalies_export: list[Anomalie] = field(default_factory=list)

    @property
    def valide(self) -> bool:
        return not any(a.bloquante for a in self.anomalies)

    @property
    def exportable(self) -> bool:
        return self.valide and not any(a.bloquante for a in self.anomalies_export)

    def matrice_active(self, regime: str):
        return {REGIME_ML35: self.ml35, REGIME_ML36: self.ml36,
                REGIME_ML37: self.ml37}[regime]


def calculer(dossier: Dossier, aujourdhui: Optional[dt.date] = None) -> ResultatDossier:
    """Calcule les trois matrices et assemble l'attestation."""
    ml36 = moteur_ml36.calculer(dossier.ml36)
    ml37 = moteur_ml37.calculer(dossier.ml37)
    ml35 = moteur_ml35.calculer(dossier.ml35) if dossier.regime == REGIME_ML35 else None

    resultat_attestation = attestation_module.construire(
        dossier, ml36, ml37, aujourdhui=aujourdhui, resultat_ml35=ml35
    )

    return ResultatDossier(
        ml35=ml35,
        ml36=ml36,
        ml37=ml37,
        attestation=resultat_attestation,
        anomalies=controler(dossier),
        anomalies_export=controler_export(dossier),
    )
