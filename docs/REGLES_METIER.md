# Règles métier — traçabilité classeur → application

Ce document recense **chaque formule** du classeur
`CALCULATEUR_TPT_V6_9_attest_Vivinter.xlsx`, sa cellule d'origine et sa traduction
applicative. Il a été établi par extraction `openpyxl` en deux passes
(`data_only=False` pour les formules, `data_only=True` pour les valeurs en cache)
sur les quatre onglets : `MATRICE ML35 VIERGE`, `MATRICE ML36 VIERGE`,
`MATRICE ML37 VIERGE` et `Attestation Vivinter`.

La dernière section (« Écarts constatés ») croise cet inventaire avec la section 5
du cahier des charges et signale toutes les divergences.

---

## 1. Conventions

| Convention | Valeur |
|---|---|
| Type numérique | `decimal.Decimal` de bout en bout, jamais `float` |
| Arrondi | `ROUND_HALF_UP` à 2 décimales, **à l'affichage et à l'export uniquement** |
| Cellule vide Excel (`""`) | `None` à l'affichage, `0` dans les calculs suivants, cas mémorisé dans `ResultatPeriode.vides` |
| `#DIV/0!` | neutralisé : la grandeur vaut 0 (aucune période saisie) |
| Format de date | `JJ/MM/AAAA` en saisie, à l'affichage et à l'export |

Le module `tpt_app/mapping_classeur.py` est la source unique des coordonnées de
cellules ; il est partagé par l'export et par l'import.

---

## 2. MATRICE ML36

### 2.1 Entrées

| Cellule | Libellé | Champ applicatif |
|---|---|---|
| `B1` | SIRET | `Salarie.siret` |
| `B2` | N° SS | `Salarie.num_secu` |
| `B3` | Matricule | `Salarie.matricule` |
| `B4` | Nom | `Salarie.nom` |
| `B5` | Prénom | `Salarie.prenom` |
| `B6` | DJT | `Salarie.djt` |
| `F1` | Mois traité | `DossierML36.mois` |
| `F2` | Nb jours dans le mois | `DossierML36.nb_jours_mois` |
| `B8` | Taux initial | `taux_initial` |
| `D8` | Taux TPT | `taux_tpt` |
| `B10` | TMF à 100 % | `tmf_100` |
| `B11` | P. TRANSFERT à 100 % | `p_transfert_100` |
| `B12:B14` | Lignes libres | `bases_libres` |
| `E10` | MAJ NUIT | `maj_nuit` |
| `E11` | maj férié | `maj_ferie` |
| `E12:E14` | Lignes libres | `majorations_libres` |
| `E16` | PANIERS + R226 | `paniers_r226` |
| `I17` | Montant SIACI | `montant_siaci` |
| `I23` | PUA | `pua` |
| `I24` | PUA perçue | `pua_percue` |
| `I31` | AUTRES PRIMES | `autres_primes` |

### 2.2 Agrégats

| Cellule | Formule Excel | Règle applicative |
|---|---|---|
| `B15` | `=SUM(B10:B14)` | `DossierML36.base_salariale` |
| `E15` | `=SUM(E10:E14)` | `DossierML36.total_majorations` |
| `I18` | `=+I17*0.245` | `montant_siaci × 0,245` → `montant_reintegre` |
| `I25` | `=I23-I24` | `pua − pua_percue` → `perte_pua` |

### 2.3 Bloc de période — `p = 21 + 5i`, `i = 0..9`

| Ligne | Contenu |
|---|---|
| `p` (21, 26, … 66) | motif principal `A_p`, dates `B_p`/`C_p`, `D_p`, `E_p` |
| `p+1` | motif d'absence `A_{p+1}`, dates `B_{p+1}`/`C_{p+1}` |
| `p+2` | RETABLI |
| `p+3` | PERÇU |
| `p+4` | PERTE |

**Nombre de jours** — `D21 = IF(B21="",0,(C21-B21+1))`
→ `Periode.nb_jours_ligne_periode()`.

**30ème** — `E21 = IF(D21=0,0,IF(OR($F$2=30,$F$2=D21),D21*30/$F$2,(D21*30/$F$2)+0.0005))`
→ `ml36.trentieme()`. Le `+0,0005` est un correctif d'arrondi historique,
**conservé à l'identique** ; il ne s'applique que si le mois ne compte pas 30 jours
*et* que la période ne couvre pas le mois entier.

**Somme des 30èmes** —
`S = $E$21+$E$26+$E$31+$E$36+$E$41+$E$46+$E$51+$E$56+$E$61+$E$66`
→ `ResultatMatrice.somme_trentiemes`.

**Quotes-parts** (lignes 6 à 15, une par période) :

| Cellule | Formule Excel | Champ |
|---|---|---|
| `I(6+i)` | `=IF($E$15<0,"",$E$15*(E_p/S))` | `quote_majorations` |
| `J(6+i)` | `=IF($E$16<0,"",$E$16*(E_p/S))` | `quote_paniers` |
| `K(6+i)` | `=IF($I$18<0,"",$I$18*(E_p/S))` | `quote_siaci` |
| `F_{p+2}` | `=IF($I$23<0,"",$I$23*(E_p/S))` | `quote_pua` |
| `F_{p+3}` | `=IF($I$24<0,"",$I$24*(E_p/S))` | `quote_pua_percue` |
| `H(75+i)` | `=IFERROR(IF($I$31<0,"",$I$31*(E_p/S)),"")` | `quote_autres_primes` |

**Absence sans solde** —
`O(6+i) = IF(A_{p+1}="Abs sans solde",($B$15*((C_{p+1}-B_{p+1}+1)*30)/$F$2)/30,0)`
→ `absence_sans_solde`. La déduction porte sur les jours de la **ligne d'absence**.

**Rétabli / Perçu / Perte** :

| Cellule | Formule Excel | Champ |
|---|---|---|
| `B_{p+2}` | `=IF(A_p="Abs (Mal, CA, autres)",0,($B$15*$B$8*E_p)/30)` | `retabli_base` |
| `D_{p+2}` | `=IF(A_p="Abs (Mal, CA, autres)",0,B_{p+2}+I(6+i)+J(6+i)+F_{p+2})` | `retabli_total` |
| `B_{p+3}` | `=IF(A_p="Abs (Mal, CA, autres)",0,(($B$15*E_p)/30)*$D$8)` | `percu_base` |
| `D_{p+3}` | `=IF(A_p="Abs (Mal, CA, autres)",0,(B_{p+3}+I(6+i)+J(6+i)+F_{p+3}+K(6+i)))` | `percu_total` |
| `D_{p+4}` | `=D_{p+2}-D_{p+3}` | `perte` |

> Le test `A_p = "Abs (Mal, CA, autres)"` n'est **jamais vrai** : cette valeur
> n'existe dans aucune liste déroulante. Voir `ANOMALIES.md` §9.1 et le
> « mode de compatibilité classeur v6 ».

### 2.4 Totaux

| Cellule | Formule Excel | Champ |
|---|---|---|
| `F4` | `=($B$15*B8)+$E$15+$E$16-O6-…-O15+I23` | `salaire_retabli_3201` |
| `F72` | `=+D25+D30+…+D70` | `perte_cpam` |
| `F74` | `=IF(I18>0,ΣD_{p+3}-$E$16-$I$18,ΣD_{p+3}-$E$16)` | `vivinter_percu` |

### 2.5 Bloc récapitulatif — lignes 75 à 84

| Cellule | Formule Excel | Champ |
|---|---|---|
| `C(75+i)` | `=+IF(B_p>0,B_p,"")` | `date_debut` |
| `E(75+i)` | `=+IF(C_p>0,C_p,"")` | `date_fin` |
| `F(75+i)` | `=+D_{p+3}-K(6+i)-J(6+i)` | `montant_declare` |
| `G(75+i)` | `=F_{p+3}` | `dont_pua_pfa` |
| `H(75+i)` | quote-part `I31` | `autres_primes` |

---

## 3. MATRICE ML37

### 3.1 Entrées

Identiques à ML36 au décalage de ligne près : `B6` = Date AT, `B7` = DJT,
`B9`/`D9` = taux, `B11` = TMF, `B12` = P. TRANSFERT, `B13:B15` lignes libres,
`E11` = REMU CA, `E12` = MAJ NUIT, `E13:E15` lignes libres, `E17` = PANIERS + R226,
`J19` = SIACI, `J23` = PUA, `J24` = PUA perçue, `J30` = AUTRES PRIMES,
`F19` = taux de taxation (0,21).

| Cellule | Formule Excel | Champ |
|---|---|---|
| `B16` | `=SUM(B11:B15)` | `base_salariale` |
| `E16` | `=SUM(E11:E15)` | `total_majorations` |
| `J20` | `=+J19*0.245` | `montant_reintegre` |
| `J25` | `=J23-J24` | `perte_pua` |

### 3.2 Bloc de période — `p = 20 + 5i`

Motifs principaux : `ML37`, `CA`. Motifs d'absence : `MALADIE`, `JEM`,
`Abs sans solde`.

**Deux 30èmes coexistent** :

```
E_p     = IF(D_p=0,0,IF(A_p="CA",  0, <30ème>))     activité ML37
E_{p+1} = IF(D_p=0,0,IF(A_p="ML37",0, <30ème>))     activité hors ML37 (congés)
```

**Quotes-parts** (lignes 5 à 14) :

| Cellule | Formule Excel | Champ |
|---|---|---|
| `J(5+i)` | `=IF(A_p="CA",0,IF($E$16<0,"",$E$16*(E_p/S)))` | `quote_majorations` |
| `K(5+i)` | `=IF($E$17<0,"",$E$17*(E_p/S))` | `quote_paniers` |
| `L(5+i)` | `=IF($J$20<0,"",$J$20*(E_p/S))` | `quote_siaci` |
| `G_{p+2}` | `=IF($J$23<0,"",$J$23*(E_p/S))` | `quote_pua` |
| `G_{p+3}` | `=IF($J$24<0,"",$J$24*(E_p/S))` | `quote_pua_percue` |
| `H(76+i)` | `=IFERROR(IF($J$30<0,"",$J$30*(E_p/S)),"")` | `quote_autres_primes` |

**Absence sans solde** — `P(5+i)`, même forme qu'en ML36 sur base `B16`.

**Rétabli / Perçu / Perte** :

```
B_{p+2} = IF(A_p="MALADIE",0,IF(A_p="ML37",($B$16*$B$9*E_p)/30,($B$16*$B$9*E_{p+1})/30))
D_{p+2} = IF(A_p="MALADIE",0,IF(A_p="ML37",B_{p+2}+J(5+i)+K(5+i)+G_{p+2},0))
B_{p+3} = IF(A_p="MALADIE",0,IF(A_p="ML37",(($B$16*E_p)/30)*$D$9,B_{p+2}))
D_{p+3} = IF(A_p="MALADIE",0,IF(A_p="ML37",(B_{p+3}+J+K+L+G_{p+3}),B_{p+3}))
D_{p+4} = IF(D_{p+2}=0,0,D_{p+2}-D_{p+3})
F_{p+3} = IF($E_p>0,D_{p+3}*$F$19,B_{p+3}*$F$19)
F_{p+4} = IF($E_p>0,D_{p+4}*$F$19,B_{p+4}*$F$19)
```

> Le test `A_p = "MALADIE"` n'est jamais vrai : `MALADIE` appartient à la liste de
> la ligne `A_{p+1}`. Voir `ANOMALIES.md` §9.1.
> `B_{p+4}` (colonne B de la ligne PERTE) est toujours vide dans le classeur :
> la taxation de la perte vaut donc 0 lorsque `E_p = 0`.

### 3.3 Totaux et récapitulatif

| Cellule | Formule Excel | Champ |
|---|---|---|
| `F4` | `=($B$16*B9)+$E$17+$E$16-P5-…-P14+J23` | `salaire_retabli_3201` |
| `F72` | `=D23+D28+…+D68` | `percu_cpam` |
| `F73` | `=+D24+D29+…+D69` | `perte_cpam` |
| `F75` | `=IF(J20>0,ΣD_{p+3}-$E$17-$J$20,ΣD_{p+3}-$E$17)` | `vivinter_percu` |
| `F(76+i)` | `=IF($A_p="CA",0,$D_{p+3}-$K(5+i)-$L(5+i))` | `montant_declare` |
| `G(76+i)` | `=G_{p+3}` | `dont_pua_pfa` |
| `H(76+i)` | quote-part `J30` | `autres_primes` |

---

## 4. MATRICE ML35

Jusqu'à **8 périodes**, lignes 3 à 10 (`I` = date de début, `K` = date de fin,
`L` = nb de jours, `M` = motif). Motifs : `ML35`, `CA`.
Cet onglet **n'alimente pas** l'attestation Vivinter.

| Cellule | Formule Excel | Champ |
|---|---|---|
| `L(3+n)` | `=IF(I>0,K-I+1,"")` | `nb_jours` |
| `F4` | `=SUM(F2:F3)` | `fixe_plus_transfert` |
| `F7` | `=SUM(F4:F6)` | `total_remuneration` |
| `B17` | `=SUMIF(M3:M10,"ML35",L3:L10)` | `jours_ml35` |
| `B14` | `=+C17/B17` | `ij_par_jour` |
| `E17` | `=+C17+D17` | `total_ij` |
| `F17` | `=+E17*F16` | `perte_declaree` |
| `K(14+n)` | `=IF(M_n="ML35",$E$17*L_n/$B$17,0)` | `ij_a_retirer` |
| `L(14+n)` | `=K(14+n)*$F$16` | `ij_taxees` |
| `H(24+n)` | `=IF(L_n=0,0,(($F$4/30)*(E_r/$B$1*30)))` | `fixe` |
| `I(24+n)` | `=IF(F_r="ML35",(($F$5+$F$6)/SUMIF(...))*E_r,0)` | `majo_paniers` |
| `J(24+n)` | `=K(14+n)` | `ij_a_retirer` |
| `K(24+n)` | `=H+I-J` | `a_declarer` |
| `L(24+n)` | `=K(24+n)*$L$23` | `a_declarer_taxe` |

---

## 5. Attestation Vivinter

Le gabarit comporte 7 lignes de période, **lignes 26 à 32**. Ce n'est plus une
limite : le tableau est étendu à l'export au nombre de périodes du dossier
(cf. `export/gabarit.py` et `ANOMALIES.md` §9.2), le PDF restant sur une page.

### 5.1 Sélection de la source, ligne par ligne

Formule d'origine (colonne B, ligne 26) :

```
=IF(ML36!B21<>"",  TEXT(ML36!B21,"jj/mm/aaaa"),
 IF(ML36!B22<>"",  TEXT(ML36!B22,"jj/mm/aaaa"),
 IF(ML37!B20<>"",  TEXT(ML37!B20,"jj/mm/aaaa"),
 IF(ML37!B21<>"",  TEXT(ML37!B21,"jj/mm/aaaa"),""))))
```

→ Pour la ligne *k* : **ML36 si la période *k* de ML36 porte une date de début,
sinon ML37, sinon ligne vide**. La sélection est faite ligne par ligne : une même
attestation peut mélanger des lignes ML36 et ML37 (`attestation.construire()`).

Le test porte sur `B_p` **puis** `B_{p+1}` : c'est la tolérance de saisie du
tableur (§9.4). Dans l'application, une période est un objet unique ; l'import,
lui, lit bien les deux lignes.

### 5.2 Colonne D — Salaires bruts soumis à cotisation

```
IF(OR(ISNUMBER(SEARCH("maladie",A_p)),ISNUMBER(SEARCH("maladie",A_{p+1}))),"Maladie",
IF(OR(A_p="CA",A_{p+1}="CA",SEARCH("jem",…),SEARCH("autres absence",…)),"Congés annuels",
IF(OR(SEARCH("sans solde",…)),"Absence sans solde",
IFERROR(F_r,""))))
```

→ `attestation.libelle_motif()`. **Le motif prime toujours sur le montant**, et
les tests portent sur les **deux** motifs de la période. L'ordre d'évaluation est
celui du classeur et ne doit pas être modifié.

| Motif saisi | ML36 | ML37 | Résultat |
|---|:--:|:--:|---|
| `Maladie` / `MALADIE` | ✓ | ✓ | Maladie |
| `CA / JEM` | ✓ | — | Congés annuels |
| `CA` (motif principal) | — | ✓ | Congés annuels |
| `JEM` | — | ✓ | Congés annuels |
| `Autres absences` | ✓ | — | Congés annuels |
| `Abs sans solde` | ✓ | ✓ | Absence sans solde |
| *(aucun)* | ✓ | ✓ | le montant `F_r` |

### 5.3 Colonnes E/F et G

```
E26 = IF(source ML36, IF(IFERROR(ML36!G75,0)=0,"",ML36!G75), …)
G26 = IF(source ML36, IF(IFERROR(ML36!H75,0)=0,"",ML36!H75), …)
```

→ `Dont PUA / PFA` et `Autres primes` : **vides si le montant vaut 0 €**, jamais
`0,00 €`. Format `#,##0.00 €`.

### 5.4 Colonne H — Taux d'activité partielle

```
=IF(OR(D26="",D26="Congés annuels",D26="Maladie",D26="Absence sans solde"),"",
 IF(source ML36, ML36!$D$8, IF(source ML37, ML37!$D$9,"")))
```

→ Vide dès que la colonne D porte un libellé d'absence ; sinon le taux TPT **de la
matrice qui alimente cette ligne**. Format pourcentage à 2 décimales.

### 5.5 Champs d'identification

| Cellule | Formule Excel | Source |
|---|---|---|
| `D11` | `=IF(ML36!B4<>"",ML36!B4,IF(ML37!B4<>"",ML37!B4,""))` | NOM |
| `D13` | idem sur `B5` | PRÉNOM |
| `D15` | idem sur `B2` | N° SÉCURITÉ SOCIALE |
| `D17` | idem sur `B3` | N° MATRICULE |
| `D19` | *(saisie)* | N° DOSSIER |
| `D21`/`F21`/`H21` | *(libellés)* | QUALIFICATION `PS`/`PNC`/`PNT` |
| `D5`/`H5` | *(libellés)* | RISQUES `INCAPACITE`/`INVALIDITE` |
| `C36` | `ROISSY CDG` | Fait à |
| `C38` | `=NOW()` | Le → date du jour |
| `C44` | `mail.csprh.vivinter@airfrance.fr` | Mail (constante) |

---

## 6. Écarts constatés entre le classeur et la section 5 du cahier des charges

Croisement systématique, comme demandé au §2.2 du cahier des charges.

### 6.1 Le classeur v6.9 fourni est **déjà correct** sur le taux de la colonne H

Le cahier des charges (§5.7) annonce : « Le classeur d'origine prenait
systématiquement le taux de ML36 (pré-rempli à 0,4), ce qui affichait 40 % sur des
dossiers ML37 devant afficher 50 %. »

**Ce n'est pas le cas de la version fournie.** La formule `H26` teste bien la
source ligne par ligne et prend `ML37!$D$9` lorsque la ligne est alimentée par
ML37. Le bug a donc déjà été corrigé en amont, ou concernait une version
antérieure. L'application applique la règle correcte, comme demandé — le résultat
est identique au classeur fourni.

### 6.2 Même remarque pour la clé de sélection de la source

Le cahier des charges (§5.7) demande de ne pas réintroduire « l'ancienne logique
du classeur qui choisissait la source selon que le montant valait 0 ou non ». La
version fournie sélectionne déjà la source sur la **présence d'une date**, ligne
par ligne. Aucune logique fondée sur le montant n'a été trouvée.

### 6.3 `Autres absences` n'existe pas dans la liste ML37

Le cahier des charges (§5.7) fait figurer `Autres absences` comme motif valable en
ML36 **et** ML37. La liste de validation ML37 (`$S$2:$S$4`) ne contient que
`MALADIE`, `JEM` et `Abs sans solde`. Le motif reste néanmoins **reconnu** par la
règle d'attestation (test par sous-chaîne) : un dossier importé qui le contiendrait
serait correctement traduit en « Congés annuels ».

### 6.4 Trois erreurs de recopie dans les formules ML37

| Cellule | Formule du classeur | Devrait être | Effet |
|---|---|---|---|
| `J14` | `=IF(A57="CA",…E65…)` | `A65` | La 10ème période teste le motif de la 8ème |
| `F63`, `F64` | `=+IF($E$55>0,…)` | `$E$60` | Taxation de la 9ème période pilotée par la 8ème |
| `F68`, `F69` | `=+IF($E$55>0,…)` | `$E$65` | Idem pour la 10ème période |

L'application implémente la **règle générale correcte** (chaque période teste son
propre motif et son propre 30ème). Ces trois cellules ne divergent que sur des
dossiers comportant 8 périodes ou plus — c'est-à-dire, en pratique, des dossiers
que l'attestation ne peut de toute façon pas déclarer intégralement (§9.2).

### 6.5 Le ML37 `F4` additionne `E17` *et* `E16`

`F4 = ($B$16*B9)+$E$17+$E$16-P5..P14+J23` additionne les paniers (`E17`) **et** les
majorations (`E16`), là où ML36 additionne `E15` (majorations) et `E16` (paniers).
Les deux régimes sont donc cohérents entre eux malgré des adresses différentes.
Aucune anomalie : la formule est reproduite telle quelle.

### 6.6 Valeur attendue du test 2 (§8) : `171,87 €`

Le cahier des charges annonce une ventilation de PUA perçue de `78,13 €` et
`171,87 €`. Ce couple n'est atteignable **que** pour un mois de **31 jours** :
c'est le correctif `+0,0005` qui déplace le second montant de `171,875` (qui
s'arrondirait à `171,88`) à `171,8695…` (qui s'arrondit à `171,87`). Le test
d'acceptation a donc été écrit avec `nb_jours_mois = 31`, ce qui est cohérent avec
les périodes citées (juillet, du 01/07 au 31/07). Les six valeurs attendues du
test 2 sont reproduites au centime.
