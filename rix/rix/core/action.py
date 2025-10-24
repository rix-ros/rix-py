from typing import Tuple, Callable

from rix.core.common import OPCODE
from rix.core.socket import Socket
from rix.msg.message import Message
from rix.msg.mediator import ActInfo, Status, Operation
from rix.core.spinner import Spinner


class Action(Spinner):
    def __init__(self, info: ActInfo, rixhub_endpoint: Tuple[str, int]):
        self.shutdown_flag = True
        self.registered_flag = False
        self.info = info
        self.server = Socket()
        self.goal_instance = None
        self.feedback_instance = None
        self.result_instance = None
        self.connection = None

        if not self.server.set_reuse_address(True):
            return
        if not self.server.bind((info.endpoint.address, info.endpoint.port)):
            return
        if not self.server.listen(32):
            return

        server_endpoint = self.server.local_endpoint()
        info.endpoint.address = server_endpoint[0]
        info.endpoint.port = server_endpoint[1]

        self.goal_callback = None
        self.preempt_callback = None
        self.callback = None
        self.rixhub_endpoint = rixhub_endpoint

        client = Socket()
        if not client.connect(self.rixhub_endpoint):
            return
        if not client.send_message(OPCODE.ACT_REGISTER, self.info):
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
                client.send_message(OPCODE.ACT_DEREGISTER, self.info)
            self.server.close()

    def ok(self) -> bool:
        return not self.shutdown_flag

    def set_goal_callback(
        self,
        callback: Callable[[], None],
    ) -> None:
        self.goal_callback = callback

    def set_preempt_callback(
        self,
        callback: Callable[[], None],
    ) -> None:
        self.preempt_callback = callback

    def set_callback(
        self,
        TGoal: Callable[[], Message],
        TFeedback: Callable[[], Message],
        TResult: Callable[[], Message],
        callback: Callable[[Message, Message, Message], bool],
    ) -> bool:
        if TGoal().hash() != self.info.goal_hash:
            return False
        if TFeedback().hash() != self.info.feedback_hash:
            return False
        if TResult().hash() != self.info.result_hash:
            return False
        self.callback = callback
        self.goal_instance = TGoal()
        self.feedback_instance = TFeedback()
        self.result_instance = TResult()
        return True

    def shutdown(self) -> None:
        self.shutdown_flag = True

    def spin_once(self) -> None:
        if self.server.is_readable():
            conn, _ = self.server.accept()

            if conn is None:
                return

            if (
                self.callback is None
                or self.goal_instance is None
                or self.feedback_instance is None
                or self.result_instance is None
            ):
                return
            op = Operation()
            if not conn.recv_message(op, op.size()):
                return

            # Reject if we already have a connection
            status = Status()
            if self.connection is not None:
                status.error = -1
                conn.send_message(OPCODE.ACT_RESPONSE_MESSAGE, status)
                conn.close()
                return

            # Reject if opcode is not GOAL
            if op.opcode != OPCODE.ACT_GOAL_MESSAGE:
                status.error = -1
                conn.send_message(OPCODE.ACT_RESPONSE_MESSAGE, status)
                conn.close()
                return

            # Receive goal message
            if not conn.recv_message(self.goal_instance, self.goal_instance.size()):
                status.error = -1
                conn.send_message(OPCODE.ACT_RESPONSE_MESSAGE, status)
                conn.close()
                return

            status.error = 0
            conn.send_message(OPCODE.ACT_RESPONSE_MESSAGE, status)

            self.connection = conn

            if self.goal_callback is not None:
                self.goal_callback()

        if (
            not self.connection
            or not self.callback
            or not self.goal_instance
            or not self.feedback_instance
            or not self.result_instance
        ):
            return

        # Check for cancel or preempt messages from current connection
        if self.connection.is_readable():
            op = Operation()
            if not self.connection.recv_message(op, op.size()):
                return

            if op.opcode == OPCODE.ACT_PREEMPT_MESSAGE:
                if not self.connection.recv_message(
                    self.goal_instance, self.goal_instance.size()
                ):
                    self.connection.close()
                    self.connection = None
                    return

                status = Status()
                status.error = 0
                self.connection.send_message(OPCODE.ACT_RESPONSE_MESSAGE, status)

                if self.preempt_callback is not None:
                    self.preempt_callback()

            elif op.opcode == OPCODE.ACT_CANCEL_MESSAGE:
                self.connection.close()
                self.connection = None
                return

            else:
                # Unknown opcode, close connection
                status = Status()
                status.error = -1
                self.connection.send_message(OPCODE.ACT_RESPONSE_MESSAGE, status)
                self.connection.close()
                self.connection = None
                return

        # Continue processing
        is_result = self.callback(
            self.goal_instance, self.feedback_instance, self.result_instance
        )
        if is_result:
            # Send result message
            self.connection.send_message(
                OPCODE.ACT_RESULT_MESSAGE, self.result_instance
            )
            self.connection.close()
            self.connection = None
            return
        else:
            # Send feedback message
            if not self.connection.send_message(
                OPCODE.ACT_FEEDBACK_MESSAGE, self.feedback_instance
            ):
                self.connection.close()
                self.connection = None
            return
