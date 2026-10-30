"""Structural validators for synthetic Mexican identifiers.

These checks accept the published shape of an RFC, CURP, email, or Mexican
phone number, including a real calendar date inside RFC and CURP. They do not
call SAT or RENAPO and they do not verify official checksums.
"""

from __future__ import annotations

import re
from datetime import datetime

RFC_FISICA_RE = re.compile(r"^[A-ZÑ&]{4}\d{6}[A-Z0-9]{3}$")
RFC_MORAL_RE = re.compile(r"^[A-ZÑ&]{3}\d{6}[A-Z0-9]{3}$")
CURP_RE = re.compile(
    r"^[A-Z][AEIOUX][A-Z]{2}\d{6}[HM]"
    r"(AS|BC|BS|CC|CL|CM|CS|CH|DF|DG|GT|GR|HG|JC|MC|MN|MS|NT|NL|OC|PL|QT|QR|SP|SL|SR|TC|TS|TL|VZ|YN|ZS|NE)"
    r"[B-DF-HJ-NP-TV-Z]{3}[A-Z0-9]\d$"
)
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
PHONE_MX_RE = re.compile(r"^\+52[2-9]\d{9}$")

CURP_STATES = (
    "AS",
    "BC",
    "BS",
    "CC",
    "CL",
    "CM",
    "CS",
    "CH",
    "DF",
    "DG",
    "GT",
    "GR",
    "HG",
    "JC",
    "MC",
    "MN",
    "MS",
    "NT",
    "NL",
    "OC",
    "PL",
    "QT",
    "QR",
    "SP",
    "SL",
    "SR",
    "TC",
    "TS",
    "TL",
    "VZ",
    "YN",
    "ZS",
    "NE",
)


def _yyMMdd_is_real(value: str) -> bool:
    if len(value) != 6 or not value.isdigit():
        return False
    try:
        datetime.strptime(value, "%y%m%d")
    except ValueError:
        return False
    return True


def valid_rfc(value: str | None, *, kind: str = "any") -> bool:
    if value is None:
        return False
    text = value.strip().upper()
    if kind == "fisica":
        matched = RFC_FISICA_RE.match(text)
        date_at = 4
    elif kind == "moral":
        matched = RFC_MORAL_RE.match(text)
        date_at = 3
    elif kind == "any":
        if RFC_FISICA_RE.match(text):
            matched = True
            date_at = 4
        elif RFC_MORAL_RE.match(text):
            matched = True
            date_at = 3
        else:
            return False
    else:
        raise ValueError(f"Unknown RFC kind: {kind}")
    if not matched:
        return False
    return _yyMMdd_is_real(text[date_at : date_at + 6])


def valid_rfc_fisica(value: str | None) -> bool:
    return valid_rfc(value, kind="fisica")


def valid_rfc_moral(value: str | None) -> bool:
    return valid_rfc(value, kind="moral")


def valid_curp(value: str | None) -> bool:
    if value is None:
        return False
    text = value.strip().upper()
    if not CURP_RE.match(text):
        return False
    return _yyMMdd_is_real(text[4:10])


def valid_email(value: str | None) -> bool:
    if value is None:
        return False
    return EMAIL_RE.match(value.strip()) is not None


def valid_phone_mx(value: str | None) -> bool:
    if value is None:
        return False
    return PHONE_MX_RE.match(value.strip()) is not None


FORMAT_FUNCTIONS = {
    "rfc_fisica": valid_rfc_fisica,
    "rfc_moral": valid_rfc_moral,
    "curp": valid_curp,
    "email": valid_email,
    "phone_mx": valid_phone_mx,
}
