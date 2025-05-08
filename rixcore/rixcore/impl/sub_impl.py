import socket
import threading
from abc import ABC, abstractmethod

from rixcore.common import PROTOCOL
from rixmsg.mediator.SubInfo import SubInfo
from rixmsg.mediator.Operation import Operation
from rixmsg.standard.UInt32 import UInt32


class SubImplBase(ABC):
    def __init__(
        self,
        id: int,
        nodeID: int,
        topic: str,
        msgHash: list,
        cb: callable,
        protocol: int,
    ):
        self.cb = cb
        self.shutdownFlag = False
        self.info = SubInfo()
        self.info.id = id
        self.info.node_id = nodeID
        self.info.topic_info.name = topic
        self.info.topic_info.message_hash = msgHash
        self.info.protocol = protocol

    def shutdown(self):
        self.shutdownFlag = True
        self._onShutdown()

    def ok(self) -> bool:
        return not self.shutdownFlag

    def getInfo(self) -> SubInfo:
        ep = self._getEndpoint()
        self.info.endpoint.address = ep[0]
        self.info.endpoint.port = ep[1]
        return self.info

    @abstractmethod
    def addPublishers(self, pubs: list) -> None:
        pass

    @abstractmethod
    def removePublishers(self, pubs: list) -> None:
        pass

    @abstractmethod
    def _getEndpoint(self) -> tuple[str, int]:
        return ("", 0)

    @abstractmethod
    def _onShutdown(self):
        pass


class SubImplTCP(SubImplBase):
    def __init__(self, id: int, nodeID: int, topic: str, msgHash: list, cb: callable):
        super().__init__(id, nodeID, topic, msgHash, cb, PROTOCOL["TCP"])
        self.threads = {}
        self.mutex = threading.Lock()

    def addPublishers(self, pubs: list) -> None:
        infoBuffer = bytearray()
        opMsg = Operation()
        opMsg.len = self.info.size()
        opMsg.serialize(infoBuffer)
        self.info.serialize(infoBuffer)

        for pub in pubs:
            try:
                sock = socket.create_connection(
                    (pub.endpoint.address, pub.endpoint.port)
                )
                sent = sock.send(infoBuffer)
                sock.settimeout(0.25)
                thread = threading.Thread(target=self._run, args=[sock])
                thread.start()
                self.threads[pub.id] = thread
            except Exception as e:
                continue

    def removePublishers(self, pubs: list) -> None:
        self.mutex.acquire()
        for pub in pubs:
            if pub.id in self.threads:
                del self.threads[pub.id]
        self.mutex.release()

    def _getEndpoint(self) -> tuple[str, int]:
        return ("", 0)

    def _onShutdown(self):
        self.mutex.acquire()
        for thread in self.threads.values():
            if thread.is_alive():
                thread.join()
        self.threads.clear()
        self.mutex.release()

    def _run(self, sock):
        while self.ok():
            try:
                msgLen = UInt32()
                recvSize = msgLen.size()
                msgLenBuffer = bytearray(recvSize)
                sock.recv_into(msgLenBuffer, recvSize)
                msgLen.deserialize(msgLenBuffer, {"offset": 0})
                msgBuffer = bytearray(msgLen.data)
                bytesRecv = 0
                while bytesRecv < msgLen.data:
                    bytesRecv += sock.recv_into(
                        memoryview(msgBuffer)[bytesRecv:], msgLen.data - bytesRecv
                    )
                self.cb(msgBuffer)
            except TimeoutError as e:
                continue
            except Exception as e:
                break
        sock.close()
