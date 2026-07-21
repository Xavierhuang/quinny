from numbers import Real


def shipping_cost(weight_kg):
    if isinstance(weight_kg, bool) or not isinstance(weight_kg, Real):
        raise TypeError("weight_kg must be a real number")
    if weight_kg < 0:
        raise ValueError("weight_kg must be non-negative")
    if weight_kg <= 1:
        return 5.00
    if weight_kg <= 10:
        return 5.00 + 1.50 * (weight_kg - 1)
    return 20.00 + 2.00 * (weight_kg - 10)
