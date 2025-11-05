import socket
from os import readv, writev
import select
from typing import List, Tuple

from rix.msg import Message, Serializable
from rix.sys_msgs import Operation


class Socket:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def bind(self, endpoint: tuple[str, int]) -> bool:
        try:
            self.sock.bind(endpoint)
            return True
        except Exception as _:
            return False

    def listen(self, backlog: int) -> bool:
        try:
            self.sock.listen(backlog)
            return True
        except Exception as _:
            return False

    def accept(self) -> tuple["Socket | None", tuple[str, int]]:
        try:
            client_sock, addr = self.sock.accept()
            client = Socket()
            client.sock = client_sock
            return client, addr
        except Exception as _:
            return None, ("", 0)

    def connect(self, endpoint: tuple[str, int]) -> bool:
        try:
            self.sock.connect(endpoint)
            return True
        except Exception as _:
            return False

    def close(self) -> None:
        try:
            self.sock.close()
        except Exception as _:
            pass

    def wait_readable(self, timeout: float) -> bool:
        try:
            readable, _, _ = select.select([self.sock], [], [], timeout)
            return len(readable) > 0
        except Exception as _:
            return False

    def wait_writable(self, timeout: float) -> bool:
        try:
            _, writable, _ = select.select([], [self.sock], [], timeout)
            return len(writable) > 0
        except Exception as _:
            return False

    def wait_exception(self, timeout: float) -> bool:
        try:
            _, _, exceptional = select.select([], [], [self.sock], timeout)
            return len(exceptional) > 0
        except Exception as _:
            return False

    def set_blocking(self, blocking: bool) -> bool:
        try:
            self.sock.setblocking(blocking)
            return True
        except Exception as _:
            return False

    def get_blocking(self) -> bool:
        try:
            return self.sock.getblocking()
        except Exception as _:
            return False

    def set_reuse_address(self, reuse: bool) -> bool:
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, int(reuse))
            return True
        except Exception as _:
            return False

    def get_reuse_address(self) -> bool:
        try:
            return self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR) != 0
        except Exception as _:
            return False

    def local_endpoint(self) -> tuple[str, int]:
        try:
            return self.sock.getsockname()
        except Exception as _:
            return ("", 0)

    def remote_endpoint(self) -> tuple[str, int]:
        try:
            return self.sock.getpeername()
        except Exception as _:
            return ("", 0)

    def is_writable(self) -> bool:
        return self.wait_writable(0.0)

    def is_readable(self) -> bool:
        return self.wait_readable(0.0)

    def is_exception(self) -> bool:
        return self.wait_exception(0.0)

    def _writev(self, buffers: List[memoryview]) -> int:
        try:
            return writev(self.sock.fileno(), buffers)
        except Exception as _:
            return -1

    def _readv(self, buffers: List[memoryview]) -> int:
        try:
            return readv(self.sock.fileno(), buffers)
        except Exception as _:
            return -1

    def _send(self, buffer: bytes) -> int:
        try:
            return self.sock.send(buffer)
        except Exception as _:
            return -1

    def _recv(self, buffer: bytearray, offset: int) -> int:
        try:
            self.sock.recv_into(buffer, len(buffer) - offset, offset)
            return len(buffer) - offset
        except Exception as _:
            return -1

    def send_message(self, opcode: int, msg: Message) -> bool:
        # Serialize the message
        op = Operation()
        op.opcode = int(opcode)
        op.len = msg.get_prefix_len()
        segments = op.get_segments()

        prefix = memoryview(msg.get_prefix_bytes())
        # Convert prefix bytes into a memoryview
        if len(prefix) > 0:
            segments.append(prefix)

        segments.extend(msg.get_segments())

        # Send all segments using writev
        sent = self._writev(segments)
        return sent > 0

    def recv_message(self, msg: Message, prefix_len: int) -> bool:
        if prefix_len > 0:
            prefix_buffer = bytearray(prefix_len)
            read = self._recv(prefix_buffer, 0)

            offset = Serializable.Offset()
            if not msg.resize(prefix_buffer, read, offset):
                return False

        segments = msg.get_segments()
        read = self._readv(segments)
        return read > 0

    def recv_message_with_opcode(self, op: Operation, msg: Message) -> bool:
        # Read the operation header first
        if not self.recv_message(op, op.get_prefix_len()):
            return False
        # Then read the message body
        return self.recv_message(msg, op.len)

    def ignore_message(self, len: int) -> bool:
        # Read and discard the message body
        buffer = bytearray(len)
        total_received: int = 0
        try:
            while total_received < len:
                read = self._recv(buffer, total_received)
                if read == -1:
                    return False
                total_received += read
            return True
        except Exception as _:
            return False
