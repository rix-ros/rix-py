import socket
import threading
from abc import ABC, abstractmethod

from rixcore.common import PROTOCOL
from rixmsg.mediator.SrvInfo import SrvInfo
from rixmsg.mediator.Operation import Operation
from rixmsg.standard.UInt32 import UInt32


class SrvImplBase(ABC):
    def __init__(
        self,
        id: int,
        nodeID: int,
        service: str,
        reqHash: list,
        resHash: list,
        cb: callable,
        protocol: int,
    ):
        self.info = SrvInfo()
        self.info.id = id
        self.info.node_id = nodeID
        self.info.name = service
        self.info.response_hash.value = resHash
        self.info.request_hash.value = reqHash
        self.info.protocol = protocol
        self.cb = cb
        self.shutdownFlag = False

    def shutdown(self):
        self.shutdownFlag = True
        self._onShutdown()

    def ok(self) -> bool:
        return not self.shutdownFlag

    def getInfo(self) -> SrvInfo:
        ep = self._getEndpoint()
        self.info.endpoint.address = ep[0]
        self.info.endpoint.port = ep[1]
        return self.info

    @abstractmethod
    def _getEndpoint(self) -> tuple[str, int]:
        return ("", 0)

    @abstractmethod
    def _onShutdown(self):
        pass


class SrvImplTCP(SrvImplBase):
    def __init__(
        self,
        id: int,
        nodeID: int,
        service: str,
        reqHash: list,
        resHash: list,
        cb: callable,
    ):
        super().__init__(id, nodeID, service, reqHash, resHash, cb, PROTOCOL["TCP"])
        self.server = socket.create_server(("", 0))
        self.server.settimeout(0.25)
        self.thread = threading.Thread(target=self._run)
        self.thread.start()

    def _getEndpoint(self) -> tuple[str, int]:
        return self.server.getsockname()

    def _onShutdown(self):
        if self.thread.is_alive():
            self.thread.join()

    def _run(self):
        while not self.shutdownFlag:
            try:
                conn, _ = self.server.accept()
                conn.settimeout(None)
                sizeMsg = UInt32()
                reqBuffer = conn.recv(sizeMsg.size())
                sizeMsg.deserialize(reqBuffer, {"offset": 0})
                reqBuffer = conn.recv(sizeMsg.data)
                resBuffer = bytearray()
                resBuffer = self.cb(reqBuffer)
                conn.send(resBuffer)
                conn.close()
            except socket.timeout:
                pass
            except Exception as e:
                print(f"Error in SrvImplTCP: {e}")
        self.server.close()
