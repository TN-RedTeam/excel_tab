"""Composants de saisie réutilisables.

Chaque champ affiche son message de validation **sous le champ concerné**, jamais
dans une boîte de dialogue modale. Les champs calculés sont visuellement
distincts (fond grisé, non éditables).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal, InvalidOperation
from typing import Optional

from PySide6.QtCore import QDate, QEvent, QLocale, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...core.arrondi import ZERO, dec, format_decimal, format_euro
from ..theme import UNITE

FORMAT_DATE = "dd/MM/yyyy"
LOCALE_FR = QLocale(QLocale.French, QLocale.France)


class Champ(QWidget):
    """Un libellé, un éditeur et une zone de message sous le champ."""

    modifie = Signal()

    def __init__(self, libelle: str, editeur: QWidget, aide: str = "",
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.libelle = libelle
        self.editeur = editeur

        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(0, 0, 0, 0)
        disposition.setSpacing(UNITE // 2)

        # L'éditeur garde sa largeur naturelle — un sélecteur de date étiré sur
        # toute la ligne serait disgracieux — mais le message, lui, occupe toute
        # la largeur disponible, faute de quoi il se replie et se retrouve tronqué.
        ligne = QHBoxLayout()
        ligne.setContentsMargins(0, 0, 0, 0)
        ligne.setSpacing(0)
        ligne.addWidget(editeur)
        ligne.addStretch(1)
        disposition.addLayout(ligne)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        self.message = QLabel(aide)
        self.message.setWordWrap(True)
        self.message.setProperty("role", "soustitre" if aide else "erreur")
        self.message.setVisible(bool(aide))
        self._aide = aide
        disposition.addWidget(self.message)

    def afficher_anomalie(self, texte: str = "", gravite: str = "erreur") -> None:
        """Affiche un message de contrôle, ou restaure le texte d'aide."""
        if texte:
            self.message.setText(texte)
            self.message.setProperty("role", gravite)
            self.message.setVisible(True)
            self.editeur.setProperty("etat", "erreur" if gravite == "erreur" else "")
        else:
            self.message.setText(self._aide)
            self.message.setProperty("role", "soustitre")
            self.message.setVisible(bool(self._aide))
            self.editeur.setProperty("etat", "")
        for widget in (self.message, self.editeur):
            widget.style().unpolish(widget)
            widget.style().polish(widget)


class SaisieTexte(QLineEdit):
    """Champ texte simple.

    La largeur minimale est dimensionnée pour qu'un nom complet reste lisible
    sans avoir à faire défiler le contenu du champ.
    """

    LARGEUR_MINIMALE = 280

    def __init__(self, gabarit: str = "", parent=None, largeur: int = 0):
        super().__init__(parent)
        if gabarit:
            self.setPlaceholderText(gabarit)
        self.setMinimumWidth(largeur or self.LARGEUR_MINIMALE)


class SaisieMontant(QLineEdit):
    """Champ monétaire : saisie libre en français, affichage formaté hors focus."""

    valeur_modifiee = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignRight)
        self._valeur: Decimal = ZERO
        self.setText("0,00 €")
        self.editingFinished.connect(self._relire)

    def valeur(self) -> Decimal:
        return self._valeur

    def definir_valeur(self, valeur) -> None:
        self._valeur = dec(valeur)
        self.setText(format_euro(self._valeur))

    def _relire(self) -> None:
        try:
            nouvelle = dec(self.text())
        except (InvalidOperation, ValueError, ArithmeticError):
            nouvelle = self._valeur       # saisie invalide : on garde l'ancienne
        self._valeur = nouvelle
        self.setText(format_euro(nouvelle))
        self.valeur_modifiee.emit()

    def focusInEvent(self, evenement):    # noqa: N802 (API Qt)
        super().focusInEvent(evenement)
        self.setText(format_decimal(self._valeur))
        self.selectAll()


class SaisieTaux(QLineEdit):
    """Champ de taux exprimé en pourcentage (``40,00 %`` ↔ ``0,4``)."""

    valeur_modifiee = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignRight)
        self._valeur: Decimal = ZERO
        self.editingFinished.connect(self._relire)

    def valeur(self) -> Decimal:
        return self._valeur

    def definir_valeur(self, valeur) -> None:
        self._valeur = dec(valeur)
        self.setText(f"{format_decimal(self._valeur * 100)} %")

    def _relire(self) -> None:
        try:
            saisie = dec(self.text())
        except (InvalidOperation, ValueError, ArithmeticError):
            saisie = self._valeur * 100
        self._valeur = saisie / 100
        self.setText(f"{format_decimal(self._valeur * 100)} %")
        self.valeur_modifiee.emit()

    def focusInEvent(self, evenement):    # noqa: N802
        super().focusInEvent(evenement)
        self.setText(format_decimal(self._valeur * 100))
        self.selectAll()


class SaisieDate(QDateEdit):
    """Sélecteur de date au format français, calendrier commençant le lundi.

    Un champ vide est représenté par la date minimale, affichée comme une case
    vide. Deux aménagements en découlent :

    * le calendrier s'ouvre sur le **mois et l'année en cours**, et non sur
      janvier 1900 ;
    * taper un chiffre dans un champ vide l'amorce à la date du jour, ce qui
      rend la **saisie entièrement au clavier** possible sans passer par le
      calendrier.
    """

    def __init__(self, parent=None, autorise_vide: bool = True):
        super().__init__(parent)
        self.setDisplayFormat(FORMAT_DATE)
        self.setCalendarPopup(True)
        self.setLocale(LOCALE_FR)
        self.calendarWidget().setFirstDayOfWeek(Qt.Monday)
        self.calendarWidget().setLocale(LOCALE_FR)
        self.setSpecialValueText(" " if autorise_vide else "")
        self.setMinimumDate(QDate(1900, 1, 1))
        self._autorise_vide = autorise_vide
        if autorise_vide:
            self.setDate(self.minimumDate())
        self.calendarWidget().installEventFilter(self)

    @property
    def _vide(self) -> bool:
        return self._autorise_vide and self.date() == self.minimumDate()

    def valeur(self) -> Optional[dt.date]:
        if self._vide:
            return None
        return self.date().toPython()

    def definir_valeur(self, valeur: Optional[dt.date]) -> None:
        if valeur is None:
            self.setDate(self.minimumDate())
        else:
            self.setDate(QDate(valeur.year, valeur.month, valeur.day))

    def eventFilter(self, objet, evenement):      # noqa: N802 (API Qt)
        """Positionne le calendrier sur le mois en cours quand le champ est vide.

        On se contente de tourner la page du calendrier : aucune date n'est
        sélectionnée tant que l'utilisateur n'a pas cliqué, refermer la fenêtre
        laisse donc bien le champ vide.
        """
        if objet is self.calendarWidget() and evenement.type() == QEvent.Show \
                and self._vide:
            aujourdhui = QDate.currentDate()
            self.calendarWidget().setCurrentPage(aujourdhui.year(), aujourdhui.month())
        return super().eventFilter(objet, evenement)

    def keyPressEvent(self, evenement):           # noqa: N802 (API Qt)
        """Amorce un champ vide à la date du jour dès la première frappe."""
        if self._vide and evenement.text()[:1].isdigit():
            self.setDate(QDate.currentDate())
            self.setCurrentSection(QDateEdit.DaySection)
        super().keyPressEvent(evenement)


class SaisieMois(QDateEdit):
    """Sélecteur de mois : la valeur retournée est toujours le 1er du mois."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDisplayFormat("MM/yyyy")
        self.setCalendarPopup(True)
        self.setLocale(LOCALE_FR)
        self.setDate(QDate.currentDate())

    def valeur(self) -> dt.date:
        date = self.date().toPython()
        return dt.date(date.year, date.month, 1)

    def definir_valeur(self, valeur: Optional[dt.date]) -> None:
        if valeur is not None:
            self.setDate(QDate(valeur.year, valeur.month, 1))


class SaisieEntier(QSpinBox):
    def __init__(self, minimum: int, maximum: int, parent=None):
        super().__init__(parent)
        self.setRange(minimum, maximum)
        self.setAlignment(Qt.AlignRight)


class SaisieChoix(QComboBox):
    def __init__(self, options, autorise_vide: bool = False, parent=None):
        super().__init__(parent)
        if autorise_vide:
            self.addItem("", "")
        for option in options:
            self.addItem(option, option)

    def valeur(self) -> str:
        return self.currentData() or ""

    def definir_valeur(self, valeur: str) -> None:
        index = self.findData(valeur or "")
        self.setCurrentIndex(max(index, 0))


class ValeurCalculee(QLineEdit):
    """Résultat en lecture seule, visuellement distinct d'un champ de saisie."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setAlignment(Qt.AlignRight)
        self.setProperty("calcule", "true")
        self.setFocusPolicy(Qt.ClickFocus)
        self.definir_valeur(ZERO)

    def definir_valeur(self, valeur, monetaire: bool = True) -> None:
        self.setText(format_euro(valeur) if monetaire else format_decimal(valeur, 4))


class Formulaire(QFormLayout):
    """Disposition en deux colonnes, alignée sur la grille de 4 px."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setHorizontalSpacing(UNITE * 4)
        self.setVerticalSpacing(UNITE * 2)
        self.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

    def ajouter(self, libelle: str, editeur: QWidget, aide: str = "") -> Champ:
        champ = Champ(libelle, editeur, aide)
        self.addRow(libelle, champ)
        return champ

    def ajouter_intitule_libre(self, gabarit: str, editeur: QWidget,
                               aide: str = "") -> tuple[Champ, QLineEdit]:
        """Ajoute une ligne dont l'**intitulé** est lui-même saisissable.

        Les lignes libres des matrices n'ont pas de libellé imposé par le
        classeur : l'utilisateur nomme lui-même la rubrique, et le nom est reporté
        dans la cellule d'en regard à l'export.
        """
        intitule = QLineEdit()
        intitule.setPlaceholderText(gabarit)
        intitule.setAlignment(Qt.AlignRight)
        intitule.setProperty("intitule", "true")
        # Assez large pour un intitulé métier complet : sans cela le texte est
        # rogné à gauche, l'alignement à droite le faisant sortir du champ.
        intitule.setMinimumWidth(190)
        champ = Champ(gabarit, editeur, aide)
        self.addRow(intitule, champ)
        return champ, intitule

    def definir_ligne_visible(self, champ: Champ, visible: bool) -> None:
        """Masque une ligne entière, libellé compris, sans laisser de trou."""
        ligne, _ = self.getWidgetPosition(champ)
        if ligne >= 0:
            self.setRowVisible(ligne, visible)
