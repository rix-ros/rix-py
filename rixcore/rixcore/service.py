import threading
import socket
import select
from typing import Tuple, Callable

from rixcore.common import (
    send_message_with_opcode,
    send_message_with_opcode_no_response,
    OPCODE,
)
from rixmsg.message import Message
from rixmsg.standard.UInt32 import UInt32
from rixmsg.mediator.SrvInfo import SrvInfo
from rixcore.interfaces.spinner import Spinner

class Service(Spinner):
    def __init__(
        self,
        info: SrvInfo,
        server: socket.socket,
        rixhub_endpoint: Tuple[str, int] = ("127.0.0.1", 0),
    ):
        self.shutdown_flag = False
        self.info = info
        self.server = server
        self.callback = None
        self.callback_mutex = threading.Lock()
        self.rixhub_endpoint = rixhub_endpoint

        client = socket.create_connection(self.rixhub_endpoint)
        if not send_message_with_opcode(client, self.info, OPCODE.SRV_REGISTER):
            self.shutdown()

    def __del__(self):
        self.shutdown()
        client = socket.create_connection(self.rixhub_endpoint)
        send_message_with_opcode_no_response(client, self.info, OPCODE.SRV_DEREGISTER)

    def ok(self) -> bool:
        return not self.shutdown_flag

    def set_callback(
        self,
        TRequest: Callable[[], Message],
        TResponse: Callable[[], Message],
        callback: Callable[[Message, Message], None],
    ):
        def callback_serialized(request_buffer: bytearray, response_buffer: bytearray):
            request_msg = TRequest()
            request_msg.deserialize(request_buffer, Message.Offset())
            response_msg = TResponse()
            callback(request_msg, response_msg)
            responseSize = UInt32()
            responseSize.data = response_msg.size()
            responseSize.serialize(response_buffer)
            response_msg.serialize(response_buffer)

        self.callback = callback_serialized

    def shutdown(self) -> None:
        self.shutdown_flag = True

    def spin_once(self) -> None:
        readable, _, _ = select.select([self.server], [], [], 0.0)
        if self.server not in readable:
            return

        conn, _ = self.server.accept()

        with self.callback_mutex:
            try:
                requestLen = UInt32()
                recvSize = requestLen.size()
                requestLenBuffer = bytearray(recvSize)
                bytesRecv = conn.recv_into(requestLenBuffer, recvSize)
                if bytesRecv <= 0:
                    return

                requestLen.deserialize(requestLenBuffer, Message.Offset())
                requestBuffer = bytearray(requestLen.data)
                bytesRecv = 0
                while bytesRecv < requestLen.data:
                    bytesRecv += conn.recv_into(
                        memoryview(requestBuffer)[bytesRecv:],
                        requestLen.data - bytesRecv,
                    )
                if self.callback is not None:
                    responseBuffer = bytearray()
                    self.callback(requestBuffer, responseBuffer)
                    conn.send(responseBuffer)

            except TimeoutError as _:
                return
            except Exception as _:
                return
