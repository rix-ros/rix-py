import threading
import socket
import select
from typing import Tuple

from rixcore.common import (
    send_message_with_opcode,
    send_message_with_opcode_no_response,
    send_message_with_opcode_and_response,
    OPCODE,
)
from rixmsg.standard.UInt32 import UInt32
from rixmsg.mediator.Operation import Operation
from rixmsg.mediator.SrvRequest import SrvRequest
from rixmsg.mediator.SrvResponse import SrvResponse


class ServiceClient:
    def __init__(
        self,
        request: SrvRequest,
        rixhub_endpoint: Tuple[str, int] = ("127.0.0.1", 0),
    ):
        self.shutdown_flag = False
        self.request = request
        self.callback_mutex = threading.Lock()

        client = socket.create_connection(rixhub_endpoint)
        response = SrvResponse()
        if not send_message_with_opcode_and_response(
            client, self.request, response, OPCODE.SRV_REQUEST
        ):
            self.shutdown()
            return

        if response.error != 0:
            self.shutdown()
            return

        self.endpoint = (
            response.srv_info.endpoint.address,
            response.srv_info.endpoint.port,
        )

    def __del__(self):
        self.shutdown()

    def ok(self) -> bool:
        return not self.shutdown_flag

    def shutdown(self) -> None:
        self.shutdown_flag = True

    def call(self, request: any, response: any) -> bool:
        client = socket.socket()
        try:
            client.connect(self.endpoint)

            requestBuffer = bytearray()
            requestLen = UInt32()
            requestLen.data = request.size()
            requestLen.serialize(requestBuffer)
            request.serialize(requestBuffer)
            client.send(requestBuffer)

            responseLen = UInt32()
            recvSize = responseLen.size()
            responseLenBuffer = bytearray(recvSize)
            bytesRecv = client.recv_into(responseLenBuffer, recvSize)
            if bytesRecv <= 0:
                return

            responseLen.deserialize(responseLenBuffer, {"offset": 0})
            responseBuffer = bytearray(responseLen.data)
            bytesRecv = 0
            while bytesRecv < responseLen.data:
                bytesRecv += client.recv_into(
                    memoryview(responseBuffer)[bytesRecv:],
                    responseLen.data - bytesRecv,
                )
            response.deserialize(responseBuffer, {"offset": 0})
        except Exception as e:
            return False
