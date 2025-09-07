class SignalManager:
    def __init__(self, signals_to_manage):
        self.signals_to_manage = signals_to_manage

    def __enter__(self):
        for signal, receiver, sender in self.signals_to_manage:
            signal.disconnect(receiver, sender=sender)

    def __exit__(self, exc_type, exc_val, exc_tb):
        for signal, receiver, sender in self.signals_to_manage:
            signal.connect(receiver, sender=sender)
