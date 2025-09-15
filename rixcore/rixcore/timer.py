import time
from typing import Callable
from rixcore.interfaces.spinner import Spinner


class Timer(Spinner):
    class Event:
        def __init__(self):
            self.current_real: int = 0
            self.current_expected: int = 0
            self.last_real: int = 0
            self.last_expected: int = 0
            self.last_duration: int = 0

    def __init__(
        self,
        duration: float,
        callback: Callable[[Event], None],
    ):
        self._duration = duration
        self._callback = callback
        self._shutdown_flag = False
        now = time.time_ns()
        self._event = Timer.Event()
        self._event.current_real = now
        self._event.current_expected = 0
        self._event.last_real = 0
        self._event.last_expected = 0
        self._event.last_duration = 0

    def ok(self) -> bool:
        return not self._shutdown_flag

    def shutdown(self) -> None:
        self._shutdown_flag = True

    def set_callback(self, callback: Callable[[Event], None]) -> None:
        self._callback = callback

    def get_callback(self) -> Callable[[Event], None]:
        return self._callback

    def spin_once(self) -> None:
        self._event.current_real = time.time_ns()
        if self._event.current_real - self._event.last_real >= self._duration * 1e9:
            self._event.last_duration = self._event.current_real - self._event.last_real
            if self._event.current_expected == 0:
                self._event.current_expected = self._event.current_real
            else:
                self._event.current_expected += int(self._duration * 1e9)
            self._callback(self._event)
            self._event.last_real = self._event.current_real
            self._event.last_expected = self._event.current_expected