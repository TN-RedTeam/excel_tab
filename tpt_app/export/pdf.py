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
from . import gabarit
from .excel import CHEMIN_TEMPLATE, ExportBloque
from .rendu import rendre_page


def valeurs_attestation(attestation: ResultatAttestation,
                        supplement: int = 0) -> dict[str, str]:
    """Texte français de chaque cellule alimentée de l'attestation.

    Les dates sont systématiquement rendues au format ``JJ/MM/AAAA`` (§9.3), les
    montants au format ``#,##0.00 €`` et les taux en pourcentage à 2 décimales.
    """
    def champ(nom: str) -> str:
        """Coordonnée du champ, décalée si elle est sous le tableau étendu."""
        return gabarit.decaler(mc.ATTESTATION_CHAMPS[nom], supplement)

    valeurs: dict[str, str] = {
        champ("nom"): attestation.nom,
        champ("prenom"): attestation.prenom,
        champ("num_secu"): attestation.num_secu,
        champ("matricule"): attestation.matricule,
        champ("num_dossier"): attestation.num_dossier,
        champ("fait_a"): attestation.fait_a,
        champ("fait_le"): format_date(attestation.fait_le),
        champ("nom_redacteur"): attestation.nom_redacteur,
        champ("telephone"): attestation.telephone,
        champ("mail"): attestation.mail,
        champ("initiales_redacteur"): attestation.initiales_redacteur,
    }

    for libelle, coordonnee in mc.ATTESTATION_RISQUES.items():
        texte = mc.ATTESTATION_RISQUES_LIBELLES[coordonnee]
        marque = "(X)" if libelle == attestation.risque else "( )"
        valeurs[coordonnee] = f"{marque} {texte}"
    for libelle, coordonnee in mc.ATTESTATION_QUALIFICATIONS.items():
        marque = "(X)" if libelle == attestation.qualification else "( )"
        valeurs[coordonnee] = f"{marque} {libelle}"

    colonnes = mc.ATTESTATION_COLONNES
    for rang, ligne in enumerate(attestation.lignes[:attestation.nb_lignes_utiles]):
        numero = gabarit.ligne_periode(rang)
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

    # Le tableau est étendu au nombre de périodes ; la page reste unique, le
    # rendu s'adaptant à l'échelle nécessaire pour tenir sur une A4.
    attestation = resultat.attestation
    supplement = gabarit.etendre_tableau_periodes(feuille, attestation.nb_lignes_utiles)

    titre = f"Attestation Vivinter — {attestation.nom} " \
            f"{attestation.prenom}".strip()
    return rendre_page(
        feuille,
        gabarit.plage_impression(supplement),
        destination,
        valeurs=valeurs_attestation(attestation, supplement),
        titre=titre,
    )
