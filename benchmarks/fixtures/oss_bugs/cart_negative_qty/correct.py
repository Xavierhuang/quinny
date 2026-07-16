"""Correct: rejects non-positive quantities."""

_items: list[tuple[str, int, float]] = []


def add_item(name: str, qty: int, price: float) -> None:
    if qty <= 0:
        raise ValueError(f"quantity must be positive, got {qty}")
    _items.append((name, qty, price))


def cart_total() -> float:
    return sum(qty * price for _, qty, price in _items)
