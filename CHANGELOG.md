# Journal des modifications

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).

## [1.4.0] — 2026-07-26

### Ajouté

- **Colonnes de cotisations à 21 %** sur l'étape « Résultats » : le perçu et la
  perte de la ML37, et la retenue d'IJ et le montant à déclarer de la ML35, sont
  désormais accompagnés de leur cotisation.
- **L'attestation Vivinter est branchée sur la ML35.** Un dossier ML35 produisait
  jusqu'ici une attestation vide. Elle reprend maintenant les périodes du bloc
  « Perçu CPAM » : dates, montant « À DÉCLARER » (ou « Congés annuels » pour une
  période CA). Les colonnes Dont PUA/PFA, Autres primes et Taux restent vides
  (régime d'incapacité totale) — un bandeau d'information le signale et la
  décision est tracée dans `docs/ANOMALIES.md` (§7).
- **Lignes libres dans la rémunération ML35**, comme en ML36/ML37 : les lignes
  du groupe « base » s'ajoutent au sous-total F4, celles du groupe
  « majorations » au total F7. Chaque ligne a un intitulé saisissable.

### Modifié

- **Rémunération ML35** alignée sur la ML36/ML37 : « Base salariale »,
  « Majorations et primes » puis « Indemnités journalières ». Le champ
  « IJ / jour » est retiré de l'affichage.
- L'**adresse mail** de l'attestation ne se tronque plus dans l'aperçu à l'écran :
  sa taille de police s'ajuste pour tenir dans la case.
- Le **calendrier** s'ouvre partout sur le mois courant, y compris là où il
  s'ouvrait encore sur janvier 1900.

### Corrigé

- Un dossier **ML35 comportant des périodes** ne provoque plus d'erreur
  d'affichage : la ML35 raisonne en jours calendaires et n'a pas de 30ème, la
  colonne correspondante reste vide.

### Supprimé

- Le champ **SIACI** pour la ML35 : ce régime n'en comporte aucun dans le
  classeur. Il ne figure plus ni en saisie, ni dans les calculs, ni à l'export.

## [1.3.0] — 2026-07-25

### Supprimé

- **Le mode de compatibilité classeur v6.** Il n'avait aucun effet sur un dossier
  saisi dans l'application, et sur un dossier importé il ne servait qu'à
  reproduire un calcul erroné du classeur. L'application applique désormais
  toujours la règle voulue : une période d'absence n'est pas rémunérée.
  La case à cocher, le double calcul et le bandeau d'écart de l'étape
  « Résultats » disparaissent avec lui.
- Les **textes d'aide sous les champs** et les **sous-titres des étapes**. Les
  messages de contrôle continuent, eux, de s'afficher sous le champ concerné.

### Modifié

- Un dossier importé dont les dates d'absence figuraient sur la ligne « période »
  du classeur est recalculé selon la règle correcte. Les dates sont
  intégralement récupérées ; seul le montant change, et le classeur le
  surévaluait.

## [1.2.0] — 2026-07-25

### Ajouté

- **Intitulés des lignes libres modifiables** dans « Rémunération ». Le nom est
  enregistré avec le dossier et reporté dans la cellule d'en regard du classeur
  exporté (`A12:A14` et `D12:D14` en ML36, `A13:A15` et `D13:D15` en ML37) ;
  l'import le relit.

### Modifié

- **Un seul menu de motifs** dans « Périodes », réunissant l'activité et les
  absences du régime. Le classeur les séparait sur deux lignes, donc deux listes ;
  une période ne portant qu'un motif, une seule liste suffit.
- Une période ajoutée démarre avec un **motif vide**.
- **G27 aligné sur le reste du tableau.** Le gabarit laissait cette cellule en
  police par défaut et privait `B27`/`C27` de bordures horizontales, ce qui se
  voyait dès la deuxième période : toutes les lignes de période reçoivent
  désormais la même mise en forme.
- Champs de l'attestation élargis : un nom de rédacteur complet reste lisible.
- « Recalculer » quitte la barre d'outils — tout est déjà recalculé à chaque
  frappe. `F5` reste disponible en filet de sécurité.
- Le **mode de compatibilité v6** est grisé et porte la mention « sans effet
  ici » tant que les deux modes concordent, c'est-à-dire sur tout dossier saisi
  dans l'application.

### Robustesse en usage partagé

- **La base de dossiers est strictement personnelle** (`%APPDATA%\CalculateurTPT\`),
  jamais à côté de l'exécutable. SQLite ne verrouille pas de façon fiable sur un
  partage réseau : une base commune aurait été corrompue à la première écriture
  simultanée.
- SQLite passe en journal **WAL** avec attente de 15 s sur verrou.
- **Écriture atomique** des exports : le fichier est produit dans un temporaire
  puis mis en place d'un seul geste. Une coupure réseau ne laisse jamais un PDF
  tronqué à la place d'une version valide.
- **Plus d'écrasement silencieux** : un nom déjà pris est numéroté (`… (2).pdf`).
- Un fichier ouvert dans Acrobat ou Excel donne un message explicite au lieu
  d'un code d'erreur système.

### Optimisé

- Le fichier Excel exporté passe de **320 Ko à 45 Ko (−86 %)** : l'onglet
  « mode d'emploi » du classeur, qui pèse à lui seul 280 Ko d'images et n'a
  aucun rôle dans une attestation, est retiré de l'export.
- Les flux du PDF sont compressés. Une attestation pèse ~55 Ko, soit près de
  18 000 attestations par gigaoctet.

## [1.1.0] — 2026-07-25

### Modifié

- **La limite de 7 lignes de l'attestation est levée.** Toutes les périodes du
  dossier sont déclarées : le tableau du gabarit Vivinter est étendu au nombre
  nécessaire (`export/gabarit.py`), et les notes de bas de page, le bloc
  « Fait à », le cadre « Cachet et Signature » ainsi que les mentions légales
  descendent d'autant.
- Le **PDF reste sur une seule page A4** quel que soit le nombre de périodes :
  le rendu ramène toujours la zone d'impression à la page, un tableau plus haut
  se traduisant par une échelle plus fine, jamais par une seconde page.
- Les exports Excel et PDF partagent la même feuille étendue : les deux
  documents déclarent exactement les mêmes lignes.
- Un dossier de 7 périodes ou moins produit un document **strictement identique**
  à celui du gabarit d'origine.

### Supprimé

- Le blocage de l'export au-delà de la 7ème période, ainsi que le bouton
  « Attestation de continuation » qu'il rendait nécessaire.

### Limite restante

- Le nombre de périodes reste borné à **10 par régime** (8 en ML35) : ce n'est
  plus l'attestation qui contraint, mais la structure des onglets matrices du
  classeur, qui ne comportent que 10 blocs de période.

## [1.0.1] — 2026-07-25

Retours d'usage sur la première présentation.

### Corrigé

- **Les listes déroulantes des motifs ne montraient plus leur flèche.** Styler
  les sous-contrôles `::drop-down` et `::down-arrow` d'un `QComboBox` oblige Qt
  à fournir une image ; faute de quoi la flèche disparaît et le champ passe pour
  une zone en lecture seule. Les motifs d'absence étaient donc bien proposés mais
  paraissaient inaccessibles. Le rendu natif est rétabli.
- **Le calendrier s'ouvrait sur janvier 1900** sur un champ de date vide. Il
  s'ouvre désormais sur le mois et l'année en cours ; tourner la page ne
  remplit pas le champ.
- **La saisie d'une date au clavier était bloquée** sur un champ vide : la
  première frappe l'amorce maintenant à la date du jour, puis la saisie se
  poursuit normalement.
- Les textes d'aide sous les champs de date et le compteur de jours étaient
  tronqués : le message occupe désormais toute la largeur de la ligne.

### Modifié

- Le champ **Date AT** n'apparaît plus en ML36 : le classeur ne l'expose que sur
  les onglets ML35 (`B7`) et ML37 (`B6`).
- Les **initiales du rédacteur** sont reportées dans la case « Cachet et
  Signature » de l'attestation (`F38`), en aperçu comme à l'export PDF et Excel.
  Les civilités sont ignorées, les prénoms composés conservés.
- L'outil est présenté comme un outil **Air France** : la mention ALYZIA est
  retirée de la documentation et du nom d'organisation de l'application.

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
- Le correctif d'arrondi historique `+0,0005` sur les 30èmes est **conservé à
  l'identique**.
