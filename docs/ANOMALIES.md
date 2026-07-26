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

L'application applique la **règle voulue** : une période portant un motif
`Maladie`, `Autres absences` ou `Abs sans solde` n'est pas rémunérée. Elle ne
compte pas dans les 30èmes, ne reçoit aucune quote-part de primes, et produit
0 €.

L'ambiguïté de saisie disparaissant par construction (§9.4), le cas qui faisait
diverger le classeur — dates d'absence portées par la ligne « période » — ne peut
plus se produire : une période d'absence place toujours ses dates sur la ligne
d'absence, à la saisie comme à l'export.

Un dossier **repris d'un classeur** dans lequel ces dates avaient été mal placées
est donc recalculé selon la règle correcte. Les dates elles-mêmes sont
intégralement récupérées (l'import lit les deux lignes) ; seul le montant change,
et il change dans le bon sens : le classeur le surévaluait.

> Une version antérieure exposait un réglage « Mode de compatibilité classeur v6 »
> qui permettait de reproduire le calcul erroné. Il a été retiré : sur un dossier
> saisi dans l'application il n'avait aucun effet, et sur un dossier importé il ne
> servait qu'à conserver un résultat faux.

### 🔶 Décision en attente du service paie

> Faut-il régulariser les dossiers historiques dont les périodes d'absence ont été
> valorisées à tort ? Réimporter le classeur dans l'application donne directement
> le montant corrigé et permet de mesurer l'écart, mais la décision de rectifier
> ou non des déclarations déjà transmises à Vivinter n'appartient pas à l'outil.

---

## 9.2 — Sept lignes pour dix périodes  — **levée**

### Constat

Le gabarit Vivinter ne comporte que **7 lignes** (lignes 26 à 32) alors que les
matrices gèrent **10 périodes**. Dans le classeur, les périodes 8, 9 et 10
n'étaient jamais déclarées à Vivinter, sans le moindre message.

### Traitement retenu

La limite est **supprimée**. À l'export, le tableau des périodes est étendu au
nombre de périodes du dossier (`export/gabarit.py`) : les lignes manquantes sont
insérées dans la feuille chargée en reprenant à l'identique la mise en forme
d'une ligne courante, et tout ce qui se trouve dessous — notes de bas de page,
bloc « Fait à », cadre « Cachet et Signature », mentions légales — descend
d'autant.

Le PDF **reste sur une seule page A4** : le rendu ramène toujours la zone
d'impression à la page, si bien qu'un tableau plus haut se traduit par une
échelle légèrement plus fine, jamais par une seconde page.

Les exports Excel et PDF consomment la même feuille étendue : les deux documents
déclarent exactement les mêmes lignes.

Un dossier de 7 périodes ou moins produit un document **strictement identique** à
celui du gabarit d'origine : aucune ligne n'est ajoutée.

### Limite restante

Le nombre de périodes reste borné à **10 par régime** (8 pour ML35). Ce n'est plus
une contrainte de l'attestation mais celle des **matrices du classeur** : les
onglets ML36 et ML37 ne comportent que 10 blocs de période (lignes 21 à 70 pour
ML36), et au-delà l'export Excel des matrices n'aurait plus où écrire. Lever cette
limite-là supposerait de restructurer les onglets matrices, ce qui romprait la
compatibilité avec le classeur.

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
avec un couple `(date_debut, date_fin)` et un seul motif. L'application place les
dates sur la bonne ligne à l'export — ligne « période » pour une activité, ligne
« motif d'absence » pour une absence.

L'import, lui, **lit les deux lignes** afin de ne perdre aucune date, quelle que
soit celle qui la portait dans le classeur.

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
ou plus. Ces dossiers étant désormais déclarés intégralement (§9.2), l'écart n'est
plus théorique : l'application applique la règle correcte, le classeur non.

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

## 7. Attestation d'un dossier ML35 : colonnes PUA/PFA, primes et taux vides *(décision à confirmer)*

Le classeur d'origine ne branche l'attestation Vivinter que sur les onglets ML36
et ML37 : un dossier ML35 produisait une attestation **vide**. L'application la
branche désormais sur le bloc « Perçu CPAM » de la ML35 (dates + montant
« À déclarer », ou « Congés annuels » pour une période `CA`).

Les colonnes **Dont PUA / PFA**, **Autres primes** et **Taux d'activité partielle**
sont laissées **vides** : la ML35 est un régime d'**incapacité totale**, sans
temps partiel ni ventilation de primes, et le classeur ne comporte aucune formule
les alimentant pour ce régime.

**Ce choix est cohérent avec la nature du régime, mais ne provient d'aucune
formule du classeur** : il n'a jamais été spécifié. Un bandeau d'information le
rappelle dans l'aperçu de l'attestation, et les trois colonnes peuvent être
réactivées si la règle métier l'exige.

---

## Récapitulatif des décisions en attente

| # | Décision | Qui tranche |
|---|---|---|
| 9.1 | Régulariser ou non les dossiers historiques dont les périodes d'absence ont été valorisées à tort ; à terme, désactiver le mode de compatibilité v6 | Service paie |
| 9.2 | Confirmer à Vivinter qu'une attestation de plus de 7 lignes est recevable — le format du formulaire est respecté, seul le nombre de lignes du tableau change | Service paie / Vivinter |
| 7 | Confirmer que l'attestation ML35 laisse vides les colonnes PUA/PFA, autres primes et taux d'activité partielle | Service paie / Vivinter |
