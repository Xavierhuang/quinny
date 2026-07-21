_TRANSITIONS = {
    ("PENDING",   "pay"):     "PAID",
    ("PENDING",   "cancel"):  "CANCELLED",
    ("PAID",      "ship"):    "SHIPPED",
    ("PAID",      "cancel"):  "CANCELLED",
    ("SHIPPED",   "deliver"): "DELIVERED",
}


class Order:
    def __init__(self):
        self.status = "PENDING"

    def _advance(self, action):
        key = (self.status, action)
        if key not in _TRANSITIONS:
            raise RuntimeError(f"cannot {action} from {self.status}")
        self.status = _TRANSITIONS[key]

    def pay(self):     self._advance("pay")
    def ship(self):    self._advance("ship")
    def deliver(self): self._advance("deliver")
    def cancel(self):  self._advance("cancel")
