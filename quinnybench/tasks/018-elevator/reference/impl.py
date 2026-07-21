class Elevator:
    def __init__(self, num_floors):
        if isinstance(num_floors, bool) or not isinstance(num_floors, int):
            raise TypeError("num_floors must be an int")
        if num_floors < 2:
            raise ValueError("num_floors must be at least 2")
        self._max = num_floors
        self.current_floor = 1
        self._queue = []

    @property
    def direction(self):
        if not self._queue:
            return "IDLE"
        t = self._queue[0]
        if t > self.current_floor: return "UP"
        if t < self.current_floor: return "DOWN"
        return "IDLE"

    @property
    def pending(self):
        return len(self._queue)

    def request(self, floor):
        if isinstance(floor, bool) or not isinstance(floor, int):
            raise TypeError("floor must be an int")
        if floor < 1 or floor > self._max:
            raise ValueError("floor out of range")
        if floor in self._queue:
            return
        self._queue.append(floor)

    def tick(self):
        if not self._queue:
            return
        target = self._queue[0]
        if self.current_floor < target:
            self.current_floor += 1
        elif self.current_floor > target:
            self.current_floor -= 1
        if self.current_floor == target:
            self._queue.pop(0)
