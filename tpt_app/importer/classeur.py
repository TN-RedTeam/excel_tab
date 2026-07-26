"""Import d'un classeur ``.xlsx`` existant (§7, §9.4).

Le tableur tolérait la saisie des dates sur deux lignes différentes selon la
liste déroulante employée. L'import lit donc **les deux lignes**, afin de ne
perdre aucune date, et le dossier repris est ensuite calculé selon la règle de
l'application.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path
from typing import Optional

import openpyxl

from .. import mapping_classeur as mc
from ..core.arrondi import ZERO, dec
from ..core.models import (
    Dossier,
    DossierML35,
    DossierML36,
    DossierML37,
    Periode,
    REGIME_ML35,
    REGIME_ML36,
    REGIME_ML37,
    Salarie,
    decomposer_motif,
)


class ImportImpossible(RuntimeError):
    """Le fichier n'est pas un classeur TPT exploitable."""


def _texte(feuille, coordonnee: str) -> str:
    valeur = feuille[coordonnee].value
    if valeur is None or isinstance(valeur, str) and valeur.startswith("="):
        return ""
    return str(valeur).strip()


def _montant(feuille, coordonnee: str) -> Decimal:
    valeur = feuille[coordonnee].value
    if valeur is None or isinstance(valeur, str) and valeur.startswith("="):
        return ZERO
    try:
        return dec(valeur)
    except Exception:
        return ZERO


def _date(feuille, coordonnee: str) -> Optional[dt.date]:
    valeur = feuille[coordonnee].value
    if isinstance(valeur, dt.datetime):
        return valeur.date()
    if isinstance(valeur, dt.date):
        return valeur
    return None


def _entier(feuille, coordonnee: str, defaut: int) -> int:
    valeur = feuille[coordonnee].value
    try:
        return int(valeur)
    except (TypeError, ValueError):
        return defaut


def _salarie(feuille, cellules: dict) -> Salarie:
    return Salarie(
        siret=_texte(feuille, cellules["siret"]),
        num_secu=_texte(feuille, cellules["num_secu"]),
        matricule=_texte(feuille, cellules["matricule"]),
        nom=_texte(feuille, cellules["nom"]),
        prenom=_texte(feuille, cellules["prenom"]),
        date_at=_date(feuille, cellules["date_at"]) if "date_at" in cellules else None,
        djt=_date(feuille, cellules["djt"]),
    )


def _lire_periode(feuille, lignes: dict) -> Periode:
    """Lit une période en examinant la ligne « période » puis la ligne « motif »."""
    ligne_periode, ligne_absence = lignes["periode"], lignes["absence"]

    debut_periode = _date(feuille, f"B{ligne_periode}")
    fin_periode = _date(feuille, f"C{ligne_periode}")
    debut_absence = _date(feuille, f"B{ligne_absence}")
    fin_absence = _date(feuille, f"C{ligne_absence}")

    if debut_periode is not None:
        debut, fin = debut_periode, fin_periode
    else:
        debut, fin = debut_absence, fin_absence

    return Periode(
        motif_principal=_texte(feuille, f"A{ligne_periode}"),
        motif_absence=_texte(feuille, f"A{ligne_absence}"),
        date_debut=debut,
        date_fin=fin,
    )


def _lire_ml36(feuille) -> DossierML36:
    cellules = mc.ML36_ENTREES
    return DossierML36(
        salarie=_salarie(feuille, cellules),
        mois=_date(feuille, cellules["mois"]),
        nb_jours_mois=_entier(feuille, cellules["nb_jours_mois"], 30),
        taux_initial=_montant(feuille, cellules["taux_initial"]) or Decimal(1),
        taux_tpt=_montant(feuille, cellules["taux_tpt"]),
        tmf_100=_montant(feuille, cellules["tmf_100"]),
        p_transfert_100=_montant(feuille, cellules["p_transfert_100"]),
        bases_libres=[_montant(feuille, c) for c in mc.ML36_BASES_LIBRES],
        libelles_bases_libres=[_texte(feuille, c)
                               for c in mc.ML36_LIBELLES_BASES_LIBRES],
        maj_nuit=_montant(feuille, cellules["maj_nuit"]),
        maj_ferie=_montant(feuille, cellules["maj_ferie"]),
        majorations_libres=[_montant(feuille, c) for c in mc.ML36_MAJORATIONS_LIBRES],
        libelles_majorations_libres=[_texte(feuille, c)
                                     for c in mc.ML36_LIBELLES_MAJORATIONS_LIBRES],
        paniers_r226=_montant(feuille, cellules["paniers_r226"]),
        montant_siaci=_montant(feuille, cellules["montant_siaci"]),
        pua=_montant(feuille, cellules["pua"]),
        pua_percue=_montant(feuille, cellules["pua_percue"]),
        autres_primes=_montant(feuille, cellules["autres_primes"]),
        periodes=[
            _lire_periode(feuille, mc.ml36_lignes_periode(index))
            for index in range(mc.NB_PERIODES)
        ],
    )


def _lire_ml37(feuille) -> DossierML37:
    cellules = mc.ML37_ENTREES
    return DossierML37(
        salarie=_salarie(feuille, cellules),
        mois=_date(feuille, cellules["mois"]),
        nb_jours_mois=_entier(feuille, cellules["nb_jours_mois"], 30),
        taux_initial=_montant(feuille, cellules["taux_initial"]) or Decimal(1),
        taux_tpt=_montant(feuille, cellules["taux_tpt"]),
        taux_taxation=_montant(feuille, cellules["taux_taxation"]) or Decimal("0.21"),
        tmf_100=_montant(feuille, cellules["tmf_100"]),
        p_transfert_100=_montant(feuille, cellules["p_transfert_100"]),
        bases_libres=[_montant(feuille, c) for c in mc.ML37_BASES_LIBRES],
        libelles_bases_libres=[_texte(feuille, c)
                               for c in mc.ML37_LIBELLES_BASES_LIBRES],
        remu_ca=_montant(feuille, cellules["remu_ca"]),
        maj_nuit=_montant(feuille, cellules["maj_nuit"]),
        majorations_libres=[_montant(feuille, c) for c in mc.ML37_MAJORATIONS_LIBRES],
        libelles_majorations_libres=[_texte(feuille, c)
                                     for c in mc.ML37_LIBELLES_MAJORATIONS_LIBRES],
        paniers_r226=_montant(feuille, cellules["paniers_r226"]),
        montant_siaci=_montant(feuille, cellules["montant_siaci"]),
        pua=_montant(feuille, cellules["pua"]),
        pua_percue=_montant(feuille, cellules["pua_percue"]),
        autres_primes=_montant(feuille, cellules["autres_primes"]),
        periodes=[
            _lire_periode(feuille, mc.ml37_lignes_periode(index))
            for index in range(mc.NB_PERIODES)
        ],
    )


def _lire_ml35(feuille) -> DossierML35:
    cellules = mc.ML35_ENTREES
    periodes = []
    for index in range(mc.ML35_NB_PERIODES):
        ligne = mc.ML35_LIGNE_PERIODE_DEPART + index
        principal, absence = decomposer_motif(
            REGIME_ML35, _texte(feuille, f"M{ligne}"))
        periodes.append(Periode(
            motif_principal=principal,
            motif_absence=absence,
            date_debut=_date(feuille, f"I{ligne}"),
            date_fin=_date(feuille, f"K{ligne}"),
        ))
    return DossierML35(
        salarie=_salarie(feuille, cellules),
        mois=_date(feuille, cellules["mois"]),
        nb_jours_mois=_entier(feuille, cellules["nb_jours_mois"], 30),
        fixe_100=_montant(feuille, cellules["fixe_100"]),
        p_transfert=_montant(feuille, cellules["p_transfert"]),
        majo=_montant(feuille, cellules["majo"]),
        paniers=_montant(feuille, cellules["paniers"]),
        bases_libres=[_montant(feuille, c) for c in mc.ML35_BASES_LIBRES],
        libelles_bases_libres=[_texte(feuille, c)
                               for c in mc.ML35_LIBELLES_BASES_LIBRES],
        majorations_libres=[_montant(feuille, c) for c in mc.ML35_MAJORATIONS_LIBRES],
        libelles_majorations_libres=[_texte(feuille, c)
                                     for c in mc.ML35_LIBELLES_MAJORATIONS_LIBRES],
        ij_total_tpt=_montant(feuille, cellules["ij_total_tpt"]),
        igr=_montant(feuille, cellules["igr"]),
        taux_perte=_montant(feuille, cellules["taux_perte"]) or Decimal("0.21"),
        taux_declaration=_montant(feuille, cellules["taux_declaration"]) or Decimal("0.21"),
        periodes=periodes,
    )


def _regime_renseigne(dossier) -> bool:
    return any(p.renseignee for p in dossier.periodes)


def importer(chemin) -> Dossier:
    """Reprend un dossier depuis un classeur TPT existant.

    Le régime actif est déduit des périodes réellement saisies : ML36 s'il en
    comporte, sinon ML37, sinon ML35.
    """
    chemin = Path(chemin)
    try:
        classeur = openpyxl.load_workbook(chemin, data_only=True)
    except Exception as erreur:      # fichier corrompu ou format inattendu
        raise ImportImpossible(
            f"Le fichier « {chemin.name} » n'a pas pu être ouvert : {erreur}"
        ) from erreur

    manquantes = [nom for nom in (mc.FEUILLE_ML35, mc.FEUILLE_ML36, mc.FEUILLE_ML37)
                  if nom not in classeur.sheetnames]
    if manquantes:
        raise ImportImpossible(
            "Le classeur ne comporte pas les onglets attendus : "
            + ", ".join(manquantes)
        )

    ml35 = _lire_ml35(classeur[mc.FEUILLE_ML35])
    ml36 = _lire_ml36(classeur[mc.FEUILLE_ML36])
    ml37 = _lire_ml37(classeur[mc.FEUILLE_ML37])

    if _regime_renseigne(ml36):
        regime = REGIME_ML36
    elif _regime_renseigne(ml37):
        regime = REGIME_ML37
    elif _regime_renseigne(ml35):
        regime = REGIME_ML35
    else:
        regime = REGIME_ML36

    dossier = Dossier(regime=regime, ml35=ml35, ml36=ml36, ml37=ml37)
    dossier.libelle = f"Import {chemin.stem}"
    return dossier
