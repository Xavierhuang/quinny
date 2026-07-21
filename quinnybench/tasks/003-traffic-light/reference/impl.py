class TrafficLight:
    _CYCLE = ("RED", "GREEN", "YELLOW")

    def __init__(self):
        self._idx = 0

    def current(self):
        return self._CYCLE[self._idx]

    def tick(self):
        self._idx = (self._idx + 1) % len(self._CYCLE)

    def reset(self):
        self._idx = 0
