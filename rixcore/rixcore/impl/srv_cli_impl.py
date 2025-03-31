import socket
import threading
from abc import ABC, abstractmethod

from rixcore.common import PROTOCOL
from rixmsg.mediator.SrvRequest import SrvRequest
from rixmsg.mediator.Operation import Operation
from rixmsg.standard.UInt32 import UInt32


class SrvCliImplBase(ABC):
    def __init__(
        self,
        id: int,
        nodeID: int,
        service: str,
        reqHash: list,
        resHash: list,
        protocol: int,
    ):
        self.ep = None
        self.request = SrvRequest()
        self.request.id = id
        self.request.node_id = nodeID
        self.request.name = service
        self.request.protocol = protocol
        self.request.request_hash.value = reqHash
        self.request.response_hash.value = resHash
        self.shutdownFlag = False

    @abstractmethod
    def call(self, req: bytearray) -> bytearray | None:
        pass

    def shutdown(self) -> None:
        self.shutdownFlag = True
        self._onShutdown()

    def ok(self) -> bool:
        return not self.shutdownFlag

    def getRequest(self) -> SrvRequest:
        return self.request

    def setEndpoint(self, ep: tuple[str, int]) -> None:
        self.ep = ep


class SrvCliImplTCP(SrvCliImplBase):
    def __init__(
        self,
        id: int,
        nodeID: int,
        service: str,
        reqHash: list,
        resHash: list,
    ):
        super().__init__(id, nodeID, service, reqHash, resHash, PROTOCOL["TCP"])

    def call(self, req: bytearray) -> bytearray | None:
        try:
            sock = socket.create_connection(self.ep)
            sock.send(req)
            sizeMsg = UInt32()
            recvSize = sizeMsg.size()
            buffer = bytearray(recvSize)
            sock.recv_into(buffer, recvSize)
            sizeMsg.deserialize(buffer, {"offset": 0})
            res = sock.recv(sizeMsg.data)
            sock.close()
            return res
        except Exception as e:
            return None

    def _onShutdown(self) -> None:
        pass
