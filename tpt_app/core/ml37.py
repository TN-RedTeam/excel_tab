"""Moteur de calcul ML37 (onglet « MATRICE ML37 VIERGE »).

La période d'indice ``i`` occupe le bloc ``p = 20 + 5i`` : ``p`` porte le motif
principal (``ML37`` ou ``CA``) et les dates, ``p+1`` le motif d'absence, ``p+2``
le rétabli, ``p+3`` le perçu et ``p+4`` la perte.

Deux 30èmes coexistent : ``E_p`` pour l'activité ML37 et ``E_{p+1}`` pour
l'activité hors ML37 (congés annuels).
"""

from __future__ import annotations

from decimal import Decimal

from .arrondi import TAUX_SIACI, TRENTE, ZERO, dec
from .ml36 import trentieme
from .models import (
    ABS_SANS_SOLDE,
    MOTIF_CA,
    NB_PERIODES_MAX,
    REGIME_ML37,
    DossierML37,
    Periode,
    ResultatMatrice,
    ResultatPeriode,
)

MOTIF_MALADIE = "MALADIE"


def _quote_part(montant: Decimal, trente_periode: Decimal, somme: Decimal,
                nom: str, vides: set[str]) -> Decimal:
    if montant < ZERO:
        vides.add(nom)
        return ZERO
    if somme == ZERO:
        return ZERO
    return montant * (trente_periode / somme)


def _periodes_completees(dossier: DossierML37) -> list[Periode]:
    periodes = list(dossier.periodes[:NB_PERIODES_MAX])
    while len(periodes) < NB_PERIODES_MAX:
        periodes.append(Periode(motif_principal=REGIME_ML37))
    return periodes


def calculer(dossier: DossierML37) -> ResultatMatrice:
    """Calcule l'intégralité de la matrice ML37.

    Les tests ``A_p = "MALADIE"`` du classeur ne sont jamais vrais — ``MALADIE``
    appartient à la liste de la ligne ``A_{p+1}``. L'application applique la règle
    voulue : une période portant un motif d'absence produit un montant nul
    (cf. `ANOMALIES.md` §9.1).
    """
    periodes = _periodes_completees(dossier)

    base = dossier.base_salariale                 # B16
    majorations = dossier.total_majorations       # E16
    paniers = dec(dossier.paniers_r226)           # E17
    siaci = dec(dossier.montant_siaci)            # J19
    reintegre = siaci * TAUX_SIACI                # J20
    pua = dec(dossier.pua)                        # J23
    pua_percue = dec(dossier.pua_percue)          # J24
    autres_primes = dec(dossier.autres_primes)    # J30
    taux_initial = dec(dossier.taux_initial)      # B9
    taux_tpt = dec(dossier.taux_tpt)              # D9
    taux_taxation = dec(dossier.taux_taxation)    # F19
    nb_jours_mois = int(dossier.nb_jours_mois or 0)

    nb_jours = [p.nb_jours_ligne_periode() for p in periodes]                  # D_p

    trentiemes: list[Decimal] = []        # E_p    — activité ML37
    trentiemes_hors: list[Decimal] = []   # E_{p+1} — activité hors ML37
    for periode, jours in zip(periodes, nb_jours):
        brut = trentieme(jours, nb_jours_mois)
        motif = periode.motif_principal
        trentiemes.append(ZERO if motif == MOTIF_CA else brut)
        trentiemes_hors.append(ZERO if motif == REGIME_ML37 else brut)

    somme_trentiemes = sum(trentiemes, ZERO)                                   # S

    resultats: list[ResultatPeriode] = []
    for i, periode in enumerate(periodes):
        vides: set[str] = set()
        e_p = trentiemes[i]
        e_hors = trentiemes_hors[i]
        motif = periode.motif_principal

        # J(5+i) : la quote-part de majorations est nulle sur une période de CA.
        if motif == MOTIF_CA:
            q_majo = ZERO
        else:
            q_majo = _quote_part(majorations, e_p, somme_trentiemes,
                                 "quote_majorations", vides)
        q_paniers = _quote_part(paniers, e_p, somme_trentiemes, "quote_paniers", vides)
        q_siaci = _quote_part(reintegre, e_p, somme_trentiemes, "quote_siaci", vides)
        q_pua = _quote_part(pua, e_p, somme_trentiemes, "quote_pua", vides)
        q_pua_percue = _quote_part(pua_percue, e_p, somme_trentiemes,
                                   "quote_pua_percue", vides)
        q_autres = _quote_part(autres_primes, e_p, somme_trentiemes,
                               "quote_autres_primes", vides)

        # P(5+i)
        if periode.motif_absence == ABS_SANS_SOLDE:
            jours_absence = periode.nb_jours_ligne_absence() or periode.nb_jours_calendaires
            sans_solde = (base * (jours_absence * TRENTE) / Decimal(nb_jours_mois)) / TRENTE \
                if nb_jours_mois else ZERO
        else:
            sans_solde = ZERO

        # Une période d'absence n'est pas rémunérée.
        neutralisee = periode.est_absence

        if neutralisee or motif == MOTIF_MALADIE:
            retabli_base = ZERO
            retabli_total = ZERO
            percu_base = ZERO
            percu_total = ZERO
        elif motif == REGIME_ML37:
            retabli_base = (base * taux_initial * e_p) / TRENTE
            retabli_total = retabli_base + q_majo + q_paniers + q_pua
            percu_base = ((base * e_p) / TRENTE) * taux_tpt
            percu_total = percu_base + q_majo + q_paniers + q_siaci + q_pua_percue
        else:
            # Période hors ML37 (congés annuels) : le rétabli sert de perçu.
            retabli_base = (base * taux_initial * e_hors) / TRENTE
            retabli_total = ZERO
            percu_base = retabli_base
            percu_total = percu_base

        perte = ZERO if retabli_total == ZERO else retabli_total - percu_total

        # F_{p+3} / F_{p+4} : taxation au taux F19.
        if e_p > ZERO:
            taxation_percu = percu_total * taux_taxation
            taxation_perte = perte * taux_taxation
        else:
            taxation_percu = percu_base * taux_taxation
            # La colonne B de la ligne PERTE est vide dans le classeur.
            taxation_perte = ZERO

        montant_declare = ZERO if motif == MOTIF_CA else percu_total - q_paniers - q_siaci

        resultats.append(
            ResultatPeriode(
                index=i + 1,
                date_debut=periode.date_debut,
                date_fin=periode.date_fin,
                motif_principal=periode.motif_principal,
                motif_absence=periode.motif_absence,
                nb_jours=nb_jours[i],
                trentieme=e_p,
                trentieme_hors_regime=e_hors,
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
                taxation_percu=taxation_percu,
                taxation_perte=taxation_perte,
                montant_declare=montant_declare,
                dont_pua_pfa=q_pua_percue,
                autres_primes=q_autres,
                vides=frozenset(vides),
            )
        )

    total_sans_solde = sum((r.absence_sans_solde for r in resultats), ZERO)
    somme_percus = sum((r.percu_total for r in resultats), ZERO)

    # F4 = ($B$16*B9)+$E$17+$E$16-P5..P14+J23
    salaire_retabli = (base * taux_initial) + paniers + majorations - total_sans_solde + pua
    # F75 = IF(J20>0, ΣD_{p+3}-E17-J20, ΣD_{p+3}-E17)
    vivinter = somme_percus - paniers - (reintegre if reintegre > ZERO else ZERO)

    return ResultatMatrice(
        regime=REGIME_ML37,
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
