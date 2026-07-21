class VendingMachine:
    def __init__(self, products):
        if not isinstance(products, dict):
            raise TypeError("products must be a dict")
        self._products = dict(products)
        self.balance = 0

    def insert_coin(self, cents):
        if isinstance(cents, bool) or not isinstance(cents, int):
            raise TypeError("coin must be an int")
        if cents < 0:
            raise ValueError("coin must be non-negative")
        self.balance += cents

    def select(self, name):
        if name not in self._products:
            raise KeyError(name)
        price = self._products[name]
        if self.balance < price:
            raise RuntimeError(f"insufficient balance for {name}")
        change = self.balance - price
        self.balance = 0
        return change

    def refund(self):
        r = self.balance
        self.balance = 0
        return r
