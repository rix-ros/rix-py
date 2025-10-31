import random
from typing import Callable, Tuple, TypeVar

from rix.core.common import (
    DEFAULT_IP,
    RIXHUB_IP,
    RIXHUB_PORT,
    OPCODE,
)
from rix.core.action import Action
from rix.core.action_client import ActionClient
from rix.core.publisher import Publisher
from rix.core.service import Service
from rix.core.service_client import ServiceClient
from rix.core.spinner import Spinner
from rix.core.subscriber import Subscriber
from rix.core.timer_callback import TimerCallback
from rix.core.socket import Socket
from rix.msg import Message
from rix.sys_msgs import (
    NodeInfo,
    ParamInfo,
    PubInfo,
    SrvInfo,
    SrvRequest,
    ActInfo,
    ActRequest,
    SubInfo,
    SystemInfo,
    Operation,
    Status,
)
from rix.std_msgs import UInt64

TMsg = TypeVar("TMsg", bound=Message)
TRequest = TypeVar("TRequest", bound=Message)
TResponse = TypeVar("TResponse", bound=Message)
TGoal = TypeVar("TGoal", bound=Message)
TFeedback = TypeVar("TFeedback", bound=Message)
TResult = TypeVar("TResult", bound=Message)


class Node(Spinner):
    def __init__(self, name: str, endpoint: Tuple[str, int] = (DEFAULT_IP, 0)):
        self.info = NodeInfo()
        self.info.id = Node.__generate_id()
        self.info.name = name
        self.rixhub_endpoint = (RIXHUB_IP, RIXHUB_PORT)
        self.shutdown_flag = True
        self.registered_flag = False
        self.components: set[Spinner] = set()

        self.server = Socket()

        if not self.server.set_reuse_address(True):
            return
        if not self.server.bind((endpoint[0], endpoint[1])):
            return
        if not self.server.listen(32):
            return

        server_endpoint = self.server.local_endpoint()
        self.info.endpoint.address = server_endpoint[0]
        self.info.endpoint.port = server_endpoint[1]

        client = Socket()
        if not client.connect(self.rixhub_endpoint):
            return
        if not client.send_message(OPCODE.NODE_REGISTER, self.info):
            return

        op = Operation()
        status = Status()
        if not client.recv_message_with_opcode(op, status):
            return
        if op.opcode != OPCODE.STATUS_RESPONSE:
            return
        if status.error != 0:
            return

        def handle_accept(event: TimerCallback.Event) -> None:
            if not self.server.is_readable():
                return

            conn, _ = self.server.accept()
            if conn is None:
                return

            op = Operation()
            if not conn.recv_message(op, op.get_prefix_len()):
                return

            if op.opcode == OPCODE.PING:
                status = Status()
                status.error = 0
                status.id = self.info.id
                conn.send_message(OPCODE.STATUS_RESPONSE, status)

        self.create_timer(0.5, handle_accept)

        self.registered_flag = True
        self.shutdown_flag = False

    def __del__(self):
        if self.registered_flag:
            client = Socket()
            if client.connect(self.rixhub_endpoint):
                client.send_message(OPCODE.NODE_DEREGISTER, self.info)

    def spin_once(self) -> None:
        remove_list: list[Spinner] = []
        for component in self.components:
            if not component.ok():
                remove_list.append(component)
                continue
            component.spin_once()
        for component in remove_list:
            self.components.remove(component)

    def shutdown(
        self,
    ) -> None:
        self.shutdown_flag = True

    def ok(
        self,
    ) -> bool:
        return not self.shutdown_flag

    def create_publisher(
        self,
        TMsg: Callable[[], Message],
        topic: str,
        endpoint: Tuple[str, int] = (DEFAULT_IP, 0),
    ) -> Publisher:
        info = PubInfo()
        info.id = Node.__generate_id()
        info.node_id = self.info.id
        info.topic_info.name = topic
        info.topic_info.message_hash = TMsg().hash()
        info.endpoint.address = endpoint[0]
        info.endpoint.port = endpoint[1]

        pub = Publisher(info, self.rixhub_endpoint)
        self.components.add(pub)
        return pub

    def create_subscriber(
        self,
        TMsg: Callable[[], Message],
        topic: str,
        callback: Callable[[TMsg], None],
        endpoint: Tuple[str, int] = (DEFAULT_IP, 0),
    ) -> Subscriber:
        info = SubInfo()
        info.id = Node.__generate_id()
        info.node_id = self.info.id
        info.topic_info.name = topic
        info.topic_info.message_hash = TMsg().hash()
        info.endpoint.address = endpoint[0]
        info.endpoint.port = endpoint[1]

        sub = Subscriber(info, self.rixhub_endpoint)
        sub.set_callback(TMsg, callback)
        self.components.add(sub)
        return sub

    def create_service(
        self,
        TRequest: Callable[[], Message],
        TResponse: Callable[[], Message],
        service: str,
        callback: Callable[[TRequest, TResponse], None],
        endpoint: Tuple[str, int] = (DEFAULT_IP, 0),
    ) -> Service:
        info = SrvInfo()
        info.id = Node.__generate_id()
        info.node_id = self.info.id
        info.name = service
        info.request_hash = TRequest().hash()
        info.response_hash = TResponse().hash()
        info.endpoint.address = endpoint[0]
        info.endpoint.port = endpoint[1]

        srv = Service(info, self.rixhub_endpoint)
        srv.set_callback(TRequest, TResponse, callback)
        self.components.add(srv)
        return srv

    def create_service_client(
        self,
        TRequest: Callable[[], Message],
        TResponse: Callable[[], Message],
        service: str,
    ) -> ServiceClient:
        request = SrvRequest()
        request.name = service
        request.node_id = self.info.id
        request.request_hash = TRequest().hash()
        request.response_hash = TResponse().hash()

        srvcli = ServiceClient(request, self.rixhub_endpoint)
        self.components.add(srvcli)
        return srvcli

    def create_timer(
        self, duration: float, callback: Callable[[TimerCallback.Event], None]
    ) -> TimerCallback:
        timer = TimerCallback(duration, callback)
        self.components.add(timer)
        return timer

    def create_action(
        self,
        TGoal: Callable[[], Message],
        TFeedback: Callable[[], Message],
        TResult: Callable[[], Message],
        action: str,
        callback: Callable[[TGoal, TFeedback, TResult], bool],
        endpoint: Tuple[str, int] = (DEFAULT_IP, 0),
    ) -> Action:
        info = ActInfo()
        info.id = Node.__generate_id()
        info.node_id = self.info.id
        info.name = action
        info.goal_hash = TGoal().hash()
        info.feedback_hash = TFeedback().hash()
        info.result_hash = TResult().hash()
        info.endpoint.address = endpoint[0]
        info.endpoint.port = endpoint[1]

        act = Action(info, self.rixhub_endpoint)
        act.set_callback(TGoal, TFeedback, TResult, callback)
        self.components.add(act)
        return act

    def create_action_client(
        self,
        TGoal: Callable[[], Message],
        TFeedback: Callable[[], Message],
        TResult: Callable[[], Message],
        action: str,
    ) -> ActionClient:
        request = ActRequest()
        request.name = action
        request.node_id = self.info.id
        request.goal_hash = TGoal().hash()
        request.feedback_hash = TFeedback().hash()
        request.result_hash = TResult().hash()

        actcli = ActionClient(request, self.rixhub_endpoint)
        self.components.add(actcli)
        return actcli

    def set_parameter(self, name: str, parameter: Message) -> bool:
        info = ParamInfo()
        info.id = self.info.id
        info.name = name
        info.message_hash = parameter.hash()
        info.data = bytearray()
        parameter.serialize(info.data)
        client = Socket()
        if not client.connect(self.rixhub_endpoint):
            return False
        if not client.send_message(OPCODE.PARAM_SET_REQUEST, info):
            return False

        op = Operation()
        status = Status()
        if not client.recv_message_with_opcode(op, status):
            return False

        if op.opcode != OPCODE.STATUS_RESPONSE:
            return False

        if status.error != 0:
            return False

        return True

    def get_parameter(self, name: str, parameter: Message) -> bool:
        info = ParamInfo()
        info.id = self.info.id
        info.name = name
        info.message_hash = parameter.hash()

        client = Socket()
        if not client.connect(self.rixhub_endpoint):
            return False

        if not client.send_message(OPCODE.PARAM_GET_REQUEST, info):
            return False

        info_received = ParamInfo()
        op = Operation()
        if not client.recv_message_with_opcode(op, info_received):
            return False

        if op.opcode != OPCODE.PARAM_GET_RESPONSE:
            return False

        parameter.deserialize(bytearray(info_received.data), Message.Offset())
        return True

    def get_system_info(self, info: SystemInfo) -> bool:
        client = Socket()
        if not client.connect(self.rixhub_endpoint):
            return False

        node_id = UInt64()
        node_id.data = self.info.id
        if not client.send_message(OPCODE.SYSTEM_GET_REQUEST, node_id):
            return False

        op = Operation()
        if not client.recv_message_with_opcode(op, info):
            return False

        if op.opcode != OPCODE.SYSTEM_GET_RESPONSE:
            return False

        return True

    @staticmethod
    def __generate_id() -> int:
        return random.getrandbits(64)
