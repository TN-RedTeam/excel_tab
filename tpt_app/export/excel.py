"""Export Excel par remplissage du template embarqué (§6.1).

Le classeur d'origine sert de gabarit : on n'écrit que ``cell.value``, jamais un
attribut de style, de fusion, de dimension ou de zone d'impression. Toutes les
formules sont remplacées par les valeurs calculées par le moteur Python, de
sorte que le fichier produit reste ouvrable sans recalcul et parfaitement
auditable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import openpyxl

from .. import mapping_classeur as mc
from ..core.arrondi import arrondi_centime, dec
from ..core.models import (
    Dossier,
    ResultatAttestation,
    ResultatMatrice,
    ResultatML35,
)
from ..core.moteur import ResultatDossier

CHEMIN_TEMPLATE = Path(__file__).resolve().parent / "template" / "attestation_template.xlsx"


class ExportBloque(RuntimeError):
    """Levée lorsqu'un contrôle interdit la production du fichier."""


def _nombre(valeur) -> Optional[float]:
    """Convertit un ``Decimal`` en flottant pour openpyxl, en arrondissant."""
    if valeur is None:
        return None
    return float(arrondi_centime(valeur))


def _brut(valeur) -> Optional[float]:
    """Convertit sans arrondir (taux, 30èmes, nombres de jours)."""
    if valeur is None:
        return None
    return float(dec(valeur))


def _ecrire(feuille, coordonnee: str, valeur) -> None:
    feuille[coordonnee] = valeur


# --------------------------------------------------------------------------
# Matrices
# --------------------------------------------------------------------------


def _remplir_matrice(feuille, saisie, resultat: ResultatMatrice, entrees: dict,
                     bases_libres: tuple, majorations_libres: tuple, calcules: dict,
                     quotes: dict, ligne_quote_depart: int, colonne_sans_solde: str,
                     lignes_periode, ligne_recap_depart: int, avec_taxation: bool) -> None:
    """Écrit une matrice ML36 ou ML37 en valeurs."""
    salarie = saisie.salarie
    valeurs_entrees = {
        "siret": salarie.siret,
        "num_secu": salarie.num_secu,
        "matricule": salarie.matricule,
        "nom": salarie.nom,
        "prenom": salarie.prenom,
        "djt": salarie.djt,
        "date_at": salarie.date_at,
        "mois": saisie.mois,
        "nb_jours_mois": saisie.nb_jours_mois,
        "taux_initial": _brut(saisie.taux_initial),
        "taux_tpt": _brut(saisie.taux_tpt),
        "taux_taxation": _brut(getattr(saisie, "taux_taxation", None)),
        "tmf_100": _nombre(saisie.tmf_100),
        "p_transfert_100": _nombre(saisie.p_transfert_100),
        "maj_nuit": _nombre(saisie.maj_nuit),
        "maj_ferie": _nombre(getattr(saisie, "maj_ferie", None)),
        "remu_ca": _nombre(getattr(saisie, "remu_ca", None)),
        "paniers_r226": _nombre(saisie.paniers_r226),
        "montant_siaci": _nombre(saisie.montant_siaci),
        "pua": _nombre(saisie.pua),
        "pua_percue": _nombre(saisie.pua_percue),
        "autres_primes": _nombre(saisie.autres_primes),
    }
    for nom, coordonnee in entrees.items():
        _ecrire(feuille, coordonnee, valeurs_entrees.get(nom))

    for coordonnee, valeur in zip(bases_libres, saisie.bases_libres):
        _ecrire(feuille, coordonnee, _nombre(valeur))
    for coordonnee, valeur in zip(majorations_libres, saisie.majorations_libres):
        _ecrire(feuille, coordonnee, _nombre(valeur))

    for nom, coordonnee in calcules.items():
        _ecrire(feuille, coordonnee, _nombre(getattr(resultat, nom)))

    for index, ligne in enumerate(resultat.periodes):
        rangs = lignes_periode(index)
        quote_ligne = ligne_quote_depart + index

        for nom, colonne in quotes.items():
            _ecrire(feuille, f"{colonne}{quote_ligne}", _nombre(getattr(ligne, nom)))
        _ecrire(feuille, f"{colonne_sans_solde}{quote_ligne}",
                _nombre(ligne.absence_sans_solde))

        sur_ligne_periode = ligne.dates_sur_ligne_periode
        _ecrire(feuille, f"A{rangs['periode']}", ligne.motif_principal or None)
        _ecrire(feuille, f"A{rangs['absence']}", ligne.motif_absence or None)
        if sur_ligne_periode:
            _ecrire(feuille, f"B{rangs['periode']}", ligne.date_debut)
            _ecrire(feuille, f"C{rangs['periode']}", ligne.date_fin)
            _ecrire(feuille, f"B{rangs['absence']}", None)
            _ecrire(feuille, f"C{rangs['absence']}", None)
        else:
            _ecrire(feuille, f"B{rangs['periode']}", None)
            _ecrire(feuille, f"C{rangs['periode']}", None)
            _ecrire(feuille, f"B{rangs['absence']}", ligne.date_debut)
            _ecrire(feuille, f"C{rangs['absence']}", ligne.date_fin)

        _ecrire(feuille, f"D{rangs['periode']}", _brut(ligne.nb_jours))
        _ecrire(feuille, f"E{rangs['periode']}", _brut(ligne.trentieme))
        if avec_taxation:
            _ecrire(feuille, f"E{rangs['absence']}", _brut(ligne.trentieme_hors_regime))

        colonne_pua = "G" if avec_taxation else "F"
        _ecrire(feuille, f"B{rangs['retabli']}", _nombre(ligne.retabli_base))
        _ecrire(feuille, f"D{rangs['retabli']}", _nombre(ligne.retabli_total))
        _ecrire(feuille, f"{colonne_pua}{rangs['retabli']}", _nombre(ligne.quote_pua))
        _ecrire(feuille, f"B{rangs['percu']}", _nombre(ligne.percu_base))
        _ecrire(feuille, f"D{rangs['percu']}", _nombre(ligne.percu_total))
        _ecrire(feuille, f"{colonne_pua}{rangs['percu']}", _nombre(ligne.quote_pua_percue))
        _ecrire(feuille, f"D{rangs['perte']}", _nombre(ligne.perte))
        if avec_taxation:
            _ecrire(feuille, f"F{rangs['percu']}", _nombre(ligne.taxation_percu))
            _ecrire(feuille, f"F{rangs['perte']}", _nombre(ligne.taxation_perte))

        recap = ligne_recap_depart + index
        _ecrire(feuille, f"C{recap}", ligne.date_debut)
        _ecrire(feuille, f"E{recap}", ligne.date_fin)
        _ecrire(feuille, f"F{recap}", _nombre(ligne.montant_declare))
        _ecrire(feuille, f"G{recap}", _nombre(ligne.dont_pua_pfa))
        _ecrire(feuille, f"H{recap}", _nombre(ligne.autres_primes))


def _remplir_ml35(feuille, saisie, resultat: ResultatML35) -> None:
    salarie = saisie.salarie
    valeurs = {
        "nb_jours_mois": saisie.nb_jours_mois,
        "mois": saisie.mois,
        "siret": salarie.siret,
        "num_secu": salarie.num_secu,
        "matricule": salarie.matricule,
        "nom": salarie.nom,
        "prenom": salarie.prenom,
        "date_at": salarie.date_at,
        "djt": salarie.djt,
        "fixe_100": _nombre(saisie.fixe_100),
        "p_transfert": _nombre(saisie.p_transfert),
        "majo": _nombre(saisie.majo),
        "paniers": _nombre(saisie.paniers),
        "ij_total_tpt": _nombre(saisie.ij_total_tpt),
        "igr": _nombre(saisie.igr),
        "taux_perte": _brut(saisie.taux_perte),
        "taux_declaration": _brut(saisie.taux_declaration),
    }
    for nom, coordonnee in mc.ML35_ENTREES.items():
        _ecrire(feuille, coordonnee, valeurs.get(nom))
    for nom, coordonnee in mc.ML35_CALCULES.items():
        valeur = getattr(resultat, nom)
        _ecrire(feuille, coordonnee,
                _brut(valeur) if nom == "jours_ml35" else _nombre(valeur))

    for index, ligne in enumerate(resultat.periodes):
        saisie_ligne = mc.ML35_LIGNE_PERIODE_DEPART + index
        _ecrire(feuille, f"I{saisie_ligne}", ligne.date_debut)
        _ecrire(feuille, f"K{saisie_ligne}", ligne.date_fin)
        _ecrire(feuille, f"L{saisie_ligne}", _brut(ligne.nb_jours) or None)
        _ecrire(feuille, f"M{saisie_ligne}", ligne.motif or None)

        ij = mc.ML35_LIGNE_IJ_DEPART + index
        _ecrire(feuille, f"H{ij}", ligne.date_debut)
        _ecrire(feuille, f"J{ij}", ligne.date_fin)
        _ecrire(feuille, f"K{ij}", _nombre(ligne.ij_a_retirer))
        _ecrire(feuille, f"L{ij}", _nombre(ligne.ij_taxees))

        cpam = mc.ML35_LIGNE_CPAM_DEPART + index
        _ecrire(feuille, f"B{cpam}", ligne.date_debut)
        _ecrire(feuille, f"D{cpam}", ligne.date_fin)
        _ecrire(feuille, f"E{cpam}", _brut(ligne.nb_jours) or None)
        _ecrire(feuille, f"F{cpam}", ligne.motif or None)
        _ecrire(feuille, f"H{cpam}", _nombre(ligne.fixe))
        _ecrire(feuille, f"I{cpam}", _nombre(ligne.majo_paniers))
        _ecrire(feuille, f"J{cpam}", _nombre(ligne.ij_a_retirer))
        _ecrire(feuille, f"K{cpam}", _nombre(ligne.a_declarer))
        _ecrire(feuille, f"L{cpam}", _nombre(ligne.a_declarer_taxe))


# --------------------------------------------------------------------------
# Attestation
# --------------------------------------------------------------------------


def _remplir_attestation(feuille, attestation: ResultatAttestation) -> None:
    valeurs = {
        "nom": attestation.nom,
        "prenom": attestation.prenom,
        "num_secu": attestation.num_secu,
        "matricule": attestation.matricule,
        "num_dossier": attestation.num_dossier,
        "fait_a": attestation.fait_a,
        "fait_le": attestation.fait_le,
        "nom_redacteur": attestation.nom_redacteur,
        "telephone": attestation.telephone,
        "mail": attestation.mail,
        "initiales_redacteur": attestation.initiales_redacteur,
    }
    for nom, coordonnee in mc.ATTESTATION_CHAMPS.items():
        _ecrire(feuille, coordonnee, valeurs.get(nom) or None)

    # Le formulaire papier propose les options côte à côte : on marque la retenue.
    for libelle, coordonnee in mc.ATTESTATION_RISQUES.items():
        texte = mc.ATTESTATION_RISQUES_LIBELLES[coordonnee]
        marque = "(X)" if libelle == attestation.risque else "( )"
        _ecrire(feuille, coordonnee, f"{marque} {texte}")
    for libelle, coordonnee in mc.ATTESTATION_QUALIFICATIONS.items():
        marque = "(X)" if libelle == attestation.qualification else "( )"
        _ecrire(feuille, coordonnee, f"{marque} {libelle}")

    for rang, ligne in enumerate(attestation.lignes):
        numero = mc.ATTESTATION_LIGNE_DEPART + rang
        colonnes = mc.ATTESTATION_COLONNES
        _ecrire(feuille, f"{colonnes['date_debut']}{numero}", ligne.date_debut)
        _ecrire(feuille, f"{colonnes['date_fin']}{numero}", ligne.date_fin)
        # Colonne D : le libellé prime toujours sur le montant.
        _ecrire(feuille, f"{colonnes['montant']}{numero}",
                ligne.libelle if ligne.libelle else _nombre(ligne.montant))
        _ecrire(feuille, f"{colonnes['dont_pua_pfa']}{numero}",
                _nombre(ligne.dont_pua_pfa))
        _ecrire(feuille, f"{colonnes['autres_primes']}{numero}",
                _nombre(ligne.autres_primes))
        _ecrire(feuille, f"{colonnes['taux']}{numero}", _brut(ligne.taux))


# --------------------------------------------------------------------------
# Point d'entrée
# --------------------------------------------------------------------------


def exporter(dossier: Dossier, resultat: ResultatDossier, destination,
             ignorer_controles: bool = False) -> Path:
    """Produit le classeur rempli à partir du template embarqué.

    Lève ``ExportBloque`` si des périodes au-delà de la 7ème sont renseignées
    (§9.2), sauf si ``ignorer_controles`` est vrai — cas de l'attestation de
    continuation, qui déclare précisément ces périodes-là.
    """
    if not ignorer_controles:
        bloquantes = [a for a in resultat.anomalies_export if a.bloquante]
        if bloquantes:
            raise ExportBloque(" ".join(a.message for a in bloquantes))

    classeur = openpyxl.load_workbook(CHEMIN_TEMPLATE)

    _remplir_matrice(
        classeur[mc.FEUILLE_ML36], dossier.ml36, resultat.ml36,
        mc.ML36_ENTREES, mc.ML36_BASES_LIBRES, mc.ML36_MAJORATIONS_LIBRES,
        mc.ML36_CALCULES, mc.ML36_QUOTES, mc.ML36_LIGNE_QUOTE_DEPART,
        mc.ML36_COLONNE_ABSENCE_SANS_SOLDE, mc.ml36_lignes_periode,
        mc.ML36_LIGNE_RECAP_DEPART, avec_taxation=False,
    )
    _remplir_matrice(
        classeur[mc.FEUILLE_ML37], dossier.ml37, resultat.ml37,
        mc.ML37_ENTREES, mc.ML37_BASES_LIBRES, mc.ML37_MAJORATIONS_LIBRES,
        mc.ML37_CALCULES, mc.ML37_QUOTES, mc.ML37_LIGNE_QUOTE_DEPART,
        mc.ML37_COLONNE_ABSENCE_SANS_SOLDE, mc.ml37_lignes_periode,
        mc.ML37_LIGNE_RECAP_DEPART, avec_taxation=True,
    )
    if resultat.ml35 is not None:
        _remplir_ml35(classeur[mc.FEUILLE_ML35], dossier.ml35, resultat.ml35)

    _remplir_attestation(classeur[mc.FEUILLE_ATTESTATION], resultat.attestation)

    chemin = Path(destination)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    classeur.save(chemin)
    return chemin
