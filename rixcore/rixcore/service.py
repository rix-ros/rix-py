import threading
import socket
import select
from typing import Tuple, Callable

from rixcore.common import (
    OPCODE,
)
from rixcore.socket import Socket
from rixmsg.message import Message
from rixmsg.standard.UInt32 import UInt32
from rixmsg.mediator.SrvInfo import SrvInfo
from rixmsg.mediator.Status import Status
from rixmsg.mediator.Operation import Operation
from rixcore.spinner import Spinner


class Service(Spinner):
    def __init__(
        self,
        info: SrvInfo,
        rixhub_endpoint: Tuple[str, int] = ("127.0.0.1", 0),
    ):
        self.shutdown_flag = True
        self.registered_flag = False
        self.info = info
        self.server = Socket()
        self.request_instance = None
        self.response_instance = None

        if not self.server.set_reuse_address(True):
            return
        if not self.server.bind((info.endpoint.address, info.endpoint.port)):
            return
        if not self.server.listen(32):
            return

        server_endpoint = self.server.local_endpoint()
        info.endpoint.address = server_endpoint[0]
        info.endpoint.port = server_endpoint[1]

        self.callback = None
        self.callback_mutex = threading.Lock()
        self.rixhub_endpoint = rixhub_endpoint

        client = Socket()
        if not client.connect(self.rixhub_endpoint):
            return
        if not client.send_message(OPCODE.SRV_REGISTER, self.info):
            return
        op = Operation()
        status = Status()
        if not client.recv_message_with_opcode(op, status):
            return
        if op.opcode != OPCODE.STATUS_RESPONSE:
            return
        if status.error != 0:
            return
        self.registered_flag = True
        self.shutdown_flag = False

    def __del__(self):
        if self.registered_flag:
            client = Socket()
            if client.connect(self.rixhub_endpoint):
                client.send_message(OPCODE.SRV_DEREGISTER, self.info)
            self.server.close()

    def ok(self) -> bool:
        return not self.shutdown_flag

    def set_callback(
        self,
        TRequest: Callable[[], Message],
        TResponse: Callable[[], Message],
        callback: Callable[[Message, Message], None],
    ) -> bool:
        if TRequest().hash() != self.info.request_hash:
            return False
        if TResponse().hash() != self.info.response_hash:
            return False
        self.callback = callback
        self.request_instance = TRequest()
        self.response_instance = TResponse()
        return True

    def shutdown(self) -> None:
        self.shutdown_flag = True

    def spin_once(self) -> None:
        if not self.server.is_readable():
            return

        conn, _ = self.server.accept()

        if conn is None:
            return

        with self.callback_mutex:
            if (
                self.callback is None
                or self.request_instance is None
                or self.response_instance is None
            ):
                return
            op = Operation()
            if not conn.recv_message_with_opcode(op, self.request_instance):
                return

            if op.opcode != OPCODE.SRV_REQUEST_MESSAGE:
                return

            self.callback(self.request_instance, self.response_instance)
            if not conn.send_message(
                OPCODE.SRV_RESPONSE_MESSAGE, self.response_instance
            ):
                return

            conn.close()
