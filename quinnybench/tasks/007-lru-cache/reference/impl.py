from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity):
        if isinstance(capacity, bool) or not isinstance(capacity, int):
            raise TypeError("capacity must be an int")
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self._cap = capacity
        self._data = OrderedDict()

    def size(self):
        return len(self._data)

    def get(self, key):
        if key not in self._data:
            raise KeyError(key)
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key, value):
        if key in self._data:
            self._data.move_to_end(key)
            self._data[key] = value
            return
        if len(self._data) >= self._cap:
            self._data.popitem(last=False)   # evict LRU
        self._data[key] = value
