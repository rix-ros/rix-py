import socket
import sys
import os
import time
import threading
import logging
import random
from abc import ABC, abstractmethod
import errno

from rixcore.common import Protocol, get_local_ip
from rixmsg.standard.ComponentInfo import ComponentInfo
from rixmsg.standard.ID import ID
from rixmsg.standard.URI import URI

class ISubscriber(ABC):
    def __init__(self, topic: str, node_id: int, protocol: int, TMsg: any):
        self.component_info = ComponentInfo()
        self.component_info.topic = topic.encode()
        self.component_info.protocol = protocol
        self.component_info.node_id = node_id
        self.component_info.component_id = random.getrandbits(64)
        self.component_info.msg_hash_a[0] = TMsg.hash()[0]
        self.component_info.msg_hash_a[1] = TMsg.hash()[1]

        self.num_pubs = 0
        self._shutdown_flag = False

    def get_num_publishers(self) -> int:
        return self.num_pubs

    def shutdown(self):
        self._shutdown_flag = True

    @abstractmethod
    def _get_id(self) -> ID:
        pass

    @abstractmethod
    def _add_publisher(self, pub_id: ID) -> None:
        pass

    @abstractmethod
    def _remove_publisher(self, pub_id: ID) -> None:
        pass

    @abstractmethod
    def _run_once(self) -> None:
        pass

class Subscriber(ISubscriber):
    def __init__(self, topic: str, callback: callable, node_id: int, protocol: int, TMsg: any):
        super().__init__(topic, node_id, protocol, TMsg)
        self.callback = callback
        self.add_pub_set = []
        self.remove_pub_set = []
        self.TMsg = TMsg

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
                client.settimeout(1)
                client.setblocking(False)

                status = -1
                while not self._shutdown_flag:
                    try:
                        client.connect((pub_id.uri.address.decode("utf-8"), pub_id.uri.port))
                        client.send(self._get_id().encode())
                        self.tcp_clients[pub_id.component_id] = client
                    except socket.timeout:
                        continue
                    except Exception as e:
                        if e.errno == errno.EINPROGRESS or e.errno == errno.EALREADY:
                            continue
                        elif e.errno == errno.EISCONN:
                            client.send(self._get_id().encode())
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
            try:
                data = self.tcp_clients[id].recv(self.TMsg.size())
            except socket.timeout:
                continue
            except Exception as e:
                if e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                    continue
                logging.error("Failed to receive data")
                break
            self.callback(self.TMsg.decode(data))

