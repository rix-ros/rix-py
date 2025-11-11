from typing import Tuple

from rix.core.common import OPCODE
from rix.core.socket import Socket
from rix.core.spinner import Spinner
from rix.msg import Message
from rix.sys_msgs import PubInfo, Status, Operation


class Publisher(Spinner):
    def __init__(
        self,
        info: PubInfo,
        rixhub_endpoint: Tuple[str, int],
    ):
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

        self.connections: set[Socket] = set()
        self.rixhub_endpoint = rixhub_endpoint

        client = Socket()
        if not client.connect(self.rixhub_endpoint):
            return

        if not client.send_message(OPCODE.PUB_REGISTER, self.info):
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
                client.send_message(OPCODE.PUB_DEREGISTER, self.info)

    def ok(self) -> bool:
        return not self.shutdown_flag

    def publish(self, msg: Message) -> None:
        if msg.hash() != self.info.topic_info.message_hash:
            print("Warning: Message type mismatch in publish!")
            return

        to_remove: list[Socket] = []
        for conn in self.connections:
            if not conn.send_message(OPCODE.PUB_MESSAGE, msg):
                to_remove.append(conn)

        for conn in to_remove:
            self.connections.remove(conn)

    def shutdown(self) -> None:
        self.shutdown_flag = True

    def spin_once(self) -> None:
        if not self.server.is_readable():
            return
        conn, _ = self.server.accept()
        if conn is None:
            return
        self.connections.add(conn)
