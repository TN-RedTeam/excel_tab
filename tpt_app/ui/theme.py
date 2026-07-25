"""Jetons de conception et feuilles de style de l'application.

Palette de neutres froids, un seul accent, espacement sur une grille de 4 px,
rayons de bordure de 4 px. Ni dégradés, ni ombres portées marquées, ni icônes
décoratives : l'outil doit se lire comme un logiciel métier.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Grille d'espacement.
UNITE = 4
RAYON = 4

POLICE_INTERFACE = "Segoe UI Variable"
POLICES_SECOURS = ("Segoe UI", "Inter", "Noto Sans", "DejaVu Sans", "sans-serif")

ACCENT = "#0F6CBD"


@dataclass(frozen=True)
class Palette:
    """Couleurs d'un thème."""

    fond: str
    fond_secondaire: str
    fond_champ: str
    fond_calcule: str
    fond_rail: str
    texte: str
    texte_discret: str
    bordure: str
    accent: str
    accent_texte: str
    accent_survol: str
    erreur: str
    avertissement: str
    succes: str
    selection: str


CLAIR = Palette(
    fond="#FFFFFF",
    fond_secondaire="#F4F6F8",
    fond_champ="#FFFFFF",
    fond_calcule="#EDF0F3",
    fond_rail="#F0F3F6",
    texte="#1A1D21",
    texte_discret="#5B6470",
    bordure="#C9D0D8",
    accent=ACCENT,
    accent_texte="#FFFFFF",
    accent_survol="#0C5AA0",
    erreur="#B3261E",
    avertissement="#8A5A00",
    succes="#1B6E3C",
    selection="#DCE9F6",
)

SOMBRE = Palette(
    fond="#1B1F24",
    fond_secondaire="#22272E",
    fond_champ="#2A3038",
    fond_calcule="#232830",
    fond_rail="#191D22",
    texte="#E6EAF0",
    texte_discret="#9AA5B1",
    bordure="#3A424C",
    accent="#4C9EE8",
    accent_texte="#0E1116",
    accent_survol="#6BB2EF",
    erreur="#F2938C",
    avertissement="#E3B341",
    succes="#7EE2A8",
    selection="#2C3D50",
)


def famille_police() -> str:
    return ", ".join(f'"{nom}"' for nom in (POLICE_INTERFACE, *POLICES_SECOURS))


def feuille_de_style(palette: Palette, taille_police: int = 10) -> str:
    """Construit la feuille de style Qt correspondant à la palette."""
    return f"""
    * {{
        font-family: {famille_police()};
        font-size: {taille_police}pt;
    }}
    QWidget {{
        background-color: {palette.fond};
        color: {palette.texte};
    }}
    QLabel[role="titre"] {{
        font-size: {taille_police + 6}pt;
        font-weight: 600;
    }}
    QLabel[role="soustitre"] {{
        color: {palette.texte_discret};
    }}
    QLabel[role="section"] {{
        font-weight: 600;
        color: {palette.texte_discret};
        padding-top: {UNITE * 2}px;
    }}
    QLabel[role="erreur"] {{ color: {palette.erreur}; }}
    QLabel[role="avertissement"] {{ color: {palette.avertissement}; }}
    QLabel[role="succes"] {{ color: {palette.succes}; }}

    QLineEdit, QDateEdit, QComboBox, QSpinBox, QPlainTextEdit, QTextEdit {{
        background-color: {palette.fond_champ};
        border: 1px solid {palette.bordure};
        border-radius: {RAYON}px;
        padding: {UNITE}px {UNITE + 2}px;
        selection-background-color: {palette.accent};
        selection-color: {palette.accent_texte};
    }}
    QLineEdit:focus, QDateEdit:focus, QComboBox:focus, QSpinBox:focus {{
        border: 1px solid {palette.accent};
    }}
    QLineEdit[etat="erreur"], QDateEdit[etat="erreur"], QComboBox[etat="erreur"] {{
        border: 1px solid {palette.erreur};
    }}
    QLineEdit[calcule="true"], QLineEdit:read-only {{
        background-color: {palette.fond_calcule};
        color: {palette.texte_discret};
    }}
    /* Intitulé de ligne libre : se lit comme un libellé, s'édite comme un champ. */
    QLineEdit[intitule="true"] {{
        background: transparent;
        border: 1px solid transparent;
        color: {palette.texte_discret};
        font-weight: 600;
    }}
    QLineEdit[intitule="true"]:hover {{ border: 1px dashed {palette.bordure}; }}
    QLineEdit[intitule="true"]:focus {{
        background-color: {palette.fond_champ};
        border: 1px solid {palette.accent};
        color: {palette.texte};
    }}

    /* Ni « ::drop-down » ni « ::down-arrow » ne sont redéfinis : styler ces
       sous-contrôles oblige Qt à fournir une image et fait disparaître la
       flèche, ce qui donne à la liste déroulante l'apparence d'un champ en
       lecture seule. Le rendu natif du style de base est conservé. */

    QPushButton {{
        background-color: {palette.fond_secondaire};
        border: 1px solid {palette.bordure};
        border-radius: {RAYON}px;
        padding: {UNITE + 2}px {UNITE * 3}px;
    }}
    QPushButton:hover {{ border-color: {palette.accent}; }}
    QPushButton:disabled {{ color: {palette.texte_discret}; }}
    QPushButton[role="primaire"] {{
        background-color: {palette.accent};
        color: {palette.accent_texte};
        border: 1px solid {palette.accent};
        font-weight: 600;
    }}
    QPushButton[role="primaire"]:hover {{ background-color: {palette.accent_survol}; }}

    QListWidget#rail {{
        background-color: {palette.fond_rail};
        border: none;
        border-right: 1px solid {palette.bordure};
        outline: none;
        padding: {UNITE * 2}px {UNITE}px;
    }}
    QListWidget#rail::item {{
        padding: {UNITE * 2}px {UNITE * 3}px;
        border-radius: {RAYON}px;
        margin: 1px {UNITE}px;
    }}
    QListWidget#rail::item:selected {{
        background-color: {palette.accent};
        color: {palette.accent_texte};
        font-weight: 600;
    }}
    QListWidget#rail::item:hover:!selected {{ background-color: {palette.selection}; }}

    QTableWidget, QTableView {{
        background-color: {palette.fond};
        alternate-background-color: {palette.fond_secondaire};
        gridline-color: {palette.bordure};
        border: 1px solid {palette.bordure};
        border-radius: {RAYON}px;
        selection-background-color: {palette.selection};
        selection-color: {palette.texte};
    }}
    QHeaderView::section {{
        background-color: {palette.fond_secondaire};
        color: {palette.texte_discret};
        border: none;
        border-bottom: 1px solid {palette.bordure};
        border-right: 1px solid {palette.bordure};
        padding: {UNITE + 2}px;
        font-weight: 600;
    }}

    QGroupBox {{
        border: 1px solid {palette.bordure};
        border-radius: {RAYON}px;
        margin-top: {UNITE * 3}px;
        padding: {UNITE * 3}px {UNITE * 2}px {UNITE * 2}px {UNITE * 2}px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: {UNITE * 2}px;
        padding: 0 {UNITE}px;
        color: {palette.texte_discret};
        font-weight: 600;
    }}

    QScrollArea {{ border: none; }}
    QStatusBar {{
        background-color: {palette.fond_secondaire};
        border-top: 1px solid {palette.bordure};
        color: {palette.texte_discret};
    }}
    QStatusBar::item {{ border: none; }}
    QToolBar {{
        background-color: {palette.fond_secondaire};
        border-bottom: 1px solid {palette.bordure};
        spacing: {UNITE * 2}px;
        padding: {UNITE}px {UNITE * 2}px;
    }}
    QFrame[role="separateur"] {{ background-color: {palette.bordure}; }}
    QFrame[role="bandeau"] {{
        background-color: {palette.fond_secondaire};
        border: 1px solid {palette.bordure};
        border-radius: {RAYON}px;
    }}
    """
