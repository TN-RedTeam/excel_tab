"""Écriture de fichiers sûre en environnement partagé.

Plusieurs personnes utilisent l'outil en même temps, souvent sur les mêmes
dossiers réseau. Trois précautions en découlent :

* **écriture atomique** — le contenu est d'abord écrit dans un fichier temporaire
  du même dossier, puis renommé. Une coupure réseau ou un plantage ne laisse
  jamais un PDF tronqué à la place d'un fichier valide ;
* **noms uniques** — deux personnes exportant le même dossier le même mois
  obtiendraient le même nom : un suffixe numéroté évite l'écrasement silencieux ;
* **diagnostic clair** — un fichier ouvert dans Acrobat ou Excel est verrouillé
  par Windows ; le message le dit, au lieu d'un code d'erreur système.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Callable


class EcritureImpossible(OSError):
    """Le fichier de destination n'a pas pu être écrit."""


def chemin_disponible(destination) -> Path:
    """Renvoie un chemin libre, en numérotant si le fichier existe déjà.

    ``attestation.pdf`` occupé devient ``attestation (2).pdf``, puis ``(3)``…
    La numérotation s'arrête à 999, au-delà de quoi le chemin d'origine est
    renvoyé tel quel — la collision est alors traitée comme une erreur normale.
    """
    chemin = Path(destination)
    if not chemin.exists():
        return chemin
    for numero in range(2, 1000):
        candidat = chemin.with_name(f"{chemin.stem} ({numero}){chemin.suffix}")
        if not candidat.exists():
            return candidat
    return chemin


def ecrire_atomiquement(destination, produire: Callable[[Path], None]) -> Path:
    """Fait produire le fichier dans un temporaire, puis le met en place.

    ``produire`` reçoit le chemin temporaire à alimenter. Le remplacement final
    est atomique sur un même volume, y compris sur un partage réseau Windows.
    """
    chemin = Path(destination)
    chemin.parent.mkdir(parents=True, exist_ok=True)

    descripteur, temporaire = tempfile.mkstemp(
        dir=str(chemin.parent), prefix=f".{chemin.stem}-", suffix=chemin.suffix
    )
    os.close(descripteur)
    temporaire = Path(temporaire)

    try:
        produire(temporaire)
        os.replace(temporaire, chemin)
    except PermissionError as erreur:
        temporaire.unlink(missing_ok=True)
        raise EcritureImpossible(
            f"« {chemin.name} » est ouvert dans une autre application ou vous "
            f"n'avez pas les droits d'écriture sur ce dossier. Fermez le fichier "
            f"puis relancez l'export."
        ) from erreur
    except OSError as erreur:
        temporaire.unlink(missing_ok=True)
        raise EcritureImpossible(
            f"« {chemin.name} » n'a pas pu être écrit : {erreur}"
        ) from erreur
    return chemin
