class KeyOut:
    def __init__(self, pin):
        self._pin = pin

    def on(self):
        self._pin.value(1)

    def off(self):
        self._pin.value(0)
