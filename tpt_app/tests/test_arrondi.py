"""Conversions, arrondis et formats d'affichage français."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from tpt_app.core.arrondi import (
    ZERO,
    arrondi_centime,
    dec,
    format_date,
    format_decimal,
    format_euro,
    format_pourcent,
)


@pytest.mark.parametrize("saisie, attendu", [
    (None, ZERO),
    ("", ZERO),
    ("   ", ZERO),
    (12, Decimal(12)),
    (True, Decimal(1)),
    (Decimal("3.5"), Decimal("3.5")),
    (0.1, Decimal("0.1")),            # pas d'imprécision binaire héritée du float
    ("1 234,56", Decimal("1234.56")),
    ("1 234,56 €", Decimal("1234.56")),
    ("40 %", Decimal(40)),
    ("-12,5", Decimal("-12.5")),
])
def test_conversion_en_decimal(saisie, attendu):
    assert dec(saisie) == attendu


@pytest.mark.parametrize("valeur, attendu", [
    ("0.005", "0.01"),      # les demis vont vers le haut, comme Excel
    ("0.004", "0.00"),
    ("171.875", "171.88"),
    ("-0.005", "-0.01"),
])
def test_arrondi_au_centime(valeur, attendu):
    assert arrondi_centime(Decimal(valeur)) == Decimal(attendu)


@pytest.mark.parametrize("valeur, attendu", [
    (Decimal("0"), "0,00 €"),
    (Decimal("391.666"), "391,67 €"),
    (Decimal("1234.5"), "1 234,50 €"),
    (Decimal("1234567.89"), "1 234 567,89 €"),
    (Decimal("-42"), "-42,00 €"),
    (None, ""),
])
def test_format_euro(valeur, attendu):
    assert format_euro(valeur) == attendu


def test_format_euro_masque_le_zero_sur_demande():
    assert format_euro(ZERO, vide_si_zero=True) == ""
    assert format_euro(Decimal("0.001"), vide_si_zero=True) == ""
    assert format_euro(Decimal("0.01"), vide_si_zero=True) == "0,01 €"


@pytest.mark.parametrize("valeur, attendu", [
    (Decimal("0.4"), "40,00 %"),
    (Decimal("0.5"), "50,00 %"),
    (Decimal("0.805"), "80,50 %"),
    (Decimal(1), "100,00 %"),
    (None, ""),
])
def test_format_pourcent(valeur, attendu):
    assert format_pourcent(valeur) == attendu


def test_format_date_toujours_en_jj_mm_aaaa():
    assert format_date(dt.date(2025, 7, 1)) == "01/07/2025"
    assert format_date(dt.date(2025, 12, 31)) == "31/12/2025"
    assert format_date(None) == ""


def test_format_decimal():
    assert format_decimal(Decimal("10.6456"), 4) == "10,6456"
    assert format_decimal(Decimal("8"), 2) == "8,00"
    assert format_decimal(None) == ""
