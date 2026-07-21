import re

_E164 = re.compile(r"^\+[1-9][0-9]{0,14}$")


def is_valid_e164(s):
    if not isinstance(s, str):
        raise TypeError("s must be a string")
    return bool(_E164.match(s))
