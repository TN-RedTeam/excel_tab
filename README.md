# Calculateur TPT — Attestation Vivinter

Application Windows native remplaçant le classeur
`CALCULATEUR_TPT_V6_9_attest_Vivinter.xlsx` utilisé par le service RH
d'Air France à Roissy-CDG : calcul des pertes de salaire liées au
**temps partiel thérapeutique** et production de l'**attestation de prévoyance
Vivinter**.

## Documentation

| Document | Contenu |
|---|---|
| [`docs/REGLES_METIER.md`](docs/REGLES_METIER.md) | Traçabilité formule Excel → règle applicative, cellule par cellule |
| [`docs/GUIDE_UTILISATEUR.md`](docs/GUIDE_UTILISATEUR.md) | Mode d'emploi, avec captures d'écran |
| [`docs/ANOMALIES.md`](docs/ANOMALIES.md) | Anomalies du classeur, traitement retenu, décisions en attente |
| [`CHANGELOG.md`](CHANGELOG.md) | Journal des modifications |

## Architecture

```
tpt_app/
├── core/              # moteurs de calcul — ni PySide6 ni openpyxl, testable seul
│   ├── models.py          dataclasses : Salarie, Periode, DossierML35/36/37
│   ├── ml35.py            moteur ML35
│   ├── ml36.py            moteur ML36
│   ├── ml37.py            moteur ML37
│   ├── attestation.py     règles de construction de l'attestation
│   ├── validation.py      contrôles de saisie et messages d'erreur
│   ├── arrondi.py         conversions Decimal et formats français
│   └── moteur.py          orchestration et comparaison des deux modes de calcul
├── export/
│   ├── excel.py           remplissage du template .xlsx
│   ├── pdf.py             attestation PDF
│   ├── rendu.py           moteur de rendu ReportLab piloté par le template
│   ├── template/          attestation_template.xlsx
│   └── assets/            polices de repli, logo, icône
├── ui/                # PySide6
│   ├── main_window.py
│   ├── pages/             un widget par étape
│   ├── widgets/           composants réutilisables
│   └── theme.py           jetons de conception, thèmes clair et sombre
├── db/repository.py   # historique SQLite des dossiers traités
├── importer/          # reprise d'un classeur existant
├── tests/
├── mapping_classeur.py  # source unique des coordonnées de cellules
└── main.py
```

`core/` n'importe **jamais** PySide6 ni openpyxl. Tous les montants circulent en
`Decimal` ; l'arrondi à 2 décimales (`ROUND_HALF_UP`) n'intervient qu'à
l'affichage et à l'export.

## Développement

```bash
python -m pip install -r requirements.txt
python -m pytest tpt_app/tests -q --cov=tpt_app.core   # 96 tests, 98 % de couverture
python -m tpt_app.main                                  # lancer l'application
```

Sur un serveur sans écran, les tests d'interface s'exécutent hors écran :

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tpt_app/tests -q
```

## Packaging Windows

**À exécuter sur un poste Windows** : PyInstaller ne pratique pas la compilation
croisée, un `.exe` ne peut pas être produit depuis Linux ou macOS.

```bat
py -3.12 -m pip install -r requirements.txt
py -3.12 -m PyInstaller CalculateurTPT.spec --noconfirm
```

Produit `dist/CalculateurTPT.exe` (mode `--onefile --windowed`, icône dédiée),
lançable par simple double-clic depuis un partage réseau ou une clé USB, **sans
droits administrateur, sans Microsoft Office et sans accès Internet**.

Le template Excel, les polices de repli et l'icône sont embarqués dans
l'exécutable ; la base `app.db` est créée à côté de celui-ci, ou dans
`%APPDATA%\CalculateurTPT\` si l'emplacement n'est pas inscriptible.

## Licences des ressources embarquées

- **Liberation Sans** (`tpt_app/export/assets/fonts/`) — SIL Open Font License
  1.1, redistribuable. Utilisée comme repli métriquement identique à Arial
  lorsque Arial n'est pas disponible.
- Le logo et le gabarit de l'attestation proviennent du classeur fourni et
  restent la propriété d'Air France / SIACI Saint-Honoré.
