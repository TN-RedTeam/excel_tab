"""Export PDF de l'attestation Vivinter (§6.2).

Le rendu reprend la zone d'impression ``A1:I55`` de l'onglet « Attestation
Vivinter » sur une page A4 portrait unique. La charte (polices, couleurs,
fusions, bordures, images) est lue dans le template embarqué par
``rendu.RenduFeuille`` ; ce module n'a la charge que du contenu.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl

from .. import mapping_classeur as mc
from ..core.arrondi import format_date, format_euro, format_pourcent
from ..core.models import Dossier, ResultatAttestation
from ..core.moteur import ResultatDossier
from .excel import CHEMIN_TEMPLATE, ExportBloque
from .rendu import rendre_page

PLAGE_IMPRESSION = "A1:I55"


def valeurs_attestation(attestation: ResultatAttestation) -> dict[str, str]:
    """Texte français de chaque cellule alimentée de l'attestation.

    Les dates sont systématiquement rendues au format ``JJ/MM/AAAA`` (§9.3), les
    montants au format ``#,##0.00 €`` et les taux en pourcentage à 2 décimales.
    """
    valeurs: dict[str, str] = {
        mc.ATTESTATION_CHAMPS["nom"]: attestation.nom,
        mc.ATTESTATION_CHAMPS["prenom"]: attestation.prenom,
        mc.ATTESTATION_CHAMPS["num_secu"]: attestation.num_secu,
        mc.ATTESTATION_CHAMPS["matricule"]: attestation.matricule,
        mc.ATTESTATION_CHAMPS["num_dossier"]: attestation.num_dossier,
        mc.ATTESTATION_CHAMPS["fait_a"]: attestation.fait_a,
        mc.ATTESTATION_CHAMPS["fait_le"]: format_date(attestation.fait_le),
        mc.ATTESTATION_CHAMPS["nom_redacteur"]: attestation.nom_redacteur,
        mc.ATTESTATION_CHAMPS["telephone"]: attestation.telephone,
        mc.ATTESTATION_CHAMPS["mail"]: attestation.mail,
        mc.ATTESTATION_CHAMPS["initiales_redacteur"]:
            attestation.initiales_redacteur,
    }

    for libelle, coordonnee in mc.ATTESTATION_RISQUES.items():
        texte = mc.ATTESTATION_RISQUES_LIBELLES[coordonnee]
        marque = "(X)" if libelle == attestation.risque else "( )"
        valeurs[coordonnee] = f"{marque} {texte}"
    for libelle, coordonnee in mc.ATTESTATION_QUALIFICATIONS.items():
        marque = "(X)" if libelle == attestation.qualification else "( )"
        valeurs[coordonnee] = f"{marque} {libelle}"

    colonnes = mc.ATTESTATION_COLONNES
    for rang, ligne in enumerate(attestation.lignes):
        numero = mc.ATTESTATION_LIGNE_DEPART + rang
        valeurs[f"{colonnes['date_debut']}{numero}"] = format_date(ligne.date_debut)
        valeurs[f"{colonnes['date_fin']}{numero}"] = format_date(ligne.date_fin)
        if ligne.vide:
            valeurs[f"{colonnes['montant']}{numero}"] = ""
        elif ligne.libelle:
            valeurs[f"{colonnes['montant']}{numero}"] = ligne.libelle
        else:
            valeurs[f"{colonnes['montant']}{numero}"] = format_euro(ligne.montant)
        # Colonnes E/F et G : vides lorsque le montant vaut 0 €.
        valeurs[f"{colonnes['dont_pua_pfa']}{numero}"] = format_euro(
            ligne.dont_pua_pfa, vide_si_zero=True)
        valeurs[f"{colonnes['autres_primes']}{numero}"] = format_euro(
            ligne.autres_primes, vide_si_zero=True)
        valeurs[f"{colonnes['taux']}{numero}"] = format_pourcent(ligne.taux)

    return valeurs


def exporter(dossier: Dossier, resultat: ResultatDossier, destination,
             ignorer_controles: bool = False) -> Path:
    """Produit l'attestation au format PDF, une page A4 portrait."""
    if not ignorer_controles:
        bloquantes = [a for a in resultat.anomalies_export if a.bloquante]
        if bloquantes:
            raise ExportBloque(" ".join(a.message for a in bloquantes))

    classeur = openpyxl.load_workbook(CHEMIN_TEMPLATE)
    feuille = classeur[mc.FEUILLE_ATTESTATION]
    titre = f"Attestation Vivinter — {resultat.attestation.nom} " \
            f"{resultat.attestation.prenom}".strip()
    return rendre_page(
        feuille,
        PLAGE_IMPRESSION,
        destination,
        valeurs=valeurs_attestation(resultat.attestation),
        titre=titre,
    )
