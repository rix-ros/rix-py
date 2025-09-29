import socket
import select
from rix.msg.message import Message
from rix.msg.mediator.Operation import Operation

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
        op.opcode = opcode
        op.len = msg.size()
        buffer = bytearray()
        op.serialize(buffer)
        msg.serialize(buffer)

        try:
          total_sent = 0
          while total_sent < len(buffer):
              sent = self._send(buffer[total_sent:])
              if sent <= 0:
                  return False
              total_sent += sent
          return total_sent == len(buffer)
        except Exception as _:
            return False
    
    def recv_message(self, msg: Message, len: int) -> bool:
        # Read the message body only
        buffer = bytearray(len)
        total_received: int = 0
        try:
            while total_received < len:
                read = self._recv(buffer, total_received)
                if read == -1:
                    return False
                total_received += read
            msg.deserialize(buffer, Message.Offset())
            return True
        except Exception as _:
            return False
        
    def recv_message_with_opcode(self, op: Operation, msg: Message) -> bool:
        # Read the operation header first
       if not self.recv_message(op, op.size()):
           return False
       # Then read the message body
       return self.recv_message(msg, op.len)
