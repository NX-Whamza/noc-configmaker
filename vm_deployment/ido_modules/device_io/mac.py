import re
from typing import List

_NON_HEX_RE = re.compile(r"[^0-9A-Fa-f]")


def normalize_mac(value) -> str:
    """
    Normalize common MAC address formats to lower-case colon-separated form.

    Accepts:
    - aa:bb:cc:dd:ee:ff
    - aa-bb-cc-dd-ee-ff
    - aabb.ccdd.eeff
    - aabbccddeeff
    - Excel-style numeric values that lose leading zeros (e.g. 1122334455 -> 00:11:22:33:44:55)

    Returns:
    - "" for None/empty values
    - Best-effort lowercased string (with '-' -> ':') for unparseable values
    """
    if value is None:
        return ""

    # openpyxl can give floats for numeric cells
    if isinstance(value, float) and value.is_integer():
        value = int(value)

    raw = str(value).strip()
    if not raw:
        return ""

    hex_chars = _NON_HEX_RE.sub("", raw)

    # If Excel treated a numeric-only MAC as a number, leading zeros may be lost.
    if len(hex_chars) != 12:
        if hex_chars.isdigit() and len(hex_chars) < 12:
            hex_chars = hex_chars.zfill(12)
        else:
            return raw.lower().replace("-", ":")

    return ":".join(hex_chars[i : i + 2] for i in range(0, 12, 2)).lower()


def mac_query_variants(value) -> List[str]:
    """
    MAC representations sometimes vary between systems. Provide a few common variants
    to try when querying external systems.
    """
    norm = normalize_mac(value)
    if not norm:
        return []
    plain = norm.replace(":", "")
    return [
        norm,
        norm.replace(":", "-"),
        f"{plain[0:4]}.{plain[4:8]}.{plain[8:12]}",
        plain,
    ]

