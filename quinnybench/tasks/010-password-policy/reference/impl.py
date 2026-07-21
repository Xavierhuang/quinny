_SPECIALS = set("!@#$%^&*()-_+=")


def validate_password(password):
    if not isinstance(password, str):
        raise TypeError("password must be a string")
    failing = []
    if len(password) < 8:
        failing.append("min_length")
    if not any(c.isupper() for c in password):
        failing.append("has_upper")
    if not any(c.islower() for c in password):
        failing.append("has_lower")
    if not any(c.isdigit() for c in password):
        failing.append("has_digit")
    if not any(c in _SPECIALS for c in password):
        failing.append("has_special")
    return failing
