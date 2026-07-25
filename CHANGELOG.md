# Journal des modifications

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).

## [1.0.0] — 2026-07-25

Première version de l'application Windows remplaçant le classeur
`CALCULATEUR_TPT_V6_9_attest_Vivinter.xlsx`.

### Ajouté

**Moteur de calcul** (`tpt_app/core/`, sans dépendance à PySide6 ni openpyxl)
- Moteurs ML35, ML36 et ML37, transcrits formule par formule depuis le classeur.
- Construction de l'attestation Vivinter : sélection de la source **ligne par
  ligne**, ML36 prioritaire sur ML37.
- Contrôles de saisie : chevauchement de périodes, dates hors du mois traité,
  somme des jours excédant le mois, motif manquant ou inconnu, taux incohérents,
  numéro de sécurité sociale.
- Tous les montants en `Decimal`, arrondi `ROUND_HALF_UP` à l'affichage et à
  l'export uniquement.

**Interface** (`tpt_app/ui/`, PySide6)
- Fenêtre unique, navigation en 6 étapes dans un rail latéral.
- Recalcul instantané à chaque frappe, sans bouton « Calculer ».
- Aperçu de l'attestation en temps réel.
- Validation affichée sous le champ concerné, jamais en boîte de dialogue modale.
- Champs calculés visuellement distincts, thèmes clair et sombre.
- Raccourcis `Ctrl+N`, `Ctrl+S`, `Ctrl+E`, `Ctrl+P`, `F5` ; barre d'état.
- Interface intégralement en français, navigable au clavier.

**Exports** (`tpt_app/export/`)
- Excel : remplissage du template embarqué, **aucun attribut de style modifié**,
  formules remplacées par les valeurs calculées.
- PDF : une page A4 portrait, charte lue directement dans le template
  (polices, fusions, bordures, images), polices Arial avec repli Liberation Sans
  embarqué.
- Nommage automatique `ATTESTATION_VIVINTER_{NOM}_{MATRICULE}_{AAAA-MM}`.

**Persistance et reprise de l'existant**
- Historique local SQLite (`app.db`) avec recherche et filtres.
- Import d'un classeur `.xlsx` existant, lisant **les deux lignes de saisie**
  afin de ne perdre aucune donnée historique.

**Tests**
- Les 7 tests d'acceptation du cahier des charges, au centime.
- 96 tests au total, 98 % de couverture sur le module de calcul.

### Corrigé par rapport au classeur

- **Priorité du motif sur le montant** : une période « Maladie » affiche
  `Maladie`, jamais son montant.
- **Masquage des zéros** : les colonnes « Dont PUA / PFA » et « Autres primes »
  restent vides à 0 €.
- **Trois erreurs de recopie ML37** : `J14` testait `A57` au lieu de `A65` ;
  `F63`, `F64`, `F68` et `F69` testaient `$E$55` au lieu de `$E$60` et `$E$65`.
- **Divisions par zéro** : un dossier sans période ne produit plus `#DIV/0!` ni
  `#VALEUR!` mais des résultats nuls.
- **Formats de date** : `JJ/MM/AAAA` partout, calendrier français.
- **Ligne de saisie ambiguë** : supprimée par construction ; l'import continue de
  lire les deux lignes.

### Modifié

- La colonne « Autres primes » de l'attestation, auparavant saisie à la main, est
  désormais **calculée** et ventilée au prorata des 30èmes.

### Points de vigilance

- Le **mode de compatibilité classeur v6** est **activé par défaut** : il
  reproduit le garde-fou inopérant du classeur (§9.1 de `docs/ANOMALIES.md`).
  Un avertissement chiffré s'affiche à l'étape « Résultats » dès que les deux
  modes divergent. Le choix définitif appartient au service paie.
- L'export est **bloqué** si des périodes au-delà de la 7ème sont renseignées ;
  une attestation de continuation peut être générée (§9.2).
- Le correctif d'arrondi historique `+0,0005` sur les 30èmes est **conservé à
  l'identique**.
