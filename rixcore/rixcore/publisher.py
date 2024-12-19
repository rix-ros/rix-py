import socket
import threading
import logging
import random
import errno
from abc import ABC, abstractmethod

from rixcore.common import Protocol, get_public_ip, recv_all_bytes, send_all_bytes
from rixmsg.component.ComponentInfo import ComponentInfo
from rixmsg.component.ID import ID
from rixmsg.component.URI import URI

class Publisher(ABC):
    def __init__(self, topic: str, node_id: int, protocol: int, TMsg: any):
        self.add_sub_set = []
        self.remove_sub_set = []
        self.mutex = threading.Lock()

        self.component_info = ComponentInfo()
        self.component_info.topic = topic.encode()
        self.component_info.protocol = protocol
        self.component_info.node_id = node_id
        self.component_info.component_id = random.getrandbits(64)
        self.component_info.message_info[0] = TMsg.info()

        self.num_subs = 0
        self._shutdown_flag = False

    def get_num_subscribers(self) -> int:
        return self.num_subs

    def shutdown(self):
        self._shutdown_flag = True

    def publish(self, msg: any) -> None:
        self.mutex.acquire()
        self._handle_msg(msg)
        self.mutex.release()

    def _add_subscriber(self, sub_id: ID) -> None:
        self.mutex.acquire()
        self.add_sub_set.append(sub_id)
        self.mutex.release()

    def _remove_subscriber(self, sub_id: ID) -> None:
        self.mutex.acquire()
        self.remove_sub_set.append(sub_id)
        self.mutex.release()

    def _run_once(self) -> None:
        self.mutex.acquire()
        if len(self.add_sub_set) > 0:
            self._accept_subscribers(self.add_sub_set)
        if len(self.remove_sub_set) > 0:
            self._remove_subscribers(self.remove_sub_set)
        self.mutex.release()

    @abstractmethod
    def _handle_msg(self, msg: any) -> None:
        pass

    @abstractmethod
    def _accept_subscribers(self, sub_ids) -> None:
        pass

    @abstractmethod
    def _remove_subscribers(self, sub_ids) -> None:
        pass

    @abstractmethod
    def _get_id(self) -> ID:
        pass

class PublisherTCP(Publisher):
    def __init__(self, topic: str, node_id: int, TMsg: any):
        super().__init__(topic, node_id, Protocol['TCP'], TMsg)
        self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server.bind((get_public_ip(), 0))
        self.tcp_server.listen(64)
        self.tcp_server.settimeout(1)
        self.tcp_server.setblocking(False)

        self.tcp_conns = {}

    def _get_id(self) -> ID:
        # Get the IP and port of the server
        ip, port = self.tcp_server.getsockname()
        id = ID()
        id.component_id = self.component_info.component_id
        id.uri.address = ip.encode()
        id.uri.port = port
        return id
    

    def _handle_msg(self, msg: any) -> None:
        for id in self.tcp_conns:
            msg_encoded = msg.encode()
            status = send_all_bytes(self.tcp_conns[id], msg_encoded)
            if not status:
                logging.error("Failed to send message")

    def _accept_subscribers(self, sub_ids) -> None:
        while len(sub_ids) > 0 and not self._shutdown_flag:

            # Accept the connection
            try:
                conn, _ = self.tcp_server.accept()
                conn.setblocking(False)
            except socket.timeout:
                continue
            except Exception as e:
                if e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                    continue
                logging.error("Failed to accept connection: " + str(e))
                break
            
            # Receive the ID of the subscriber
            data = recv_all_bytes(conn, ID.size(), True)
            sub_id = ID.decode(data)
            self.tcp_conns[sub_id.component_id] = conn
            sub_ids.pop()
        self.num_subs = len(self.tcp_conns)

    def _remove_subscribers(self, sub_ids) -> None:
        for sub_id in sub_ids:
            if sub_id.component_id in self.tcp_conns:
                self.tcp_conns[sub_id.component_id].close()
                del self.tcp_conns[sub_id.component_id]
        sub_ids.clear()
        self.num_subs = len(self.tcp_conns)