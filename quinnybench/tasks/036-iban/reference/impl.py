import re

_ALLOWED = re.compile(r"^[A-Z0-9]+$")


def is_valid_iban(s):
    if not isinstance(s, str):
        raise TypeError("s must be a string")
    if not (15 <= len(s) <= 34):
        return False
    if not _ALLOWED.match(s):
        return False
    # Rearrange: move first 4 chars to the end.
    rearranged = s[4:] + s[:4]
    # Convert letters to numbers (A=10 .. Z=35).
    digits = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    return int(digits) % 97 == 1
