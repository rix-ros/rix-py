import threading

from rixmsg.standard.UInt32 import UInt32
from rixcore.impl.srv_impl import SrvImplBase


class Service:
    def __init__(self, impl: SrvImplBase):
        self.mutex = threading.Lock()
        self.impl = impl

    def getService(self) -> str:
        if not self.ok():
            return ""
        self.mutex.acquire()
        topic = self.impl.getInfo().name
        self.mutex.release()
        return topic

    def ok(self) -> bool:
        self.mutex.acquire()
        if self.impl is None:
            status = False
        else:
            status = self.impl.ok()
        self.mutex.release()
        return status

    def _shutdown(self) -> None:
        if not self.ok():
            return
        self.mutex.acquire()
        self.impl.shutdown()
        self.mutex.release()
