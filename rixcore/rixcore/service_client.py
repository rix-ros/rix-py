import threading

from rixmsg.standard.UInt32 import UInt32
from rixcore.impl.srv_cli_impl import SrvCliImplBase


class ServiceClient:
    def __init__(self, impl: SrvCliImplBase):
        self.mutex = threading.Lock()
        self.impl = impl

    def getService(self) -> str:
        if not self.ok():
            return ""
        self.mutex.acquire()
        topic = self.impl.getRequest().name
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

    def call(self, req: any, res: any) -> bool:
        reqBuffer = bytearray()
        msgLen = UInt32()
        msgLen.data = req.size()
        msgLen.serialize(reqBuffer)
        req.serialize(reqBuffer)
        resBuffer = bytearray()
        self.mutex.acquire()
        resBuffer = self.impl.call(reqBuffer)
        if resBuffer is None:
            self.mutex.release()
            return False
        self.mutex.release()
        res.deserialize(resBuffer, {"offset": 0})
        return True
