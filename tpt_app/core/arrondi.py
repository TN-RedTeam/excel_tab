"""Conversions et arrondis monétaires.

Toutes les valeurs monétaires du moteur circulent en ``Decimal``. L'arrondi au
centime (``ROUND_HALF_UP``, comme Excel) n'est appliqué qu'au moment de
l'affichage ou de l'export, jamais dans les calculs intermédiaires.
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal, ROUND_HALF_UP

CENTIME = Decimal("0.01")
ZERO = Decimal(0)
TRENTE = Decimal(30)

#: Taux de réintégration du montant SIACI (ML36 I18, ML37 J20).
TAUX_SIACI = Decimal("0.245")

#: Correctif d'arrondi historique appliqué au calcul des 30èmes.
CORRECTIF_TRENTIEME = Decimal("0.0005")

#: Séparateur de milliers. L'usage typographique français est l'espace fine
#: insécable (U+202F), mais elle est absente des polices Type 1 utilisées en
#: dernier recours par ReportLab : on retient l'espace ordinaire, rendue
#: correctement par Excel comme par le PDF.
SEPARATEUR_MILLIERS = " "

#: Espaces à ignorer lors de la lecture d'un montant saisi.
_ESPACES = (" ", "\t", "\xa0", " ", " ")


def dec(valeur) -> Decimal:
    """Convertit une saisie quelconque en ``Decimal``.

    Une valeur vide (``None``, chaîne vide) vaut zéro. Les ``float`` passent par
    leur représentation textuelle pour éviter de traîner l'imprécision binaire.
    """
    if valeur is None:
        return ZERO
    if isinstance(valeur, Decimal):
        return valeur
    if isinstance(valeur, bool):
        return Decimal(int(valeur))
    if isinstance(valeur, int):
        return Decimal(valeur)
    if isinstance(valeur, float):
        return Decimal(repr(valeur))
    texte = str(valeur).strip()
    for espace in _ESPACES:
        texte = texte.replace(espace, "")
    texte = texte.replace("€", "").replace("%", "").replace(",", ".")
    if not texte:
        return ZERO
    return Decimal(texte)


def arrondi_centime(valeur) -> Decimal:
    """Arrondit au centime le plus proche, les demis vers le haut."""
    return dec(valeur).quantize(CENTIME, rounding=ROUND_HALF_UP)


def format_euro(valeur, vide_si_zero: bool = False) -> str:
    """Formate un montant selon le format Excel ``#,##0.00 €`` en français."""
    if valeur is None:
        return ""
    montant = arrondi_centime(valeur)
    if vide_si_zero and montant == ZERO:
        return ""
    entier, _, decimales = f"{abs(montant):.2f}".partition(".")
    groupes = []
    while len(entier) > 3:
        groupes.insert(0, entier[-3:])
        entier = entier[:-3]
    groupes.insert(0, entier)
    signe = "-" if montant < ZERO else ""
    return f"{signe}{SEPARATEUR_MILLIERS.join(groupes)},{decimales} €"


def format_pourcent(valeur) -> str:
    """Formate un taux (0,4 → ``40,00 %``)."""
    if valeur is None:
        return ""
    pourcent = (dec(valeur) * 100).quantize(CENTIME, rounding=ROUND_HALF_UP)
    return f"{pourcent:.2f}".replace(".", ",") + " %"


def format_date(valeur: _dt.date | None) -> str:
    """Formate une date au format français ``JJ/MM/AAAA``."""
    if valeur is None:
        return ""
    return valeur.strftime("%d/%m/%Y")


def format_decimal(valeur, decimales: int = 2) -> str:
    """Formate un nombre nu avec la virgule décimale française."""
    if valeur is None:
        return ""
    quantum = Decimal(1).scaleb(-decimales)
    return f"{dec(valeur).quantize(quantum, rounding=ROUND_HALF_UP)}".replace(".", ",")
