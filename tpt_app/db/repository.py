"""Persistance locale des dossiers traités (SQLite, sans dépendance externe).

Le dossier est sérialisé en JSON dans une colonne unique : le schéma applicatif
peut évoluer sans migration, et les colonnes indexées (nom, matricule, mois,
régime) suffisent à la recherche de l'écran « Dossiers ».

**La base est strictement personnelle** : elle vit dans le profil Windows de
l'utilisateur, jamais sur un partage réseau. SQLite ne supporte pas de manière
fiable le verrouillage sur SMB, et deux personnes écrivant dans le même fichier
finiraient par le corrompre. Chacun a donc son propre historique ; le partage
d'un dossier passe par l'export puis l'import d'un classeur.
"""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from dataclasses import fields, is_dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from ..core.models import (
    Attestation,
    Dossier,
    DossierML35,
    DossierML36,
    DossierML37,
    Periode,
    Salarie,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS dossiers (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    libelle      TEXT    NOT NULL DEFAULT '',
    nom          TEXT    NOT NULL DEFAULT '',
    prenom       TEXT    NOT NULL DEFAULT '',
    matricule    TEXT    NOT NULL DEFAULT '',
    regime       TEXT    NOT NULL DEFAULT 'ML36',
    mois         TEXT,
    donnees      TEXT    NOT NULL,
    cree_le      TEXT    NOT NULL,
    modifie_le   TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dossiers_nom ON dossiers(nom);
CREATE INDEX IF NOT EXISTS idx_dossiers_matricule ON dossiers(matricule);
CREATE INDEX IF NOT EXISTS idx_dossiers_mois ON dossiers(mois);
"""

#: Classes reconstruites à la lecture, par nom de champ du dossier.
_SOUS_DOSSIERS = {"ml35": DossierML35, "ml36": DossierML36, "ml37": DossierML37}


# --------------------------------------------------------------------------
# Sérialisation
# --------------------------------------------------------------------------


def _encoder(valeur: Any) -> Any:
    if is_dataclass(valeur):
        return {champ.name: _encoder(getattr(valeur, champ.name))
                for champ in fields(valeur)}
    if isinstance(valeur, Decimal):
        return {"__decimal__": str(valeur)}
    if isinstance(valeur, dt.datetime):
        return {"__datetime__": valeur.isoformat()}
    if isinstance(valeur, dt.date):
        return {"__date__": valeur.isoformat()}
    if isinstance(valeur, (list, tuple)):
        return [_encoder(element) for element in valeur]
    if isinstance(valeur, dict):
        return {clef: _encoder(element) for clef, element in valeur.items()}
    return valeur


def _decoder(valeur: Any) -> Any:
    if isinstance(valeur, dict):
        if "__decimal__" in valeur:
            return Decimal(valeur["__decimal__"])
        if "__datetime__" in valeur:
            return dt.datetime.fromisoformat(valeur["__datetime__"])
        if "__date__" in valeur:
            return dt.date.fromisoformat(valeur["__date__"])
        return {clef: _decoder(element) for clef, element in valeur.items()}
    if isinstance(valeur, list):
        return [_decoder(element) for element in valeur]
    return valeur


def _construire(classe, donnees: dict):
    """Instancie une dataclass en ignorant les champs inconnus (compatibilité)."""
    noms = {champ.name for champ in fields(classe)}
    return classe(**{clef: valeur for clef, valeur in donnees.items() if clef in noms})


def serialiser(dossier: Dossier) -> str:
    return json.dumps(_encoder(dossier), ensure_ascii=False)


def deserialiser(charge: str) -> Dossier:
    brut = _decoder(json.loads(charge))

    sous_dossiers = {}
    for nom, classe in _SOUS_DOSSIERS.items():
        contenu = dict(brut.get(nom) or {})
        contenu["salarie"] = _construire(Salarie, contenu.get("salarie") or {})
        contenu["periodes"] = [_construire(Periode, p)
                               for p in contenu.get("periodes") or []]
        sous_dossiers[nom] = _construire(classe, contenu)

    principal = dict(brut)
    principal.update(sous_dossiers)
    principal["attestation"] = _construire(Attestation, brut.get("attestation") or {})
    return _construire(Dossier, principal)


# --------------------------------------------------------------------------
# Dépôt
# --------------------------------------------------------------------------


class DepotDossiers:
    """Accès à la base locale ``app.db``."""

    def __init__(self, chemin: Optional[Path] = None):
        self.chemin = Path(chemin) if chemin else Path("app.db")
        if self.chemin.parent != Path(""):
            self.chemin.parent.mkdir(parents=True, exist_ok=True)
        # ``timeout`` fait patienter plutôt qu'échouer si la base est
        # momentanément verrouillée (antivirus, seconde instance ouverte par la
        # même personne). Le journal WAL autorise lectures et écriture simultanées.
        self.connexion = sqlite3.connect(str(self.chemin), timeout=15.0)
        self.connexion.row_factory = sqlite3.Row
        try:
            self.connexion.execute("PRAGMA journal_mode=WAL")
            self.connexion.execute("PRAGMA synchronous=FULL")
        except sqlite3.DatabaseError:
            # Certains systèmes de fichiers réseau refusent le WAL : on reste
            # alors sur le journal par défaut, moins concurrent mais valide.
            pass
        self.connexion.executescript(SCHEMA)
        self.connexion.commit()

    def fermer(self) -> None:
        self.connexion.close()

    def __enter__(self) -> "DepotDossiers":
        return self

    def __exit__(self, *_) -> None:
        self.fermer()

    # -- écriture ---------------------------------------------------------

    def enregistrer(self, dossier: Dossier) -> int:
        """Crée ou met à jour le dossier et renvoie son identifiant."""
        matrice = dossier.matrice_active()
        maintenant = dt.datetime.now()
        dossier.modifie_le = maintenant
        if dossier.cree_le is None:
            dossier.cree_le = maintenant

        valeurs = (
            dossier.libelle,
            matrice.salarie.nom,
            matrice.salarie.prenom,
            matrice.salarie.matricule,
            dossier.regime,
            matrice.mois.isoformat() if matrice.mois else None,
            serialiser(dossier),
            dossier.cree_le.isoformat(),
            maintenant.isoformat(),
        )

        if dossier.identifiant is None:
            curseur = self.connexion.execute(
                "INSERT INTO dossiers (libelle, nom, prenom, matricule, regime, mois,"
                " donnees, cree_le, modifie_le) VALUES (?,?,?,?,?,?,?,?,?)",
                valeurs,
            )
            dossier.identifiant = int(curseur.lastrowid)
        else:
            self.connexion.execute(
                "UPDATE dossiers SET libelle=?, nom=?, prenom=?, matricule=?, regime=?,"
                " mois=?, donnees=?, cree_le=?, modifie_le=? WHERE id=?",
                valeurs + (dossier.identifiant,),
            )
        self.connexion.commit()
        return dossier.identifiant

    def supprimer(self, identifiant: int) -> None:
        self.connexion.execute("DELETE FROM dossiers WHERE id=?", (identifiant,))
        self.connexion.commit()

    # -- lecture ----------------------------------------------------------

    def charger(self, identifiant: int) -> Optional[Dossier]:
        ligne = self.connexion.execute(
            "SELECT * FROM dossiers WHERE id=?", (identifiant,)
        ).fetchone()
        if ligne is None:
            return None
        dossier = deserialiser(ligne["donnees"])
        dossier.identifiant = int(ligne["id"])
        return dossier

    def lister(self, recherche: str = "", regime: str = "",
               mois: str = "") -> list[dict]:
        """Liste les dossiers, filtrés par texte libre, régime et mois."""
        clauses, parametres = [], []
        if recherche:
            motif = f"%{recherche.strip()}%"
            clauses.append("(nom LIKE ? OR prenom LIKE ? OR matricule LIKE ?"
                           " OR libelle LIKE ?)")
            parametres += [motif] * 4
        if regime:
            clauses.append("regime = ?")
            parametres.append(regime)
        if mois:
            clauses.append("mois LIKE ?")
            parametres.append(f"{mois}%")

        requete = ("SELECT id, libelle, nom, prenom, matricule, regime, mois,"
                   " modifie_le FROM dossiers")
        if clauses:
            requete += " WHERE " + " AND ".join(clauses)
        requete += " ORDER BY modifie_le DESC"

        return [dict(ligne) for ligne in
                self.connexion.execute(requete, parametres).fetchall()]
