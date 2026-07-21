_TRANSITIONS = {
    ("CLOSED",      "open"):    "SYN_SENT",
    ("SYN_SENT",    "syn_ack"): "ESTABLISHED",
    ("ESTABLISHED", "close"):   "CLOSED",
}


class TCPConnection:
    def __init__(self):
        self.state = "CLOSED"

    def _advance(self, action):
        key = (self.state, action)
        if key not in _TRANSITIONS:
            raise RuntimeError(f"cannot {action} from {self.state}")
        self.state = _TRANSITIONS[key]

    def open(self):    self._advance("open")
    def syn_ack(self): self._advance("syn_ack")
    def close(self):   self._advance("close")
