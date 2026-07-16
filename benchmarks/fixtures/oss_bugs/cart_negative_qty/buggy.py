"""Buggy: accepts any integer qty. Negative qty becomes a self-credit."""

_items: list[tuple[str, int, float]] = []


def add_item(name: str, qty: int, price: float) -> None:
    # No validation — matches the real-world CVE pattern.
    _items.append((name, qty, price))


def cart_total() -> float:
    return sum(qty * price for _, qty, price in _items)
