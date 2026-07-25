"""Adressage des cellules du classeur d'origine.

Ce module est la source unique de vérité pour la correspondance
« cellule Excel ↔ grandeur applicative ». Il est partagé par l'export (§6.1) et
par l'import d'un classeur historique (§9.4) afin qu'une seule table de
coordonnées existe dans le projet.
"""

from __future__ import annotations

FEUILLE_ML35 = "MATRICE ML35 VIERGE"
FEUILLE_ML36 = "MATRICE ML36 VIERGE"
FEUILLE_ML37 = "MATRICE ML37 VIERGE"
FEUILLE_ATTESTATION = "Attestation Vivinter"

NB_PERIODES = 10

# --------------------------------------------------------------------------
# ML36
# --------------------------------------------------------------------------

ML36_ENTREES = {
    "siret": "B1",
    "num_secu": "B2",
    "matricule": "B3",
    "nom": "B4",
    "prenom": "B5",
    "djt": "B6",
    "mois": "F1",
    "nb_jours_mois": "F2",
    "taux_initial": "B8",
    "taux_tpt": "D8",
    "tmf_100": "B10",
    "p_transfert_100": "B11",
    "maj_nuit": "E10",
    "maj_ferie": "E11",
    "paniers_r226": "E16",
    "montant_siaci": "I17",
    "pua": "I23",
    "pua_percue": "I24",
    "autres_primes": "I31",
}
ML36_BASES_LIBRES = ("B12", "B13", "B14")
ML36_MAJORATIONS_LIBRES = ("E12", "E13", "E14")

ML36_CALCULES = {
    "base_salariale": "B15",
    "total_majorations": "E15",
    "montant_reintegre": "I18",
    "perte_pua": "I25",
    "salaire_retabli_3201": "F4",
    "perte_cpam": "F72",
    "vivinter_percu": "F74",
}

#: Colonnes des quotes-parts, indexées par période (lignes 6 à 15).
ML36_QUOTES = {
    "quote_majorations": "I",
    "quote_paniers": "J",
    "quote_siaci": "K",
}
ML36_LIGNE_QUOTE_DEPART = 6
ML36_COLONNE_ABSENCE_SANS_SOLDE = "O"
ML36_LIGNE_PERIODE_DEPART = 21
ML36_LIGNE_RECAP_DEPART = 75


def ml36_lignes_periode(index: int) -> dict[str, int]:
    """Lignes du bloc de la période d'indice ``index`` (0-based)."""
    p = ML36_LIGNE_PERIODE_DEPART + 5 * index
    return {"periode": p, "absence": p + 1, "retabli": p + 2,
            "percu": p + 3, "perte": p + 4}


# --------------------------------------------------------------------------
# ML37
# --------------------------------------------------------------------------

ML37_ENTREES = {
    "siret": "B1",
    "num_secu": "B2",
    "matricule": "B3",
    "nom": "B4",
    "prenom": "B5",
    "date_at": "B6",
    "djt": "B7",
    "mois": "F1",
    "nb_jours_mois": "F2",
    "taux_initial": "B9",
    "taux_tpt": "D9",
    "taux_taxation": "F19",
    "tmf_100": "B11",
    "p_transfert_100": "B12",
    "remu_ca": "E11",
    "maj_nuit": "E12",
    "paniers_r226": "E17",
    "montant_siaci": "J19",
    "pua": "J23",
    "pua_percue": "J24",
    "autres_primes": "J30",
}
ML37_BASES_LIBRES = ("B13", "B14", "B15")
ML37_MAJORATIONS_LIBRES = ("E13", "E14", "E15")

ML37_CALCULES = {
    "base_salariale": "B16",
    "total_majorations": "E16",
    "montant_reintegre": "J20",
    "perte_pua": "J25",
    "salaire_retabli_3201": "F4",
    "percu_cpam": "F72",
    "perte_cpam": "F73",
    "vivinter_percu": "F75",
}

ML37_QUOTES = {
    "quote_majorations": "J",
    "quote_paniers": "K",
    "quote_siaci": "L",
}
ML37_LIGNE_QUOTE_DEPART = 5
ML37_COLONNE_ABSENCE_SANS_SOLDE = "P"
ML37_LIGNE_PERIODE_DEPART = 20
ML37_LIGNE_RECAP_DEPART = 76


def ml37_lignes_periode(index: int) -> dict[str, int]:
    p = ML37_LIGNE_PERIODE_DEPART + 5 * index
    return {"periode": p, "absence": p + 1, "retabli": p + 2,
            "percu": p + 3, "perte": p + 4}


# --------------------------------------------------------------------------
# ML35
# --------------------------------------------------------------------------

ML35_ENTREES = {
    "nb_jours_mois": "B1",
    "mois": "C1",
    "siret": "B2",
    "num_secu": "B3",
    "matricule": "B4",
    "nom": "B5",
    "prenom": "B6",
    "date_at": "B7",
    "djt": "B8",
    "fixe_100": "F2",
    "p_transfert": "F3",
    "majo": "F5",
    "paniers": "F6",
    "ij_total_tpt": "C17",
    "igr": "D17",
    "taux_perte": "F16",
    "taux_declaration": "L23",
}

ML35_CALCULES = {
    "fixe_plus_transfert": "F4",
    "total_remuneration": "F7",
    "ij_par_jour": "B14",
    "jours_ml35": "B17",
    "total_ij": "E17",
    "perte_declaree": "F17",
}

ML35_NB_PERIODES = 8
ML35_LIGNE_PERIODE_DEPART = 3      # lignes 3 à 10 : I=début, K=fin, L=nb jours, M=motif
ML35_LIGNE_IJ_DEPART = 14          # lignes 14 à 21 : H/J dates, K=IJ, L=IJ taxées
ML35_LIGNE_CPAM_DEPART = 24        # lignes 24 à 31 : perçu CPAM


# --------------------------------------------------------------------------
# Attestation Vivinter
# --------------------------------------------------------------------------

ATTESTATION_CHAMPS = {
    "nom": "D11",
    "prenom": "D13",
    "num_secu": "D15",
    "matricule": "D17",
    "num_dossier": "D19",
    "fait_a": "C36",
    "fait_le": "C38",
    "nom_redacteur": "C40",
    "telephone": "C42",
    "mail": "C44",
    # Case « Cachet et Signature » (fusion F38:H44), sous le libellé F36:H37.
    "initiales_redacteur": "F38",
}

ATTESTATION_RISQUES = {"INCAPACITÉ": "D5", "INVALIDITÉ": "H5"}
ATTESTATION_RISQUES_LIBELLES = {"D5": "INCAPACITE", "H5": "INVALIDITE"}
ATTESTATION_QUALIFICATIONS = {"PS": "D21", "PNC": "F21", "PNT": "H21"}

ATTESTATION_LIGNE_DEPART = 26      # lignes 26 à 32
ATTESTATION_NB_LIGNES = 7
ATTESTATION_COLONNES = {
    "date_debut": "B",
    "date_fin": "C",
    "montant": "D",
    "dont_pua_pfa": "E",
    "autres_primes": "G",
    "taux": "H",
}
