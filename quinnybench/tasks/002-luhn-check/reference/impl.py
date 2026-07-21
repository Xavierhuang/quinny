def is_valid_luhn(card_number):
    if not isinstance(card_number, str):
        raise TypeError("card_number must be a string")
    stripped = card_number.replace(" ", "").replace("-", "")
    if len(stripped) < 2 or not stripped.isdigit():
        return False
    total = 0
    reverse = stripped[::-1]
    for i, ch in enumerate(reverse):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0
