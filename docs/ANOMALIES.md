# Anomalies du classeur — traitement retenu et décisions en attente

Ce document reprend les quatre anomalies de la section 9 du cahier des charges,
indique ce que fait l'application, et **isole les décisions qui appartiennent au
service paie**.

Deux anomalies supplémentaires, découvertes lors de l'extraction des formules,
sont documentées en fin de document (§5 et §6).

---

## 9.1 — Code mort dans les mises à zéro

### Constat

Les formules ML36 testent `A_p = "Abs (Mal, CA, autres)"` :

```
B23 = IF(A21="Abs (Mal, CA, autres)", 0, ($B$15*$B$8*E21)/30)
```

Or cette valeur **n'existe dans aucune liste déroulante** du fichier. La liste
attachée à `A21` (`$Q$2:$Q$6`) ne contient que `ML36` ; celle attachée à `A22`
(`$R$2:$R$5`) contient `Maladie`, `CA / JEM`, `Autres absences`,
`Abs sans solde`. Le test n'est donc **jamais vrai**.

Même problème sur ML37 : `B22` et `D22` testent `A_p = "MALADIE"`, alors que
`MALADIE` appartient à la liste de la ligne `A_{p+1}` (`$S$2:$S$4`), jamais à
celle de `A_p` (`$R$2:$R$4`, qui contient `ML37` et `CA`).

### Portée réelle de l'anomalie

Elle est **plus étroite qu'il n'y paraît**, et il faut le dire précisément.

Dans l'usage courant, l'utilisateur choisit le motif d'absence dans la liste
déroulante de la ligne `p+1`, et saisit les dates **sur cette même ligne**. La
période d'absence a alors `D_p = 0`, donc `E_p = 0` : tous les montants sont nuls
de toute façon, et le garde-fou mort ne change rien.

L'anomalie ne se manifeste que lorsque les dates d'une période d'absence ont été
saisies sur la **ligne « période »** — ce que le tableur autorise (§9.4). Dans ce
cas seulement, la matrice calcule un salaire pour une période d'absence, et les
totaux `PERTE CPAM` et `VIVINTER ON DECLARE LE PERCU` sont **surévalués**.

### Traitement retenu

L'application implémente le calcul **correct** — une période portant un motif
`Maladie`, `Autres absences` ou `Abs sans solde` produit un montant nul — et
expose un réglage `Mode de compatibilité classeur v6`, **activé par défaut**,
qui reproduit le comportement historique.

| | Mode compatibilité v6 (défaut) | Mode corrigé |
|---|---|---|
| Période d'absence saisie dans l'application | montants nuls | montants nuls |
| Période d'absence **importée** avec dates sur la ligne « période » | montants calculés (comme le classeur) | montants nuls |

Les deux modes sont **toujours calculés**, et l'étape « Résultats » affiche un
avertissement détaillant l'écart poste par poste dès qu'ils divergent.

Pour un dossier saisi dans l'application, les deux modes donnent le même
résultat : le réglage n'a d'effet que sur les dossiers repris d'un classeur.

### 🔶 Décision en attente du service paie

> Faut-il régulariser les dossiers historiques dont les périodes d'absence ont été
> valorisées à tort ? L'application sait chiffrer l'écart dossier par dossier
> (bandeau de l'étape « Résultats »), mais la décision de rectifier ou non des
> déclarations déjà transmises à Vivinter n'appartient pas à l'outil.

---

## 9.2 — Sept lignes pour dix périodes

### Constat

L'attestation ne comporte que **7 lignes** (lignes 26 à 32) alors que les matrices
gèrent **10 périodes**. Les périodes 8, 9 et 10 ne sont jamais déclarées à
Vivinter, sans le moindre message.

### Traitement retenu

- L'export affiche les 7 lignes, contrainte de format Vivinter oblige.
- Dès qu'une période au-delà de la 7ème est renseignée, **l'export est bloqué**
  avec un message explicite nommant les périodes concernées
  (`validation.controler_export`).
- Un bouton **« Attestation de continuation »** apparaît dans l'étape
  « Attestation » et produit un second document pour les périodes restantes
  (suffixe `_SUITE`).

---

## 9.3 — Formats de date américains

### Constat

Toutes les cellules de saisie de dates du classeur sont au format `m/d/yyyy`,
y compris dans l'attestation (`B26:C32`, `C38`).

### Traitement retenu

`JJ/MM/AAAA` est le **seul format autorisé** dans l'application : en saisie, à
l'affichage et à l'export. Les sélecteurs de date utilisent le calendrier
français, la semaine commençant le lundi. L'export PDF écrit les dates déjà
formatées, sans dépendre du format de cellule du template.

> L'export Excel écrit de véritables dates dans les cellules du template, qui
> conservent leur format `m/d/yyyy` d'origine — le fichier reste ainsi
> rigoureusement identique au modèle Vivinter. Le PDF, lui, affiche `JJ/MM/AAAA`.

---

## 9.4 — Ligne de saisie ambiguë

### Constat

Le tableur accepte les dates sur deux lignes différentes selon la liste
déroulante employée : la ligne « période » (`B_p`/`C_p`) ou la ligne « motif
d'absence » (`B_{p+1}`/`C_{p+1}`). Les formules de l'attestation testent les deux,
mais **les formules de la matrice ne lisent que la ligne « période »** : choisir
la « mauvaise » ligne casse silencieusement le calcul.

### Traitement retenu

L'ambiguïté est supprimée **par construction** : une période est un objet unique,
avec un couple `(date_debut, date_fin)`, un motif principal et un motif
d'absence.

L'import, lui, **lit les deux lignes** et mémorise laquelle portait les dates
(`Periode.dates_sur_ligne_periode`), afin que le dossier repris reproduise
exactement le calcul d'origine. Dès que l'utilisateur modifie la ligne dans la
table des périodes, cette mémoire est effacée et la règle applicative reprend la
main.

---

## 5. Trois erreurs de recopie dans les formules ML37 *(hors cahier des charges)*

Découvertes lors de l'extraction.

| Cellule | Formule du classeur | Attendu | Effet |
|---|---|---|---|
| `J14` | `=IF(A57="CA",…)` | `A65` | La quote-part de majorations de la **10ème** période teste le motif de la **8ème** |
| `F63`, `F64` | `=+IF($E$55>0,…)` | `$E$60` | La taxation de la **9ème** période est pilotée par le 30ème de la **8ème** |
| `F68`, `F69` | `=+IF($E$55>0,…)` | `$E$65` | Idem pour la **10ème** période |

**Traitement retenu** : l'application applique la règle générale correcte — chaque
période teste son propre motif et son propre 30ème.

**Portée** : ces cellules ne divergent que sur les dossiers comportant 8 périodes
ou plus, c'est-à-dire précisément ceux que l'attestation ne peut pas déclarer
intégralement (§9.2). L'impact pratique est donc nul, mais l'écart est réel et
signalé ici pour mémoire.

---

## 6. Lignes vides produisant `#VALEUR!` en ML35 *(hors cahier des charges)*

`H24 = IF(L3=0,0,(($F$4/30)*(E24/$B$1*30)))` teste `L3=0`, mais `L3` vaut `""`
(chaîne vide) tant que la période n'est pas saisie — et `""=0` est **faux** en
Excel. La formule calcule donc avec une chaîne vide et renvoie `#VALEUR!`, ce que
confirment les valeurs en cache du classeur fourni.

De même, `B14 = C17/B17` renvoie `#DIV/0!` tant qu'aucune période ML35 n'est
saisie.

**Traitement retenu** : l'application renvoie `0` dans les deux cas. Aucune
division par zéro, aucune propagation d'erreur — cf. test d'acceptation 7.

---

## Récapitulatif des décisions en attente

| # | Décision | Qui tranche |
|---|---|---|
| 9.1 | Régulariser ou non les dossiers historiques dont les périodes d'absence ont été valorisées à tort ; à terme, désactiver le mode de compatibilité v6 | Service paie |
| 9.2 | Valider le principe de l'attestation de continuation auprès de Vivinter, ou obtenir un formulaire à plus de 7 lignes | Service paie / Vivinter |
