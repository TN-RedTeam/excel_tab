"""Orchestration : calcule un dossier complet et compare les deux modes.

Le « mode de compatibilité classeur v6 » reproduit les formules d'origine, dont
certains garde-fous ne se déclenchent jamais (cf. `docs/ANOMALIES.md`, §9.1). Le
moteur calcule systématiquement les deux modes afin que l'interface puisse
signaler l'écart et laisser le service paie trancher.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from . import attestation as attestation_module
from . import ml35 as moteur_ml35
from . import ml36 as moteur_ml36
from . import ml37 as moteur_ml37
from .arrondi import arrondi_centime
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


@dataclass(frozen=True)
class EcartCompatibilite:
    """Divergence entre le mode compatibilité v6 et le mode corrigé."""

    regime: str
    libelle: str
    valeur_compatibilite: Decimal
    valeur_corrigee: Decimal

    @property
    def ecart(self) -> Decimal:
        return self.valeur_compatibilite - self.valeur_corrigee


@dataclass
class ResultatDossier:
    """Tous les résultats d'un dossier, prêts pour l'affichage et l'export."""

    ml35: Optional[ResultatML35] = None
    ml36: Optional[ResultatMatrice] = None
    ml37: Optional[ResultatMatrice] = None
    attestation: Optional[ResultatAttestation] = None
    anomalies: list[Anomalie] = field(default_factory=list)
    anomalies_export: list[Anomalie] = field(default_factory=list)
    ecarts_compatibilite: list[EcartCompatibilite] = field(default_factory=list)

    @property
    def valide(self) -> bool:
        return not any(a.bloquante for a in self.anomalies)

    @property
    def exportable(self) -> bool:
        return self.valide and not any(a.bloquante for a in self.anomalies_export)

    def matrice_active(self, regime: str):
        return {REGIME_ML35: self.ml35, REGIME_ML36: self.ml36,
                REGIME_ML37: self.ml37}[regime]


_TOTAUX_COMPARES = (
    ("perte_cpam", "PERTE CPAM"),
    ("vivinter_percu", "VIVINTER — perçu déclaré"),
    ("salaire_retabli_3201", "SALAIRE RETABLI 3201"),
)


def _comparer(regime: str, compat: ResultatMatrice,
              corrige: ResultatMatrice) -> list[EcartCompatibilite]:
    ecarts = []
    for attribut, libelle in _TOTAUX_COMPARES:
        gauche = getattr(compat, attribut)
        droite = getattr(corrige, attribut)
        if arrondi_centime(gauche) != arrondi_centime(droite):
            ecarts.append(EcartCompatibilite(regime, libelle, gauche, droite))
    return ecarts


def calculer(dossier: Dossier, aujourdhui: Optional[dt.date] = None) -> ResultatDossier:
    """Calcule le dossier dans le mode retenu et mesure l'écart avec l'autre mode."""
    mode = dossier.mode_compatibilite

    ml36_compat = moteur_ml36.calculer(dossier.ml36, mode_compatibilite=True)
    ml36_corrige = moteur_ml36.calculer(dossier.ml36, mode_compatibilite=False)
    ml37_compat = moteur_ml37.calculer(dossier.ml37, mode_compatibilite=True)
    ml37_corrige = moteur_ml37.calculer(dossier.ml37, mode_compatibilite=False)

    ml36 = ml36_compat if mode else ml36_corrige
    ml37 = ml37_compat if mode else ml37_corrige
    ml35 = moteur_ml35.calculer(dossier.ml35) if dossier.regime == REGIME_ML35 else None

    ecarts = _comparer(REGIME_ML36, ml36_compat, ml36_corrige) \
        + _comparer(REGIME_ML37, ml37_compat, ml37_corrige)

    resultat_attestation = attestation_module.construire(
        dossier, ml36, ml37, aujourdhui=aujourdhui
    )

    return ResultatDossier(
        ml35=ml35,
        ml36=ml36,
        ml37=ml37,
        attestation=resultat_attestation,
        anomalies=controler(dossier),
        anomalies_export=controler_export(dossier),
        ecarts_compatibilite=ecarts,
    )
