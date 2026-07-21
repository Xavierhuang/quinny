Implement a `VendingMachine` class.

## API

- `VendingMachine(products)` — `products` is a `dict` mapping product name (`str`) to price in cents (`int`). Non-dict `products` → `TypeError`.
- `.balance` — current balance in cents. Starts at 0.
- `.insert_coin(cents)` — add coins to the balance. `cents` must be a non-negative `int` (booleans excluded). Non-int → `TypeError`. Negative → `ValueError`.
- `.select(name) -> int` — attempt to buy `name`:
  - Unknown product → `KeyError`.
  - Balance too low → `RuntimeError`, and the balance is **preserved** (customer can add more coins).
  - Balance sufficient → return **change** (`balance - price`, may be 0). Balance resets to 0.
- `.refund() -> int` — return the current balance and reset to 0. On an empty balance, returns 0.

## Interface

- File: `impl.py`.
- Export exactly one public class: `VendingMachine`.
- Stdlib only.

## Reference cases

```python
PRODUCTS = {"cola": 150, "chips": 100, "candy": 75}
m = VendingMachine(PRODUCTS)
m.balance                    # 0
m.insert_coin(25); m.balance # 25
m.insert_coin(50); m.balance # 75

m2 = VendingMachine(PRODUCTS); m2.insert_coin(100)
m2.select("chips")           # 0        (exact)
m2.balance                   # 0        (reset)

m3 = VendingMachine(PRODUCTS); m3.insert_coin(200)
m3.select("chips")           # 100      (change)

m4 = VendingMachine(PRODUCTS); m4.insert_coin(50)
m4.select("chips")           # RuntimeError (needs 100)
m4.balance                   # 50       (preserved)

m5 = VendingMachine(PRODUCTS); m5.insert_coin(200)
m5.select("gum")             # KeyError

m6 = VendingMachine(PRODUCTS); m6.insert_coin(75)
m6.refund()                  # 75
m6.balance                   # 0

VendingMachine(PRODUCTS).insert_coin(0.25)   # TypeError
VendingMachine(PRODUCTS).insert_coin(-25)    # ValueError
```

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
