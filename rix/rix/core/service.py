from typing import Tuple, Callable

from rix.core.common import OPCODE
from rix.core.socket import Socket
from rix.core.spinner import Spinner
from rix.msg import Message
from rix.sys_msgs import SrvInfo, Status, Operation


class Service(Spinner):
    def __init__(self, info: SrvInfo, rixhub_endpoint: Tuple[str, int]):
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
        if not conn.send_message(OPCODE.SRV_RESPONSE_MESSAGE, self.response_instance):
            return

        conn.close()
