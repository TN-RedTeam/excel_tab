"""Moteur de calcul ML36 (onglet « MATRICE ML36 VIERGE »).

Correspondance des lignes : la période d'indice ``i`` (0-based) occupe le bloc
``p = 21 + 5i`` ; ``p`` porte le motif principal et les dates, ``p+1`` le motif
d'absence, ``p+2`` le rétabli, ``p+3`` le perçu et ``p+4`` la perte.
"""

from __future__ import annotations

from decimal import Decimal

from .arrondi import CORRECTIF_TRENTIEME, TAUX_SIACI, TRENTE, ZERO, dec
from .models import (
    ABS_SANS_SOLDE,
    NB_PERIODES_MAX,
    REGIME_ML36,
    DossierML36,
    Periode,
    ResultatMatrice,
    ResultatPeriode,
)


def trentieme(nb_jours: Decimal, nb_jours_mois: int) -> Decimal:
    """``E_p`` : quotité de la période exprimée en trentièmes du mois.

    ``=IF(D_p=0,0,IF(OR($F$2=30,$F$2=D_p),D_p*30/$F$2,(D_p*30/$F$2)+0.0005))``

    Le ``+0,0005`` est un correctif d'arrondi historique : il n'est appliqué que
    lorsque le mois ne compte pas 30 jours *et* que la période ne couvre pas le
    mois entier. Il est conservé à l'identique.
    """
    if nb_jours == ZERO:
        return ZERO
    diviseur = Decimal(nb_jours_mois)
    if diviseur == ZERO:
        return ZERO
    brut = nb_jours * TRENTE / diviseur
    if nb_jours_mois == 30 or diviseur == nb_jours:
        return brut
    return brut + CORRECTIF_TRENTIEME


def _quote_part(montant: Decimal, trente_periode: Decimal, somme: Decimal,
                nom: str, vides: set[str]) -> Decimal:
    """Ventile ``montant`` au prorata des 30èmes.

    Le classeur écrit ``""`` (cellule vide) lorsque le montant à ventiler est
    négatif ; on mémorise le cas dans ``vides`` et on retient 0 pour la suite des
    calculs — le classeur, lui, propagerait une erreur ``#VALEUR!``.
    """
    if montant < ZERO:
        vides.add(nom)
        return ZERO
    if somme == ZERO:
        # Le classeur renverrait #DIV/0! ; l'application neutralise la période.
        return ZERO
    return montant * (trente_periode / somme)


def _periodes_completees(dossier: DossierML36) -> list[Periode]:
    periodes = list(dossier.periodes[:NB_PERIODES_MAX])
    while len(periodes) < NB_PERIODES_MAX:
        periodes.append(Periode(motif_principal=REGIME_ML36))
    return periodes


def calculer(dossier: DossierML36, mode_compatibilite: bool = True) -> ResultatMatrice:
    """Calcule l'intégralité de la matrice ML36.

    ``mode_compatibilite`` reproduit le comportement du classeur v6 : le garde-fou
    ``IF(A_p="Abs (Mal, CA, autres)";0;…)`` n'y est jamais vrai, si bien qu'une
    période d'absence dont les dates ont été saisies sur la ligne « période »
    produit malgré tout un salaire. Désactivé, il applique la règle corrigée :
    une période portant un motif d'absence produit un montant nul.
    """
    periodes = _periodes_completees(dossier)

    base = dossier.base_salariale                 # B15
    majorations = dossier.total_majorations       # E15
    paniers = dec(dossier.paniers_r226)           # E16
    siaci = dec(dossier.montant_siaci)            # I17
    reintegre = siaci * TAUX_SIACI                # I18
    pua = dec(dossier.pua)                        # I23
    pua_percue = dec(dossier.pua_percue)          # I24
    autres_primes = dec(dossier.autres_primes)    # I31
    taux_initial = dec(dossier.taux_initial)      # B8
    taux_tpt = dec(dossier.taux_tpt)              # D8
    nb_jours_mois = int(dossier.nb_jours_mois or 0)

    nb_jours = [p.nb_jours_ligne_periode() for p in periodes]                 # D_p
    trentiemes = [trentieme(n, nb_jours_mois) for n in nb_jours]              # E_p
    somme_trentiemes = sum(trentiemes, ZERO)                                  # S

    resultats: list[ResultatPeriode] = []
    for i, periode in enumerate(periodes):
        vides: set[str] = set()
        e_p = trentiemes[i]

        q_majo = _quote_part(majorations, e_p, somme_trentiemes, "quote_majorations", vides)
        q_paniers = _quote_part(paniers, e_p, somme_trentiemes, "quote_paniers", vides)
        q_siaci = _quote_part(reintegre, e_p, somme_trentiemes, "quote_siaci", vides)
        q_pua = _quote_part(pua, e_p, somme_trentiemes, "quote_pua", vides)
        q_pua_percue = _quote_part(pua_percue, e_p, somme_trentiemes, "quote_pua_percue", vides)
        q_autres = _quote_part(autres_primes, e_p, somme_trentiemes,
                               "quote_autres_primes", vides)

        # O(6+i) : la déduction porte sur les jours de la ligne « motif d'absence ».
        if periode.motif_absence == ABS_SANS_SOLDE:
            jours_absence = periode.nb_jours_ligne_absence() or periode.nb_jours_calendaires
            sans_solde = (base * (jours_absence * TRENTE) / Decimal(nb_jours_mois)) / TRENTE \
                if nb_jours_mois else ZERO
        else:
            sans_solde = ZERO

        neutralisee = (not mode_compatibilite) and periode.est_absence

        if neutralisee:
            retabli_base = ZERO
            retabli_total = ZERO
            percu_base = ZERO
            percu_total = ZERO
        else:
            retabli_base = (base * taux_initial * e_p) / TRENTE                # B_{p+2}
            retabli_total = retabli_base + q_majo + q_paniers + q_pua          # D_{p+2}
            percu_base = ((base * e_p) / TRENTE) * taux_tpt                    # B_{p+3}
            percu_total = percu_base + q_majo + q_paniers + q_pua_percue + q_siaci  # D_{p+3}

        perte = retabli_total - percu_total                                    # D_{p+4}

        resultats.append(
            ResultatPeriode(
                index=i + 1,
                date_debut=periode.date_debut,
                date_fin=periode.date_fin,
                motif_principal=periode.motif_principal,
                motif_absence=periode.motif_absence,
                dates_sur_ligne_periode=periode.sur_ligne_periode,
                nb_jours=nb_jours[i],
                trentieme=e_p,
                quote_majorations=q_majo,
                quote_paniers=q_paniers,
                quote_siaci=q_siaci,
                quote_pua=q_pua,
                quote_pua_percue=q_pua_percue,
                quote_autres_primes=q_autres,
                absence_sans_solde=sans_solde,
                retabli_base=retabli_base,
                retabli_total=retabli_total,
                percu_base=percu_base,
                percu_total=percu_total,
                perte=perte,
                # Bloc récapitulatif lignes 75 à 84.
                montant_declare=percu_total - q_siaci - q_paniers,   # F_r
                dont_pua_pfa=q_pua_percue,                           # G_r
                autres_primes=q_autres,                              # H_r
                vides=frozenset(vides),
            )
        )

    total_sans_solde = sum((r.absence_sans_solde for r in resultats), ZERO)
    somme_percus = sum((r.percu_total for r in resultats), ZERO)

    # F4 = ($B$15*B8)+$E$15+$E$16-O6..O15+I23
    salaire_retabli = (base * taux_initial) + majorations + paniers - total_sans_solde + pua
    # F74 = IF(I18>0, ΣD_{p+3}-E16-I18, ΣD_{p+3}-E16)
    vivinter = somme_percus - paniers - (reintegre if reintegre > ZERO else ZERO)

    return ResultatMatrice(
        regime=REGIME_ML36,
        periodes=resultats,
        base_salariale=base,
        total_majorations=majorations,
        paniers=paniers,
        montant_reintegre=reintegre,
        perte_pua=pua - pua_percue,
        somme_trentiemes=somme_trentiemes,
        total_absences_sans_solde=total_sans_solde,
        salaire_retabli_3201=salaire_retabli,
        percu_cpam=somme_percus,
        perte_cpam=sum((r.perte for r in resultats), ZERO),
        vivinter_percu=vivinter,
    )
