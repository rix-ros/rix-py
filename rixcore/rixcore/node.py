import random
import socket
from typing import Callable, Tuple, TypeVar
from rixmsg.message import Message

from rixcore.common import (
    RIXHUB_PORT,
    send_message_with_opcode,
    send_message_with_opcode_no_response,
    send_message_with_opcode_and_response,
    send_opcode_with_response,
    OPCODE,
)
from rixcore.interfaces.spinner import Spinner
from rixmsg.mediator.NodeInfo import NodeInfo
from rixmsg.mediator.ParamInfo import ParamInfo
from rixmsg.mediator.PubInfo import PubInfo
from rixmsg.mediator.SrvInfo import SrvInfo
from rixmsg.mediator.SrvRequest import SrvRequest
from rixmsg.mediator.SubInfo import SubInfo
from rixmsg.mediator.SystemInfo import SystemInfo
from rixcore.publisher import Publisher
from rixcore.service import Service
from rixcore.service_client import ServiceClient
from rixcore.subscriber import Subscriber
from rixcore.timer import Timer

TMsg = TypeVar("TMsg", bound=Message)
TRequest = TypeVar("TRequest", bound=Message)
TResponse = TypeVar("TResponse", bound=Message)

class Node(Spinner):
    def __init__(
        self,
        name: str, 
        rixhub_endpoint: Tuple[str, int] = ("127.0.0.1", RIXHUB_PORT),
    ):
        self.info = NodeInfo()
        self.info.id = Node.__generateID()
        self.info.machine_id = Node.__getMachineID()
        self.info.name = name
        self.rixhub_endpoint = rixhub_endpoint
        self.shutdown_flag = False
        self.components: set[Spinner] = set()

        client = socket.create_connection(self.rixhub_endpoint)
        if not send_message_with_opcode(client, self.info, OPCODE.NODE_REGISTER):
            self.shutdown()

    def __del__(self):
        self.shutdown()
        client = socket.create_connection(self.rixhub_endpoint)
        send_message_with_opcode_no_response(client, self.info, OPCODE.NODE_DEREGISTER)

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
        endpoint: Tuple[str, int] = ("127.0.0.1", 0),
    ) -> Publisher:
        info = PubInfo()
        info.id = Node.__generateID()
        info.node_id = self.info.id
        info.topic_info.name = topic
        info.topic_info.message_hash = TMsg().hash()

        server = socket.create_server(endpoint)
        server_endpoint = server.getsockname()
        info.endpoint.address = server_endpoint[0]
        info.endpoint.port = server_endpoint[1]

        pub = Publisher(info, server, self.rixhub_endpoint)
        self.components.add(pub)
        return pub

    def create_subscriber(
        self,
        TMsg: Callable[[], Message],
        topic: str,
        callback: Callable[[TMsg], None],
        endpoint: Tuple[str, int] = ("127.0.0.1", 0),
    ) -> Subscriber:
        info = SubInfo()
        info.id = Node.__generateID()
        info.node_id = self.info.id
        info.topic_info.name = topic
        info.topic_info.message_hash = TMsg().hash()

        server = socket.create_server(endpoint)
        server_endpoint = server.getsockname()
        info.endpoint.address = server_endpoint[0]
        info.endpoint.port = server_endpoint[1]

        sub = Subscriber(info, server, self.rixhub_endpoint)
        sub.set_callback(TMsg, callback)
        self.components.add(sub)
        return sub

    def create_service(
        self,
        TRequest: Callable[[], Message],
        TResponse: Callable[[], Message],
        service: str,
        callback: Callable[[TRequest, TResponse], None],
        endpoint: Tuple[str, int] = ("127.0.0.1", 0),
    ) -> Service:
        info = SrvInfo()
        info.id = Node.__generateID()
        info.node_id = self.info.id
        info.name = service
        info.request_hash = TRequest().hash()
        info.response_hash = TResponse().hash()

        server = socket.create_server(endpoint)
        server_endpoint = server.getsockname()
        info.endpoint.address = server_endpoint[0]
        info.endpoint.port = server_endpoint[1]

        srv = Service(info, server, self.rixhub_endpoint)
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
        request.id = Node.__generateID()
        request.name = service
        request.node_id = self.info.id
        request.request_hash = TRequest().hash()
        request.response_hash = TResponse().hash()

        return ServiceClient(request, self.rixhub_endpoint)

    def create_timer(self, duration: float, callback: Callable[[Timer.Event], None]) -> Timer:
        timer = Timer(duration, callback)
        self.components.add(timer)
        return timer

    def set_parameter(self, name: str, parameter: Message) -> bool:
        info = ParamInfo()
        info.name = name
        info.message_hash = parameter.hash()
        info.data = bytearray()
        parameter.serialize(info.data)
        client = socket.create_connection(self.rixhub_endpoint)
        if not send_message_with_opcode(client, info, OPCODE.PARAM_SET_REQUEST):
            return False
        return True

    def get_parameter(self, name: str, parameter: Message) -> bool:
        info = ParamInfo()
        info.name = name
        info.message_hash = parameter.hash()
        info_received = ParamInfo()
        client = socket.create_connection(self.rixhub_endpoint)
        if not send_message_with_opcode_and_response(
            client, info, info_received, OPCODE.PARAM_GET_REQUEST
        ):
            return False
        parameter.deserialize(bytearray(info_received.data), Message.Offset())
        return True

    def get_system_info(self, info: SystemInfo) -> bool:
        client = socket.create_connection(self.rixhub_endpoint)
        return send_opcode_with_response(client, info, OPCODE.SYSTEM_GET_REQUEST)

    @staticmethod
    def __getMachineID() -> int:
        return 0

    @staticmethod
    def __generateID() -> int:
        return random.getrandbits(64)
