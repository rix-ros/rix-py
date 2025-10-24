from typing import Tuple, Callable

from rix.core.common import (
    OPCODE,
)
from rix.core.socket import Socket
from rix.msg.message import Message
from rix.msg.standard import Void
from rix.msg.mediator import ActRequest, ActResponse, Operation, Status
from rix.core.spinner import Spinner


class ActionClient(Spinner):
    def __init__(
        self,
        request: ActRequest,
        rixhub_endpoint: Tuple[str, int] = ("127.0.0.1", 0),
    ):
        self.shutdown_flag = True
        self.request = request
        self.endpoint: Tuple[str, int] = ("", 0)
        self.client = None
        self.result_received = False
        self.feedback_instance = None
        self.result_instance = None
        self.feedback_callback = None
        self.result_callback = None

        client = Socket()
        if not client.connect(rixhub_endpoint):
            return

        if not client.send_message(OPCODE.ACT_REQUEST, self.request):
            return

        op = Operation()
        response = ActResponse()
        if not client.recv_message_with_opcode(op, response):
            return

        if op.opcode != OPCODE.ACT_RESPONSE:
            return

        if response.error != 0:
            return

        self.endpoint = (
            response.act_info.endpoint.address,
            response.act_info.endpoint.port,
        )
        self.shutdown_flag = False

    def __del__(self):
        self.shutdown()

    def ok(self) -> bool:
        return not self.shutdown_flag

    def shutdown(self) -> None:
        self.shutdown_flag = True

    def set_feedback_callback(
        self,
        TFeedback: Callable[[], Message],
        callback: Callable[[Message], None],
    ) -> None:
        self.feedback_instance = TFeedback()
        self.feedback_callback = callback

    def set_result_callback(
        self,
        TResult: Callable[[], Message],
        callback: Callable[[Message], None],
    ) -> None:
        self.result_instance = TResult()
        self.result_callback = callback

    def dispatch(self, goal: Message) -> bool:
        opcode = OPCODE.ACT_PREEMPT_MESSAGE
        if self.client is None:
            opcode = OPCODE.ACT_GOAL_MESSAGE
            self.client = Socket()
            if not self.client.connect(self.endpoint):
                self.client.close()
                self.client = None
                return False

        if not self.client.send_message(opcode, goal):
            self.client.close()
            self.client = None
            return False

        op = Operation()
        # Clear any pending feedback messages
        while True:
            self.client.recv_message(op, op.size())
            if op.opcode == OPCODE.ACT_RESPONSE_MESSAGE:
                break
            self.client.ignore_message(op.len)

        # Receive the response message
        status = Status()
        if not self.client.recv_message(status, op.len):
            self.client.close()
            self.client = None
            return False

        if status.error != 0:
            self.client.close()
            self.client = None
            return False

        self.result_received = False
        return True

    def cancel(self) -> bool:
        if self.client is None:
            return False

        void_msg = Void()
        if not self.client.send_message(OPCODE.ACT_CANCEL_MESSAGE, void_msg):
            self.client.close()
            self.client = None
            return False

        self.client.close()
        self.client = None
        self.result_received = False
        return True

    def spin_once(self) -> None:
        if (
            self.client is None
            or self.feedback_instance is None
            or self.result_instance is None
        ):
            return

        if not self.client.is_readable():
            return

        op = Operation()
        if not self.client.recv_message(op, op.size()):
            self.client.close()
            self.client = None
            return

        if op.opcode == OPCODE.ACT_FEEDBACK_MESSAGE:
            if not self.client.recv_message(self.feedback_instance, op.len):
                self.client.close()
                self.client = None
                return

            if self.feedback_callback is not None:
                self.feedback_callback(self.feedback_instance)

        elif op.opcode == OPCODE.ACT_RESULT_MESSAGE:
            if not self.client.recv_message(self.result_instance, op.len):
                self.client.close()
                self.client = None
                return

            self.result_received = True

            if self.result_callback is not None:
                self.result_callback(self.result_instance)

            self.client.close()
            self.client = None
            return
