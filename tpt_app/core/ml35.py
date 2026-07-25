"""Moteur de calcul ML35 (onglet « MATRICE ML35 VIERGE »).

ML35 suit une logique distincte de ML36/ML37 : jusqu'à 8 périodes saisies sur
les lignes 3 à 10, dont les résultats sont restitués lignes 14 à 21 (IJ à
retirer) puis lignes 24 à 31 (perçu CPAM).

L'attestation Vivinter ne lit pas cet onglet : un dossier ML35 produit une perte
à déclarer, pas une attestation de temps partiel.
"""

from __future__ import annotations

from decimal import Decimal

from .arrondi import TRENTE, ZERO, dec
from .models import (
    NB_PERIODES_MAX_ML35,
    REGIME_ML35,
    DossierML35,
    Periode,
    ResultatML35,
    ResultatPeriodeML35,
)


def _periodes_completees(dossier: DossierML35) -> list[Periode]:
    periodes = list(dossier.periodes[:NB_PERIODES_MAX_ML35])
    while len(periodes) < NB_PERIODES_MAX_ML35:
        periodes.append(Periode())
    return periodes


def _est_ml35(periode: Periode) -> bool:
    """Le classeur teste ``M_n="ML35"`` ; la liste déroulante propose ML35 et CA."""
    return (periode.motif_principal or "").strip().upper() == REGIME_ML35


def calculer(dossier: DossierML35) -> ResultatML35:
    """Calcule l'intégralité de la matrice ML35."""
    periodes = _periodes_completees(dossier)

    fixe_transfert = dossier.fixe_plus_transfert           # F4
    majo = dec(dossier.majo)                               # F5
    paniers = dec(dossier.paniers)                         # F6
    ij_total = dec(dossier.ij_total_tpt)                   # C17
    igr = dec(dossier.igr)                                 # D17
    taux_perte = dec(dossier.taux_perte)                   # F16
    taux_declaration = dec(dossier.taux_declaration)       # L23
    nb_jours_mois = Decimal(dossier.nb_jours_mois or 0)    # B1

    jours = [p.nb_jours_calendaires for p in periodes]     # L_n
    jours_ml35 = sum(                                       # B17
        (j for p, j in zip(periodes, jours) if _est_ml35(p)), ZERO
    )
    total_ij = ij_total + igr                              # E17
    perte_declaree = total_ij * taux_perte                 # F17
    ij_par_jour = ij_total / jours_ml35 if jours_ml35 else ZERO   # B14

    resultats: list[ResultatPeriodeML35] = []
    for i, (periode, nb) in enumerate(zip(periodes, jours)):
        ml35 = _est_ml35(periode)

        # K_(11+n) puis L_(11+n)
        if ml35 and jours_ml35:
            ij_a_retirer = total_ij * nb / jours_ml35
        else:
            ij_a_retirer = ZERO
        ij_taxees = ij_a_retirer * taux_perte

        # H_r : le classeur renverrait #VALEUR! sur une ligne vide ; ici 0.
        if nb == ZERO or nb_jours_mois == ZERO:
            fixe = ZERO
        else:
            fixe = (fixe_transfert / TRENTE) * (nb / nb_jours_mois * TRENTE)

        # I_r
        if ml35 and jours_ml35:
            majo_paniers = (majo + paniers) / jours_ml35 * nb
        else:
            majo_paniers = ZERO

        a_declarer = fixe + majo_paniers - ij_a_retirer     # K_r
        resultats.append(
            ResultatPeriodeML35(
                index=i + 1,
                date_debut=periode.date_debut,
                date_fin=periode.date_fin,
                motif=periode.motif_principal,
                nb_jours=nb,
                ij_a_retirer=ij_a_retirer,
                ij_taxees=ij_taxees,
                fixe=fixe,
                majo_paniers=majo_paniers,
                a_declarer=a_declarer,
                a_declarer_taxe=a_declarer * taux_declaration,   # L_r
            )
        )

    return ResultatML35(
        periodes=resultats,
        jours_ml35=jours_ml35,
        ij_par_jour=ij_par_jour,
        total_ij=total_ij,
        perte_declaree=perte_declaree,
        fixe_plus_transfert=fixe_transfert,
        total_remuneration=dossier.total_remuneration,
        total_a_declarer=sum((r.a_declarer for r in resultats), ZERO),
        total_a_declarer_taxe=sum((r.a_declarer_taxe for r in resultats), ZERO),
    )
