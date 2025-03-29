import threading

from rixmsg.standard.UInt32 import UInt32
from rixcore.impl.pub_impl import PubImplBase


class Publisher:
    def __init__(self, impl: PubImplBase):
        self.mutex = threading.Lock()
        self.impl = impl

    def getTopic(self) -> str:
        if not self.ok():
            return ""
        self.mutex.acquire()
        topic = self.impl.get_info().topic_info.name
        self.mutex.release()
        return topic

    def getNumSubscribers(self) -> int:
        if not self.ok():
            return 0
        self.mutex.acquire()
        num_subs = self.impl.getNumSubscribers()
        self.mutex.release()
        return num_subs

    def ok(self) -> bool:
        self.mutex.acquire()
        if self.impl is None:
            status = False
        else:
            status = self.impl.ok()
        self.mutex.release()
        return status

    def publish(self, msg: any) -> None:
        self.mutex.acquire()
        buffer = bytearray()
        msgLen = UInt32()
        msgLen.data = msg.size()
        msgLen.serialize(buffer)
        msg.serialize(buffer)
        self.impl.publish(buffer)
        self.mutex.release()

    def _shutdown(self) -> None:
        if not self.ok():
            return
        self.mutex.acquire()
        self.impl.shutdown()
        self.mutex.release()

    def _addSubscribers(self, subs: list) -> None:
        self.mutex.acquire()
        self.impl.addSubscribers(subs)
        self.mutex.release()

    def _removeSubscribers(self, subs: list) -> None:
        self.mutex.acquire()
        self.impl.removeSubscribers(subs)
        self.mutex.release()
