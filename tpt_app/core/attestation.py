"""Construction de l'attestation de prévoyance Vivinter.

L'attestation comporte 7 lignes de période (lignes 26 à 32 du classeur). Chaque
ligne est alimentée **indépendamment** : la source est choisie période par
période, jamais globalement, et ML36 est prioritaire sur ML37. Une même
attestation peut donc mélanger des lignes ML36 et des lignes ML37.
"""

from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal
from typing import Optional

from .arrondi import ZERO, dec
from .models import (
    NB_LIGNES_ATTESTATION,
    NB_PERIODES_MAX,
    REGIME_ML36,
    REGIME_ML37,
    Attestation,
    Dossier,
    LigneAttestation,
    ResultatAttestation,
    ResultatMatrice,
)

LIBELLE_MALADIE = "Maladie"
LIBELLE_CONGES = "Congés annuels"
LIBELLE_SANS_SOLDE = "Absence sans solde"

#: Libellés de la colonne D qui interdisent l'affichage d'un taux en colonne H.
LIBELLES_SANS_TAUX = ("", LIBELLE_MALADIE, LIBELLE_CONGES, LIBELLE_SANS_SOLDE)


def libelle_motif(motif_principal: str, motif_absence: str) -> Optional[str]:
    """Traduit le couple de motifs en libellé d'attestation.

    Le motif prime toujours sur le montant, et les tests portent sur les deux
    motifs de la période : si l'un des deux correspond, la règle s'applique.
    L'ordre d'évaluation est celui du classeur et ne doit pas être modifié.
    """
    motifs = [(m or "").strip() for m in (motif_principal, motif_absence)]
    minuscules = [m.lower() for m in motifs]

    if any("maladie" in m for m in minuscules):
        return LIBELLE_MALADIE
    if any(m.upper() == "CA" for m in motifs) \
            or any("jem" in m for m in minuscules) \
            or any("autres absence" in m for m in minuscules):
        return LIBELLE_CONGES
    if any("sans solde" in m for m in minuscules):
        return LIBELLE_SANS_SOLDE
    return None


def _montant_ou_vide(valeur: Decimal) -> Optional[Decimal]:
    """Les colonnes E/F et G restent vides lorsque le montant vaut 0 €."""
    if valeur is None:
        return None
    montant = dec(valeur)
    return None if montant == ZERO else montant


def _construire_ligne(index: int, source: str, resultat, taux: Decimal) -> LigneAttestation:
    libelle = libelle_motif(resultat.motif_principal, resultat.motif_absence)
    ligne = LigneAttestation(
        index=index,
        source=source,
        date_debut=resultat.date_debut,
        date_fin=resultat.date_fin,
        libelle=libelle,
        montant=None if libelle else dec(resultat.montant_declare),
        dont_pua_pfa=_montant_ou_vide(resultat.dont_pua_pfa),
        autres_primes=_montant_ou_vide(resultat.autres_primes),
    )
    # Colonne H : aucun taux dès que la colonne D porte un libellé d'absence.
    if libelle is None:
        ligne.taux = dec(taux)
    return ligne


#: Civilités à ignorer pour ne garder que le nom et le prénom du rédacteur.
CIVILITES = {"m", "m.", "mr", "mr.", "mme", "mme.", "mlle", "mlle.", "dr", "dr."}


def initiales(nom_complet: str) -> str:
    """Initiales d'un rédacteur : « Jean MARTIN » → ``J.M.``.

    Les civilités (M., Mme…) sont écartées afin que « M. MARTIN » donne ``M.``
    et non ``M.M.``. Les prénoms composés sont conservés : « Anne-Marie DUPONT »
    donne ``A.M.D.``.
    """
    lettres = []
    for mot in re.split(r"[\s\-']+", (nom_complet or "").strip()):
        if not mot or mot.lower() in CIVILITES:
            continue
        premier = mot[0]
        if premier.isalpha():
            lettres.append(premier.upper())
    return "".join(f"{lettre}." for lettre in lettres)


def _premier_non_vide(*valeurs: str) -> str:
    for valeur in valeurs:
        if valeur:
            return valeur
    return ""


def construire(
    dossier: Dossier,
    resultat_ml36: Optional[ResultatMatrice] = None,
    resultat_ml37: Optional[ResultatMatrice] = None,
    aujourdhui: Optional[dt.date] = None,
) -> ResultatAttestation:
    """Assemble l'attestation à partir des résultats des deux matrices.

    ``resultat_ml36`` et ``resultat_ml37`` peuvent être omis : la source
    correspondante est alors simplement considérée comme non renseignée.
    """
    lignes: list[LigneAttestation] = []
    hors_formulaire: list[LigneAttestation] = []

    taux_ml36 = dec(dossier.ml36.taux_tpt)   # D8
    taux_ml37 = dec(dossier.ml37.taux_tpt)   # D9

    for index in range(1, NB_PERIODES_MAX + 1):
        rang = index - 1
        r36 = resultat_ml36.periodes[rang] if resultat_ml36 else None
        r37 = resultat_ml37.periodes[rang] if resultat_ml37 else None

        if r36 is not None and r36.renseignee:
            ligne = _construire_ligne(index, REGIME_ML36, r36, taux_ml36)
        elif r37 is not None and r37.renseignee:
            ligne = _construire_ligne(index, REGIME_ML37, r37, taux_ml37)
        else:
            ligne = LigneAttestation(index=index)

        if index <= NB_LIGNES_ATTESTATION:
            lignes.append(ligne)
        elif not ligne.vide:
            hors_formulaire.append(ligne)

    parametres: Attestation = dossier.attestation
    return ResultatAttestation(
        nom=_premier_non_vide(dossier.ml36.salarie.nom, dossier.ml37.salarie.nom),
        prenom=_premier_non_vide(dossier.ml36.salarie.prenom, dossier.ml37.salarie.prenom),
        num_secu=_premier_non_vide(dossier.ml36.salarie.num_secu,
                                   dossier.ml37.salarie.num_secu),
        matricule=_premier_non_vide(dossier.ml36.salarie.matricule,
                                    dossier.ml37.salarie.matricule),
        num_dossier=parametres.num_dossier,
        qualification=parametres.qualification,
        risque=parametres.risque,
        fait_a=parametres.fait_a,
        fait_le=parametres.fait_le or aujourdhui or dt.date.today(),
        nom_redacteur=parametres.nom_redacteur,
        telephone=parametres.telephone,
        mail=parametres.mail,
        lignes=lignes,
        periodes_non_declarees=hors_formulaire,
        initiales_redacteur=initiales(parametres.nom_redacteur),
    )


def nom_fichier(attestation: ResultatAttestation, mois: Optional[dt.date],
                extension: str) -> str:
    """``ATTESTATION_VIVINTER_{NOM}_{MATRICULE}_{AAAA-MM}.{pdf|xlsx}``."""
    periode = mois.strftime("%Y-%m") if mois else "SANS-MOIS"
    nom = (attestation.nom or "SANS-NOM").upper().replace(" ", "-")
    matricule = attestation.matricule or "SANS-MATRICULE"
    return f"ATTESTATION_VIVINTER_{nom}_{matricule}_{periode}.{extension}"
