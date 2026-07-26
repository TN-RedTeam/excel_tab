"""Modèle de données du calculateur TPT.

Le vocabulaire suit celui du classeur ``CALCULATEUR_TPT_V6_9_attest_Vivinter.xlsx`` :
chaque champ porte en commentaire la cellule d'origine, de façon à pouvoir
remonter d'une valeur applicative à la formule Excel correspondante.

Ce module n'importe ni PySide6 ni openpyxl : il est testable seul.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from .arrondi import ZERO, dec

# --------------------------------------------------------------------------
# Régimes et motifs
# --------------------------------------------------------------------------

REGIME_ML35 = "ML35"
REGIME_ML36 = "ML36"
REGIME_ML37 = "ML37"
REGIMES = (REGIME_ML35, REGIME_ML36, REGIME_ML37)

MOTIF_CA = "CA"

#: Motifs principaux proposés par le classeur, par régime (liste ``$Q$2:$Q$6``
#: pour ML35/ML36, ``$R$2:$R$4`` pour ML37).
MOTIFS_PRINCIPAUX = {
    REGIME_ML35: ("ML35", "CA"),
    REGIME_ML36: ("ML36",),
    REGIME_ML37: ("ML37", "CA"),
}

#: Motifs d'absence proposés par le classeur (liste ``$R$2:$R$5`` pour ML36,
#: ``$S$2:$S$4`` pour ML37). ML35 ne comporte pas de ligne « motif d'absence ».
MOTIFS_ABSENCE = {
    REGIME_ML35: (),
    REGIME_ML36: ("Maladie", "CA / JEM", "Autres absences", "Abs sans solde"),
    REGIME_ML37: ("MALADIE", "JEM", "Abs sans solde"),
}

#: Libellé exact du motif déclenchant la déduction « absence sans solde ».
ABS_SANS_SOLDE = "Abs sans solde"


def motifs_proposes(regime: str) -> tuple[str, ...]:
    """Tous les motifs d'un régime, activité et absences confondues.

    Le classeur séparait le motif d'activité et le motif d'absence sur deux
    lignes distinctes, donc deux listes déroulantes. Une période ne pouvant
    porter qu'un seul motif, l'application n'en propose qu'une.
    """
    return MOTIFS_PRINCIPAUX.get(regime, ()) + MOTIFS_ABSENCE.get(regime, ())


def decomposer_motif(regime: str, motif: str) -> tuple[str, str]:
    """Traduit le motif choisi en couple (motif principal, motif d'absence).

    Un motif d'absence laisse le motif principal au régime lui-même : c'est ce
    que porte la ligne « période » de la matrice, la ligne « motif d'absence »
    recevant l'absence et les dates.
    """
    motif = (motif or "").strip()
    if not motif:
        return ("", "")
    if motif in MOTIFS_ABSENCE.get(regime, ()):
        principal = MOTIFS_PRINCIPAUX.get(regime, ("",))[0]
        return (principal, motif)
    return (motif, "")


def recomposer_motif(motif_principal: str, motif_absence: str) -> str:
    """Opération inverse : le motif à présenter dans la liste déroulante."""
    return (motif_absence or motif_principal or "").strip()


NB_PERIODES_MAX = 10
NB_PERIODES_MAX_ML35 = 8
#: Nombre de lignes de période du gabarit Vivinter. Ce n'est plus une limite :
#: l'attestation est étendue autant que nécessaire (cf. `export/gabarit.py`).
NB_LIGNES_ATTESTATION_MODELE = 7

QUALIFICATIONS = ("PS", "PNC", "PNT")
RISQUES = ("INCAPACITÉ", "INVALIDITÉ")

MAIL_VIVINTER = "mail.csprh.vivinter@airfrance.fr"
LIEU_PAR_DEFAUT = "ROISSY CDG"


# --------------------------------------------------------------------------
# Période
# --------------------------------------------------------------------------


@dataclass
class Periode:
    """Une période continue au sein du mois traité.

    Dans le classeur, une période occupe deux lignes : la « ligne période »
    (motif d'activité + dates) et la « ligne motif d'absence » (motif d'absence +
    dates). L'utilisateur saisissait les dates sur l'une ou l'autre selon la
    liste déroulante employée, ce qui cassait silencieusement le calcul en cas
    d'erreur de ligne. L'application supprime cette ambiguïté : un seul couple de
    dates, placé automatiquement sur la bonne ligne à l'export.
    """

    motif_principal: str = ""
    motif_absence: str = ""
    date_debut: Optional[dt.date] = None
    date_fin: Optional[dt.date] = None

    @property
    def renseignee(self) -> bool:
        """Vrai dès qu'une date de début est saisie, quelle que soit la ligne."""
        return self.date_debut is not None

    @property
    def est_absence(self) -> bool:
        """Vrai si un motif d'absence est sélectionné."""
        return bool(self.motif_absence)

    @property
    def sur_ligne_periode(self) -> bool:
        """Vrai si les dates alimentent la ligne « période » de la matrice.

        Une période d'absence porte ses dates sur la ligne « motif d'absence » :
        elle n'est pas rémunérée, ne compte pas dans les 30èmes, et ne reçoit
        donc aucune quote-part de primes.
        """
        return not self.est_absence

    @property
    def nb_jours_calendaires(self) -> Decimal:
        """``date_fin − date_debut + 1``, ou 0 si la période est vide."""
        if self.date_debut is None or self.date_fin is None:
            return ZERO
        return Decimal((self.date_fin - self.date_debut).days + 1)

    def nb_jours_ligne_periode(self) -> Decimal:
        """Colonne ``D_p`` de la matrice : 0 si les dates sont sur l'autre ligne."""
        if not self.sur_ligne_periode:
            return ZERO
        return self.nb_jours_calendaires

    def nb_jours_ligne_absence(self) -> Decimal:
        """Nombre de jours porté par la ligne « motif d'absence »."""
        if self.sur_ligne_periode:
            return ZERO
        return self.nb_jours_calendaires

    def motifs(self) -> tuple[str, str]:
        """Le couple (motif principal, motif d'absence)."""
        return (self.motif_principal or "", self.motif_absence or "")


# --------------------------------------------------------------------------
# Dossiers
# --------------------------------------------------------------------------


@dataclass
class Salarie:
    """Identité du salarié, commune aux trois régimes."""

    siret: str = ""          # B1 (ML36/ML37) — B2 (ML35)
    num_secu: str = ""       # B2 (ML36/ML37) — B3 (ML35)
    matricule: str = ""      # B3 (ML36/ML37) — B4 (ML35)
    nom: str = ""            # B4 (ML36/ML37) — B5 (ML35)
    prenom: str = ""         # B5 (ML36/ML37) — B6 (ML35)
    date_at: Optional[dt.date] = None   # B6 (ML37) — B7 (ML35)
    djt: Optional[dt.date] = None       # B6 (ML36) — B7 (ML37) — B8 (ML35)


@dataclass
class DossierML36:
    """Saisie complète d'un dossier ML36 (onglet « MATRICE ML36 VIERGE »)."""

    salarie: Salarie = field(default_factory=Salarie)
    mois: Optional[dt.date] = None            # F1
    nb_jours_mois: int = 30                   # F2
    taux_initial: Decimal = Decimal(1)        # B8
    taux_tpt: Decimal = Decimal("0.4")        # D8

    tmf_100: Decimal = ZERO                   # B10
    p_transfert_100: Decimal = ZERO           # B11
    bases_libres: list[Decimal] = field(default_factory=lambda: [ZERO, ZERO, ZERO])  # B12:B14
    #: Intitulés des lignes libres, écrits en colonne A du classeur (A12:A14).
    libelles_bases_libres: list[str] = field(default_factory=lambda: ["", "", ""])

    maj_nuit: Decimal = ZERO                  # E10
    maj_ferie: Decimal = ZERO                 # E11
    majorations_libres: list[Decimal] = field(default_factory=lambda: [ZERO, ZERO, ZERO])  # E12:E14
    #: Intitulés des lignes libres de majorations (D12:D14).
    libelles_majorations_libres: list[str] = field(default_factory=lambda: ["", "", ""])

    paniers_r226: Decimal = ZERO              # E16
    montant_siaci: Decimal = ZERO             # I17
    pua: Decimal = ZERO                       # I23
    pua_percue: Decimal = ZERO                # I24
    autres_primes: Decimal = ZERO             # I31

    periodes: list[Periode] = field(default_factory=list)

    @property
    def base_salariale(self) -> Decimal:
        """``B15 = SUM(B10:B14)``."""
        return dec(self.tmf_100) + dec(self.p_transfert_100) + sum(
            (dec(v) for v in self.bases_libres), ZERO
        )

    @property
    def total_majorations(self) -> Decimal:
        """``E15 = SUM(E10:E14)``."""
        return dec(self.maj_nuit) + dec(self.maj_ferie) + sum(
            (dec(v) for v in self.majorations_libres), ZERO
        )


@dataclass
class DossierML37:
    """Saisie complète d'un dossier ML37 (onglet « MATRICE ML37 VIERGE »)."""

    salarie: Salarie = field(default_factory=Salarie)
    mois: Optional[dt.date] = None            # F1
    nb_jours_mois: int = 30                   # F2
    taux_initial: Decimal = Decimal(1)        # B9
    taux_tpt: Decimal = Decimal("0.5")        # D9
    taux_taxation: Decimal = Decimal("0.21")  # F19

    tmf_100: Decimal = ZERO                   # B11
    p_transfert_100: Decimal = ZERO           # B12
    bases_libres: list[Decimal] = field(default_factory=lambda: [ZERO, ZERO, ZERO])  # B13:B15
    #: Intitulés des lignes libres, écrits en colonne A du classeur (A13:A15).
    libelles_bases_libres: list[str] = field(default_factory=lambda: ["", "", ""])

    remu_ca: Decimal = ZERO                   # E11
    maj_nuit: Decimal = ZERO                  # E12
    majorations_libres: list[Decimal] = field(default_factory=lambda: [ZERO, ZERO, ZERO])  # E13:E15
    #: Intitulés des lignes libres de majorations (D13:D15).
    libelles_majorations_libres: list[str] = field(default_factory=lambda: ["", "", ""])

    paniers_r226: Decimal = ZERO              # E17
    montant_siaci: Decimal = ZERO             # J19
    pua: Decimal = ZERO                       # J23
    pua_percue: Decimal = ZERO                # J24
    autres_primes: Decimal = ZERO             # J30

    periodes: list[Periode] = field(default_factory=list)

    @property
    def base_salariale(self) -> Decimal:
        """``B16 = SUM(B11:B15)``."""
        return dec(self.tmf_100) + dec(self.p_transfert_100) + sum(
            (dec(v) for v in self.bases_libres), ZERO
        )

    @property
    def total_majorations(self) -> Decimal:
        """``E16 = SUM(E11:E15)``."""
        return dec(self.remu_ca) + dec(self.maj_nuit) + sum(
            (dec(v) for v in self.majorations_libres), ZERO
        )


@dataclass
class DossierML35:
    """Saisie complète d'un dossier ML35 (onglet « MATRICE ML35 VIERGE »)."""

    salarie: Salarie = field(default_factory=Salarie)
    mois: Optional[dt.date] = None            # C1
    nb_jours_mois: int = 30                   # B1

    fixe_100: Decimal = ZERO                  # F2
    p_transfert: Decimal = ZERO               # F3
    #: Lignes libres du groupe « base », qui s'ajoutent au sous-total F4.
    bases_libres: list[Decimal] = field(default_factory=lambda: [ZERO, ZERO, ZERO])
    libelles_bases_libres: list[str] = field(default_factory=lambda: ["", "", ""])

    majo: Decimal = ZERO                      # F5
    paniers: Decimal = ZERO                   # F6
    #: Lignes libres du groupe « majorations », qui s'ajoutent au total F7.
    majorations_libres: list[Decimal] = field(default_factory=lambda: [ZERO, ZERO, ZERO])
    libelles_majorations_libres: list[str] = field(default_factory=lambda: ["", "", ""])

    ij_total_tpt: Decimal = ZERO              # C17
    igr: Decimal = ZERO                       # D17
    taux_perte: Decimal = Decimal("0.21")     # F16
    taux_declaration: Decimal = Decimal("0.21")  # L23

    periodes: list[Periode] = field(default_factory=list)

    @property
    def fixe_plus_transfert(self) -> Decimal:
        """``F4 = F2 + F3`` augmenté des lignes de base libres."""
        return (dec(self.fixe_100) + dec(self.p_transfert)
                + sum((dec(v) for v in self.bases_libres), ZERO))

    @property
    def total_remuneration(self) -> Decimal:
        """``F7 = F4 + F5 + F6`` augmenté des lignes de majoration libres."""
        return (self.fixe_plus_transfert + dec(self.majo) + dec(self.paniers)
                + sum((dec(v) for v in self.majorations_libres), ZERO))


@dataclass
class Attestation:
    """Champs de l'attestation qui ne proviennent pas des matrices."""

    num_dossier: str = ""
    qualification: str = "PS"
    risque: str = "INCAPACITÉ"
    fait_a: str = LIEU_PAR_DEFAUT
    fait_le: Optional[dt.date] = None
    nom_redacteur: str = ""
    telephone: str = ""
    mail: str = MAIL_VIVINTER


@dataclass
class Dossier:
    """Un dossier complet : identité, régime actif, matrices et attestation."""

    identifiant: Optional[int] = None
    libelle: str = ""
    regime: str = REGIME_ML36
    ml35: DossierML35 = field(default_factory=DossierML35)
    ml36: DossierML36 = field(default_factory=DossierML36)
    ml37: DossierML37 = field(default_factory=DossierML37)
    attestation: Attestation = field(default_factory=Attestation)
    cree_le: Optional[dt.datetime] = None
    modifie_le: Optional[dt.datetime] = None

    def matrice_active(self):
        """Renvoie la sous-saisie correspondant au régime sélectionné."""
        return {
            REGIME_ML35: self.ml35,
            REGIME_ML36: self.ml36,
            REGIME_ML37: self.ml37,
        }[self.regime]


# --------------------------------------------------------------------------
# Résultats
# --------------------------------------------------------------------------


@dataclass
class ResultatPeriode:
    """Résultats d'une période, tous régimes ML36/ML37 confondus."""

    index: int
    date_debut: Optional[dt.date] = None
    date_fin: Optional[dt.date] = None
    motif_principal: str = ""
    motif_absence: str = ""

    nb_jours: Decimal = ZERO                # D_p
    trentieme: Decimal = ZERO               # E_p
    trentieme_hors_regime: Decimal = ZERO   # E_{p+1} (ML37 uniquement)

    quote_majorations: Decimal = ZERO       # I(6+i) / J(5+i)
    quote_paniers: Decimal = ZERO           # J(6+i) / K(5+i)
    quote_siaci: Decimal = ZERO             # K(6+i) / L(5+i)
    quote_pua: Decimal = ZERO               # F_{p+2} / G_{p+2}
    quote_pua_percue: Decimal = ZERO        # F_{p+3} / G_{p+3}
    quote_autres_primes: Decimal = ZERO     # H_r du bloc récapitulatif

    absence_sans_solde: Decimal = ZERO      # O(6+i) / P(5+i)

    retabli_base: Decimal = ZERO            # B_{p+2}
    retabli_total: Decimal = ZERO           # D_{p+2}
    percu_base: Decimal = ZERO              # B_{p+3}
    percu_total: Decimal = ZERO             # D_{p+3}
    perte: Decimal = ZERO                   # D_{p+4}

    taxation_percu: Decimal = ZERO          # F_{p+3} (ML37)
    taxation_perte: Decimal = ZERO          # F_{p+4} (ML37)

    montant_declare: Decimal = ZERO         # F_r du bloc récapitulatif
    dont_pua_pfa: Decimal = ZERO            # G_r
    autres_primes: Decimal = ZERO           # H_r

    #: Noms des grandeurs que le classeur laisserait vides (formules ``""``).
    vides: frozenset[str] = frozenset()

    @property
    def renseignee(self) -> bool:
        return self.date_debut is not None


@dataclass
class ResultatMatrice:
    """Résultats consolidés d'une matrice ML36 ou ML37."""

    regime: str
    periodes: list[ResultatPeriode] = field(default_factory=list)

    base_salariale: Decimal = ZERO          # B15 / B16
    total_majorations: Decimal = ZERO       # E15 / E16
    paniers: Decimal = ZERO                 # E16 / E17
    montant_reintegre: Decimal = ZERO       # I18 / J20
    perte_pua: Decimal = ZERO               # I25 / J25
    somme_trentiemes: Decimal = ZERO        # S
    total_absences_sans_solde: Decimal = ZERO

    salaire_retabli_3201: Decimal = ZERO    # F4
    percu_cpam: Decimal = ZERO              # F72 (ML37)
    perte_cpam: Decimal = ZERO              # F72 (ML36) / F73 (ML37)
    vivinter_percu: Decimal = ZERO          # F74 (ML36) / F75 (ML37)


@dataclass
class ResultatPeriodeML35:
    """Résultats d'une période ML35 (lignes 3 à 10 de la matrice)."""

    index: int
    date_debut: Optional[dt.date] = None
    date_fin: Optional[dt.date] = None
    motif: str = ""
    nb_jours: Decimal = ZERO                # L_n
    ij_a_retirer: Decimal = ZERO            # K_(11+n)
    ij_taxees: Decimal = ZERO               # L_(11+n)
    fixe: Decimal = ZERO                    # H_r
    majo_paniers: Decimal = ZERO            # I_r
    a_declarer: Decimal = ZERO              # K_r
    a_declarer_taxe: Decimal = ZERO         # L_r


@dataclass
class ResultatML35:
    """Résultats consolidés d'un dossier ML35."""

    periodes: list[ResultatPeriodeML35] = field(default_factory=list)
    jours_ml35: Decimal = ZERO              # B17
    ij_par_jour: Decimal = ZERO             # B14
    total_ij: Decimal = ZERO                # E17
    perte_declaree: Decimal = ZERO          # F17
    fixe_plus_transfert: Decimal = ZERO     # F4
    total_remuneration: Decimal = ZERO      # F7
    total_a_declarer: Decimal = ZERO
    total_a_declarer_taxe: Decimal = ZERO


@dataclass
class LigneAttestation:
    """Une des 7 lignes de période de l'attestation Vivinter."""

    index: int                              # 1 à 7
    source: Optional[str] = None            # "ML36", "ML37" ou None
    date_debut: Optional[dt.date] = None    # colonne B
    date_fin: Optional[dt.date] = None      # colonne C
    libelle: Optional[str] = None           # colonne D, si un motif s'applique
    montant: Optional[Decimal] = None       # colonne D, sinon
    dont_pua_pfa: Optional[Decimal] = None  # colonnes E/F
    autres_primes: Optional[Decimal] = None  # colonne G
    taux: Optional[Decimal] = None          # colonne H

    @property
    def vide(self) -> bool:
        return self.source is None


@dataclass
class ResultatAttestation:
    """Attestation complète prête à être affichée ou exportée."""

    nom: str = ""
    prenom: str = ""
    num_secu: str = ""
    matricule: str = ""
    num_dossier: str = ""
    qualification: str = "PS"
    risque: str = "INCAPACITÉ"
    fait_a: str = LIEU_PAR_DEFAUT
    fait_le: Optional[dt.date] = None
    nom_redacteur: str = ""
    telephone: str = ""
    mail: str = MAIL_VIVINTER
    lignes: list[LigneAttestation] = field(default_factory=list)
    #: Initiales du rédacteur, reportées dans la case « Cachet et Signature ».
    initiales_redacteur: str = ""

    @property
    def nb_lignes_utiles(self) -> int:
        """Nombre de lignes à imprimer : au moins celles du gabarit d'origine."""
        remplies = [ligne.index for ligne in self.lignes if not ligne.vide]
        return max(NB_LIGNES_ATTESTATION_MODELE, max(remplies, default=0))
