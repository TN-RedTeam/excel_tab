"""Aperçu de l'attestation en temps réel.

Le rendu reprend la mise en page du PDF final : bandeau orange, blocs
d'identification, tableau des 7 périodes bordé, notes de bas de page. Il est
dessiné au QPainter afin de rester instantané à chaque frappe.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ...core.arrondi import format_date, format_euro, format_pourcent
from ...core.models import ResultatAttestation

ORANGE = QColor("#FF6600")
NOIR = QColor("#000000")
BLANC = QColor("#FFFFFF")
GRIS = QColor("#333333")

#: Proportions d'une page A4 portrait.
RATIO_A4 = 297 / 210

#: Hauteur maximale du tableau des périodes, en proportion de la page.
HAUTEUR_TABLEAU_MAX = 0.154

TEXTE_INTRODUCTION = (
    "Nous soussignés Société AIR FRANCE , attestons le salaire perçu pour le(s) "
    "mois cité(s) en référence ci-dessous en activité partielle."
)
NOTE_1 = ("Salaires d'activité partielle (primes incluses) soumis à cotisation "
          "Prévoyance Maladie ;")
NOTE_2 = "A reconstituer en cas d'arrêt de travail sur la période considérée."


class ApercuAttestation(QWidget):
    """Rendu fidèle et instantané de l'attestation."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._attestation: Optional[ResultatAttestation] = None
        self.setMinimumWidth(420)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAutoFillBackground(False)

    def definir_attestation(self, attestation: ResultatAttestation) -> None:
        self._attestation = attestation
        self.update()

    # -- dessin -----------------------------------------------------------

    def paintEvent(self, evenement):      # noqa: N802 (API Qt)
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.Antialiasing)
        peintre.setRenderHint(QPainter.TextAntialiasing)

        # La page conserve les proportions A4 et se centre dans le widget.
        largeur = min(self.width() - 16, (self.height() - 16) / RATIO_A4)
        largeur = max(largeur, 200)
        hauteur = largeur * RATIO_A4
        origine_x = (self.width() - largeur) / 2
        origine_y = 8

        page = QRectF(origine_x, origine_y, largeur, hauteur)
        peintre.fillRect(page, BLANC)
        peintre.setPen(QPen(QColor("#B0B7BF"), 1))
        peintre.drawRect(page)

        if self._attestation is None:
            peintre.end()
            return

        # Toutes les coordonnées ci-dessous sont exprimées en pourcentage de la
        # page, ce qui rend l'aperçu indépendant de la taille du widget.
        self._dessiner(peintre, page)
        peintre.end()

    def _police(self, page: QRectF, taille: float, gras: bool = False) -> QFont:
        police = QFont("Arial")
        police.setPointSizeF(max(taille * page.width() / 595.0, 3.0))
        police.setBold(gras)
        return police

    def _texte(self, peintre, page, x, y, largeur, hauteur, texte, taille,
               gras=False, alignement=Qt.AlignLeft | Qt.AlignVCenter,
               couleur=NOIR, retour=False):
        police = self._police(page, taille, gras)
        cadre = QRectF(page.x() + page.width() * x, page.y() + page.height() * y,
                       page.width() * largeur, page.height() * hauteur)

        # Sans retour à la ligne, un texte plus large que sa case — l'adresse mail
        # dans son cadre étroit, typiquement — est réduit jusqu'à tenir, plutôt
        # que tronqué. Le PDF fait de même.
        if texte and not retour:
            marge = page.width() * 0.006
            largeur_utile = max(cadre.width() - 2 * marge, 1)
            from PySide6.QtGui import QFontMetricsF
            largeur_texte = QFontMetricsF(police).horizontalAdvance(texte)
            if largeur_texte > largeur_utile:
                police.setPointSizeF(police.pointSizeF() * largeur_utile / largeur_texte)

        peintre.setFont(police)
        peintre.setPen(QPen(couleur))
        drapeaux = alignement | (Qt.TextWordWrap if retour else 0)
        peintre.drawText(cadre, int(drapeaux), texte)

    def _dessiner(self, peintre: QPainter, page: QRectF) -> None:
        attestation = self._attestation

        self._texte(peintre, page, 0.06, 0.045, 0.88, 0.035,
                    "ATTESTATION DE TEMPS PARTIEL", 16, True, Qt.AlignCenter)

        self._texte(peintre, page, 0.06, 0.090, 0.20, 0.025, "RISQUES :", 12, True)
        for libelle, position in (("INCAPACITE", 0.30), ("INVALIDITE", 0.62)):
            marque = "(X)" if attestation.risque.startswith(libelle[:5]) else "( )"
            self._texte(peintre, page, position, 0.090, 0.30, 0.025,
                        f"{marque} {libelle}", 12, True)

        self._texte(peintre, page, 0.06, 0.120, 0.88, 0.040, TEXTE_INTRODUCTION,
                    10, True, Qt.AlignLeft | Qt.AlignTop, NOIR, retour=True)

        bandeau = QRectF(page.x() + page.width() * 0.06,
                         page.y() + page.height() * 0.170,
                         page.width() * 0.88, page.height() * 0.026)
        peintre.fillRect(bandeau, ORANGE)
        self._texte(peintre, page, 0.06, 0.170, 0.88, 0.026,
                    "IDENTIFICATION DU SALARIE", 14, True, Qt.AlignCenter, BLANC)

        identification = (
            ("NOM", attestation.nom),
            ("PRENOM", attestation.prenom),
            ("N° SECURITE SOCIALE", attestation.num_secu),
            ("N° MATRICULE", attestation.matricule),
            ("N° DOSSIER", attestation.num_dossier),
        )
        y = 0.212
        for libelle, valeur in identification:
            self._texte(peintre, page, 0.06, y, 0.30, 0.024, libelle, 11, True)
            cadre = QRectF(page.x() + page.width() * 0.36,
                           page.y() + page.height() * y,
                           page.width() * 0.58, page.height() * 0.024)
            peintre.setPen(QPen(NOIR, 0.8))
            peintre.drawRect(cadre)
            self._texte(peintre, page, 0.36, y, 0.58, 0.024, valeur, 11, True,
                        Qt.AlignCenter)
            y += 0.030

        self._texte(peintre, page, 0.06, y, 0.28, 0.024, "QUALIFICATION", 11, True)
        for libelle, position in (("PS", 0.36), ("PNC", 0.56), ("PNT", 0.76)):
            marque = "(X)" if attestation.qualification == libelle else "( )"
            self._texte(peintre, page, position, y, 0.18, 0.024,
                        f"{marque} {libelle}", 11, True, Qt.AlignCenter)

        self._dessiner_tableau(peintre, page, y + 0.040)
        self._dessiner_pied(peintre, page)

    def _lignes_utiles(self) -> list:
        """Les lignes à afficher : celles du gabarit, et davantage si besoin."""
        return self._attestation.lignes[: self._attestation.nb_lignes_utiles]

    def _dessiner_tableau(self, peintre: QPainter, page: QRectF, haut: float) -> None:
        colonnes = (0.06, 0.175, 0.29, 0.50, 0.645, 0.755, 0.94)
        entetes = ("Du", "Au", "Salaires bruts soumis\nà cotisation (1)",
                   "Dont PUA / PFA", "Autres primes", "Taux d'activité\npartielle")
        hauteur_entete = 0.045

        # Le tableau déclare toutes les périodes : au-delà des 7 lignes du
        # gabarit, les lignes se resserrent pour que la page reste unique,
        # exactement comme le PDF produit.
        lignes = self._lignes_utiles()
        hauteur_ligne = min(0.022, HAUTEUR_TABLEAU_MAX / max(len(lignes), 1))

        peintre.setPen(QPen(NOIR, 0.8))
        for index, libelle in enumerate(entetes):
            gauche, droite = colonnes[index], colonnes[index + 1]
            cadre = QRectF(page.x() + page.width() * gauche,
                           page.y() + page.height() * haut,
                           page.width() * (droite - gauche),
                           page.height() * hauteur_entete)
            peintre.drawRect(cadre)
            self._texte(peintre, page, gauche, haut, droite - gauche, hauteur_entete,
                        libelle, 8, True, Qt.AlignCenter, NOIR, retour=True)

        y = haut + hauteur_entete
        for ligne in lignes:
            valeurs = (
                format_date(ligne.date_debut),
                format_date(ligne.date_fin),
                "" if ligne.vide else (ligne.libelle or format_euro(ligne.montant)),
                format_euro(ligne.dont_pua_pfa, vide_si_zero=True),
                format_euro(ligne.autres_primes, vide_si_zero=True),
                format_pourcent(ligne.taux),
            )
            for index, valeur in enumerate(valeurs):
                gauche, droite = colonnes[index], colonnes[index + 1]
                cadre = QRectF(page.x() + page.width() * gauche,
                               page.y() + page.height() * y,
                               page.width() * (droite - gauche),
                               page.height() * hauteur_ligne)
                peintre.setPen(QPen(NOIR, 0.8))
                peintre.drawRect(cadre)
                self._texte(peintre, page, gauche, y, droite - gauche, hauteur_ligne,
                            valeur, 8, True, Qt.AlignCenter)
            y += hauteur_ligne

        self._texte(peintre, page, 0.10, y + 0.010, 0.03, 0.020, "(1)", 8, True,
                    Qt.AlignRight | Qt.AlignVCenter, ORANGE)
        self._texte(peintre, page, 0.14, y + 0.010, 0.80, 0.020, NOTE_1, 8, True)
        self._texte(peintre, page, 0.10, y + 0.030, 0.03, 0.020, "(2)", 8, True,
                    Qt.AlignRight | Qt.AlignVCenter, ORANGE)
        self._texte(peintre, page, 0.14, y + 0.030, 0.80, 0.020, NOTE_2, 8, True)

        self._dessiner_signature(peintre, page, y + 0.060)

    def _dessiner_signature(self, peintre: QPainter, page: QRectF, haut: float) -> None:
        attestation = self._attestation
        lignes = (
            ("Fait à :", attestation.fait_a),
            ("le :", format_date(attestation.fait_le)),
            ("Nom du rédacteur :", attestation.nom_redacteur),
            ("Téléphone :", attestation.telephone),
            ("Mail :", attestation.mail),
        )
        y = haut
        for libelle, valeur in lignes:
            self._texte(peintre, page, 0.06, y, 0.20, 0.022, libelle, 9)
            cadre = QRectF(page.x() + page.width() * 0.26,
                           page.y() + page.height() * y,
                           page.width() * 0.24, page.height() * 0.022)
            peintre.setPen(QPen(NOIR, 0.8))
            peintre.drawRect(cadre)
            self._texte(peintre, page, 0.26, y, 0.24, 0.022, valeur, 8, False,
                        Qt.AlignCenter)
            y += 0.028

        cadre = QRectF(page.x() + page.width() * 0.55,
                       page.y() + page.height() * haut,
                       page.width() * 0.39, page.height() * 0.130)
        peintre.setPen(QPen(NOIR, 0.8))
        peintre.drawRect(cadre)
        self._texte(peintre, page, 0.55, haut, 0.39, 0.024,
                    "Cachet et Signature", 10, True, Qt.AlignCenter)
        # Initiales du rédacteur, reprises du champ « Nom du rédacteur ».
        self._texte(peintre, page, 0.55, haut + 0.024, 0.39, 0.106,
                    attestation.initiales_redacteur, 12, True, Qt.AlignCenter)

    def _dessiner_pied(self, peintre: QPainter, page: QRectF) -> None:
        self._texte(
            peintre, page, 0.06, 0.905, 0.88, 0.045,
            "Les informations recueillies font l'objet de traitements informatiques "
            "destinés à la passation, la promotion, la gestion et l'exécution des "
            "contrats proposés par notre groupe ainsi que le respect de nos "
            "obligations légales.", 6, False, Qt.AlignLeft | Qt.AlignTop, NOIR,
            retour=True)
        self._texte(
            peintre, page, 0.06, 0.955, 0.88, 0.020,
            "A retourner à VIVINTER - Service Prevoyance - 82 rue Villeneuve - "
            "92584 CLICHY Cedex", 7, True, Qt.AlignCenter, GRIS)
        self._texte(
            peintre, page, 0.06, 0.973, 0.88, 0.020,
            "M.L. : SIACI SAINT HONORE - 572 059 939 RCS Paris - "
            "n° ORIAS 07 000 771", 6, True, Qt.AlignCenter, GRIS)
