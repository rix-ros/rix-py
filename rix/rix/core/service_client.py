from typing import Tuple

from rix.core.common import (
    OPCODE,
)
from rix.core.socket import Socket
from rix.msg.message import Message
from rix.msg.mediator.SrvRequest import SrvRequest
from rix.msg.mediator.SrvResponse import SrvResponse
from rix.msg.mediator.Operation import Operation
from rix.core.spinner import Spinner


class ServiceClient(Spinner):
    def __init__(
        self,
        request: SrvRequest,
        rixhub_endpoint: Tuple[str, int] = ("127.0.0.1", 0),
    ):
        self.shutdown_flag = True
        self.request = request
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

    def spin_once(self) -> None:
        pass
