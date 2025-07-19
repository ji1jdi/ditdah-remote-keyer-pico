from time import ticks_ms, ticks_diff

class Keyer:
    def __init__(self, emitter):
        self._emitter = emitter
        self._keying = False
        self._t0 = ticks_ms()

    def on(self):
        if self._keying:
            return

        if ticks_diff(ticks_ms(), self._t0) <= 10:
            return

        print("on")
        self._keying = True
        self._t0 = ticks_ms()
        self._emitter.emit("on")

    def off(self):
        if not self._keying:
            return

        d = ticks_diff(ticks_ms(), self._t0)
        if d < 20:
            return

        print("off", d)
        self._keying = False
        self._emitter.emit("off")

    @property
    def keying(self):
        return self._keying
