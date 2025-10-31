from typing import Tuple, Callable

from rix.core.common import OPCODE
from rix.core.socket import Socket
from rix.core.spinner import Spinner
from rix.msg import Message
from rix.sys_msgs import Operation, Status, SubInfo, SubNotify


class Subscriber(Spinner):
    def __init__(self, info: SubInfo, rixhub_endpoint: Tuple[str, int]):
        self.shutdown_flag = True
        self.registered_flag = False
        self.info = info
        self.server = Socket()
        if not self.server.set_reuse_address(True):
            return
        if not self.server.bind((info.endpoint.address, info.endpoint.port)):
            return
        if not self.server.listen(32):
            return

        server_endpoint = self.server.local_endpoint()
        info.endpoint.address = server_endpoint[0]
        info.endpoint.port = server_endpoint[1]

        self.clients: set[Socket] = set()
        self.callback = None
        self.rixhub_endpoint = rixhub_endpoint
        self.message_instance: Message | None = None

        client = Socket()
        if not client.connect(self.rixhub_endpoint):
            return

        if not client.send_message(OPCODE.SUB_REGISTER, self.info):
            return

        op = Operation()
        status = Status()
        if not client.recv_message_with_opcode(op, status):
            return
        if op.opcode != OPCODE.STATUS_RESPONSE:
            return
        if status.error != 0:
            return

        self.shutdown_flag = False
        self.registered_flag = True

    def __del__(self):
        if self.registered_flag:
            client = Socket()
            if client.connect(self.rixhub_endpoint):
                client.send_message(OPCODE.SUB_DEREGISTER, self.info)

    def ok(self) -> bool:
        return not self.shutdown_flag

    def set_callback(
        self, TMsg: Callable[[], Message], callback: Callable[[Message], None]
    ) -> bool:
        if TMsg().hash() != self.info.topic_info.message_hash:
            return False
        self.message_instance = TMsg()
        self.callback = callback
        return True

    def shutdown(self) -> None:
        self.shutdown_flag = True

    def spin_once(self) -> None:
        if self.server.is_readable():
            conn, _ = self.server.accept()
            if conn is None:
                return
            # Receive SubNotify message and connect to publishers
            op = Operation()
            sub_notify = SubNotify()
            if not conn.recv_message_with_opcode(op, sub_notify):
                conn.close()
                return

            if op.opcode != OPCODE.SUB_NOTIFY:
                conn.close()
                return

            for pub in sub_notify.publishers:
                client = Socket()
                client.set_blocking(False)
                client.connect((pub.endpoint.address, pub.endpoint.port))

                self.clients.add(client)

        if self.callback is not None and self.message_instance is not None:
            # Check all clients for incoming messages
            to_remove: list[Socket] = []
            for client in self.clients:
                if client.is_exception():
                    to_remove.append(client)
                    continue

                if client.is_readable():
                    op = Operation()
                    if not client.recv_message_with_opcode(op, self.message_instance):
                        to_remove.append(client)
                        continue

                    if op.opcode != OPCODE.PUB_MESSAGE:
                        to_remove.append(client)
                        continue

                    self.callback(self.message_instance)

            for client in to_remove:
                self.clients.remove(client)
