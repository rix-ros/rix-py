import socket
import logging
import random
from abc import ABC, abstractmethod
import errno

from rixcore.common import Protocol, get_public_ip, recv_all_bytes, send_all_bytes
from rixmsg.component.ComponentInfo import ComponentInfo
from rixmsg.component.ID import ID
from rixmsg.component.URI import URI

class Subscriber(ABC):
    def __init__(self, topic: str, callback: callable, node_id: int, protocol: int, TMsg: any):
        self.callback = callback
        self.add_pub_set = []
        self.remove_pub_set = []
        self.TMsg = TMsg

        self.component_info = ComponentInfo()
        self.component_info.topic = topic.encode()
        self.component_info.protocol = protocol
        self.component_info.node_id = node_id
        self.component_info.component_id = random.getrandbits(64)
        self.component_info.message_info[0] = TMsg.info()

        self.num_pubs = 0
        self._shutdown_flag = False

    def get_num_publishers(self) -> int:
        return self.num_pubs

    def shutdown(self):
        self._shutdown_flag = True

    def _add_publisher(self, pub_id: ID) -> None:
        self.add_pub_set.append(pub_id)
    
    def _remove_publisher(self, pub_id: ID) -> None:
        self.remove_pub_set.append(pub_id)

    def _run_once(self) -> None:
        if len(self.add_pub_set) > 0:
            self._connect_publishers(self.add_pub_set)
        if len(self.remove_pub_set) > 0:
            self._remove_publishers(self.remove_pub_set)
        self._handle_msg()

    @abstractmethod
    def _connect_publishers(self, pub_id: set[ID]) -> None:
        pass

    @abstractmethod
    def _remove_publishers(self, pub_id: set[ID]) -> None:
        pass

    @abstractmethod
    def _handle_msg(self) -> None:
        pass

    @abstractmethod
    def _get_id(self) -> ID:
        pass

class SubscriberTCP(Subscriber):
    def __init__(self, topic: str, callback: callable, node_id: int, TMsg: any):
        super().__init__(topic, callback, node_id, Protocol['TCP'], TMsg)
        self.tcp_clients = {}

    def _get_id(self) -> ID:
        id = ID()
        id.component_id = self.component_info.component_id
        return id
    
    def _connect_publishers(self, pub_ids: set[ID]) -> None:
        while len(pub_ids) > 0:
            pub_id = pub_ids.pop()
            if pub_id.component_id not in self.tcp_clients:
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.setblocking(False)

                while not self._shutdown_flag:
                    try:
                        client.connect((pub_id.uri.address.decode("utf-8"), pub_id.uri.port))
                        send_all_bytes(client, self._get_id().encode())
                        self.tcp_clients[pub_id.component_id] = client
                    except socket.timeout:
                        continue
                    except Exception as e:
                        if e.errno == errno.EINPROGRESS or e.errno == errno.EALREADY:
                            continue
                        elif e.errno == errno.EISCONN:
                            send_all_bytes(client, self._get_id().encode())
                            self.tcp_clients[pub_id.component_id] = client
                            break
                        logging.error("Unknown error: " + str(e))
                        break
        self.num_pubs = len(self.tcp_clients)

    def _remove_publishers(self, pub_ids: set[ID]) -> None:
        for pub_id in pub_ids:
            if pub_id.component_id in self.tcp_clients:
                self.tcp_clients[pub_id.component_id].close()
                del self.tcp_clients[pub_id.component_id]
        pub_ids.clear()
        self.num_pubs = len(self.tcp_clients)

    def _handle_msg(self) -> None:
        for id in self.tcp_clients:
            data = recv_all_bytes(self.tcp_clients[id], self.TMsg.size())
            if data is not None:
                self.callback(self.TMsg.decode(data))

