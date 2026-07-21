import re

_LOCAL = re.compile(r"^[A-Za-z0-9_%+\-]+(?:\.[A-Za-z0-9_%+\-]+)*$")
_LABEL = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$")
_TLD   = re.compile(r"^[A-Za-z]{2,}$")


def is_valid_email(s):
    if not isinstance(s, str):
        raise TypeError("s must be a string")
    if s.count("@") != 1:
        return False
    local, _, domain = s.partition("@")
    if not local or not domain:
        return False
    if not _LOCAL.match(local):
        return False
    labels = domain.split(".")
    if len(labels) < 2:
        return False
    for label in labels[:-1]:
        if not label or not _LABEL.match(label):
            return False
    if not _TLD.match(labels[-1]):
        return False
    return True
