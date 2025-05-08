import socket
import threading
from abc import ABC, abstractmethod

from rixcore.common import PROTOCOL
from rixmsg.mediator.PubInfo import PubInfo
from rixmsg.mediator.SubInfo import SubInfo
from rixmsg.mediator.Operation import Operation


class PubImplBase(ABC):
    def __init__(self, id: int, nodeID: int, topic: str, msgHash: list, protocol: int):
        self.shutdownFlag = False
        self.info = PubInfo()
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

    def getInfo(self) -> PubInfo:
        ep = self._getEndpoint()
        self.info.endpoint.address = ep[0]
        self.info.endpoint.port = ep[1]
        return self.info

    @abstractmethod
    def publish(self, msg: bytearray) -> None:
        pass

    @abstractmethod
    def addSubscribers(self, subs: list) -> None:
        pass

    @abstractmethod
    def removeSubscribers(self, subs: list) -> None:
        pass

    @abstractmethod
    def _getEndpoint(self) -> tuple[str, int]:
        return ("", 0)

    @abstractmethod
    def _onShutdown(self):
        pass


class PubImplTCP(PubImplBase):
    def __init__(self, id: int, nodeID: int, topic: str, msgHash: list):
        super().__init__(id, nodeID, topic, msgHash, PROTOCOL["TCP"])
        self.server = socket.create_server(("", 0))
        self.server.settimeout(0.25)
        self.connections = {}
        self.mutex = threading.Lock()
        self.thread = threading.Thread(target=self._run)
        self.thread.start()

    def publish(self, msg: bytearray) -> None:
        self.mutex.acquire()
        for conn in self.connections.values():
            try:
                sent = conn.send(msg)
            except Exception as e:
                continue
        self.mutex.release()

    def addSubscribers(self, subs: list) -> None:
        pass

    def removeSubscribers(self, subs: list) -> None:
        self.mutex.acquire()
        for sub in subs:
            if sub.id in self.connections:
                del self.connections[sub.id]
        self.mutex.release()

    def _getEndpoint(self) -> tuple[str, int]:
        return self.server.getsockname()

    def _onShutdown(self):
        if self.thread.is_alive():
            self.thread.join()

    def _run(self):
        while self.ok():
            try:
                sock, _ = self.server.accept()
            except TimeoutError as e:
                continue
            except Exception as e:
                return

            opMsg = Operation()
            buffer = sock.recv(opMsg.size())
            opMsg.deserialize(buffer, {"offset": 0})
            buffer = sock.recv(opMsg.len)
            subInfo = SubInfo()
            subInfo.deserialize(buffer, {"offset": 0})
            self.mutex.acquire()
            self.connections[subInfo.id] = sock
            self.mutex.release()
