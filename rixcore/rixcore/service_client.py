import threading
from typing import Tuple

from rixcore.common import (
    OPCODE,
)
from rixcore.socket import Socket
from rixmsg.message import Message
from rixmsg.standard.UInt32 import UInt32
from rixmsg.mediator.SrvRequest import SrvRequest
from rixmsg.mediator.SrvResponse import SrvResponse
from rixmsg.mediator.Operation import Operation


class ServiceClient:
    def __init__(
        self,
        request: SrvRequest,
        rixhub_endpoint: Tuple[str, int] = ("127.0.0.1", 0),
    ):
        self.shutdown_flag = True
        self.request = request
        self.callback_mutex = threading.Lock()
        self.endpoint: Tuple[str, int] = ("", 0)

        client = Socket()
        if not client.connect(rixhub_endpoint):
            return

        if not client.send_message(OPCODE.SRV_REQUEST, self.request):
            return
        
        op = Operation()
        response = SrvResponse()
        if not client.recv_message_with_opcode(op, response):
            return
        
        if op.opcode != OPCODE.SRV_RESPONSE:
            return

        if response.error != 0:
            return

        self.endpoint = (
            response.srv_info.endpoint.address,
            response.srv_info.endpoint.port,
        )
        self.shutdown_flag = False

    def __del__(self):
        self.shutdown()

    def ok(self) -> bool:
        return not self.shutdown_flag

    def shutdown(self) -> None:
        self.shutdown_flag = True

    def call(self, request: Message, response: Message) -> bool:
        client = Socket()
        if not client.connect(self.endpoint):
            return False

        if not client.send_message(OPCODE.SRV_REQUEST_MESSAGE, request):
            return False

        op = Operation()
        if not client.recv_message_with_opcode(op, response):
            return False
        
        if op.opcode != OPCODE.SRV_RESPONSE_MESSAGE:
            return False
        
        return True