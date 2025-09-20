from abc import ABC, abstractmethod

class Spinner(ABC):
    def __init__(self):
        pass

    def spin(self):
        try:
            while self.ok():
                self.spin_once()
        except KeyboardInterrupt as _:
            self.shutdown()

    @abstractmethod
    def spin_once(self):
        pass

    @abstractmethod
    def ok(self) -> bool:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass