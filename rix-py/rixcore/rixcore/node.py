import socket
import sys
import os
import time
import threading
import logging
import random
import signal

from time import time_ns, sleep

from rixcore.common import Protocol, CORE_TOPICS
from rixcore.publisher import IPublisher, Publisher, PublisherTCP
from rixcore.subscriber import ISubscriber, Subscriber, SubscriberTCP
from rixmsg.standard.Info import Info
from rixmsg.standard.ComponentInfo import ComponentInfo
from rixmsg.standard.ID import ID
from rixmsg.standard.URI import URI

# Create Node class
class Node:
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Node, cls).__new__(cls)
        return cls._instance
    
    def __del__(self):
        self.shutdown()

    def init(self, name: str, hub_ip: str, hub_port: int):
        self.name = name
        self.hub_ip = hub_ip
        self.hub_port = hub_port
        self.mutex = threading.Lock()
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._shutdown_flag = False

        logging.basicConfig(level=logging.INFO, format=f'[%(asctime)s] [%(levelname)s] [{self.name}] %(message)s')

        # Set the signal handler for SIGINT and SIGTERM
        signal.signal(signal.SIGINT, Node._sigint_handler)
        signal.signal(signal.SIGTERM, Node._sigint_handler)

        try:
            with open('/etc/rix/rix.conf', 'r') as f:
                self.machine_id = int(f.readline().strip())
        except:
            logging.error("Failed to read machine id")
            sys.exit(1)

        random.seed(None)
        self.node_id = random.getrandbits(64)

        self.client.settimeout(1)
        try:
            self.client.connect((self.hub_ip, self.hub_port))
        except:
            logging.error("Failed to connect to hub")
            sys.exit(1)

        self.pubs: dict[str, IPublisher] = {}
        self.subs: dict[str, ISubscriber] = {}

        self.spin_thread = None
        self.initialized = True

    def spin(self, block: bool = True) -> None:
        if not self.initialized:
            logging.error("Node not initialized")
            return
        if self.spin_thread is not None:
            logging.error("Spin thread already running")
            return
        
        self.spin_thread = threading.Thread(target=self.__run)
        self.spin_thread.start()
        if block:
            self.spin_thread.join()

    def shutdown(self):
        self._shutdown_flag = True

        # Get this thread's ID
        current_thread = threading.current_thread()
        if current_thread != self.spin_thread and self.spin_thread.is_alive():
            self.spin_thread.join()

        for topic in self.pubs:
            for pub in self.pubs[topic]:
                self.__deregister_publisher(pub)
        self.pubs.clear()
            
        for topic in self.subs:
            for sub in self.subs[topic]:
                self.__deregister_subscriber(sub)
        self.subs.clear()
    
        self.client.close()

    def ok(self):
        return not self._shutdown_flag
    
    def advertise(self, TMsg: any, topic: str, protocol: int) -> Publisher:
        pub = None
        if protocol == Protocol['TCP']:
            pub = PublisherTCP(topic, self.node_id, TMsg)
        else:
            logging.error("Invalid protocol")
            return None
        
        if (not self.__register_publisher(pub)):
            logging.error("Failed to register publisher")
            return None

        if self.pubs.get(topic) is None:
            self.pubs[topic] = []
        
        self.pubs[topic].append(pub)
        logging.info("Advertised topic: " + topic)
        return pub

    def subscribe(self, TMsg: any, topic: str, cb: callable, protocol: int) -> Subscriber:
        sub = None
        if protocol == Protocol['TCP']:
            sub = SubscriberTCP(topic, cb, self.node_id, TMsg)
        else:
            logging.error("Invalid protocol")
            return None
        
        if (not self.__register_subscriber(sub)):
            logging.error("Failed to register subscriber")
            return None

        if self.subs.get(topic) is None:
            self.subs[topic] = []
        
        self.subs[topic].append(sub)
        logging.info("Subscribed to topic: " + topic)
        return sub
    
    @staticmethod
    def _sigint_handler(sig, frame):
        node = Node()
        node._shutdown_flag = True

    def __run(self) -> None:
        while self.ok():

            data = None
            try:
                data = self.client.recv(Info.size())
            except socket.timeout:
                pass
            except:
                logging.error("Failed to receive data")
                break

            if data is not None:
                info = Info.decode(data)
                if info.opcode == CORE_TOPICS['PUB_NOTIFY']:
                    self.__handle_pub_notify(info)
                elif info.opcode == CORE_TOPICS['SUB_NOTIFY']:
                    self.__handle_sub_notify(info)
                elif info.opcode == CORE_TOPICS['PUB_DISCONNECT']:
                    self.__handle_pub_disconnect(info)
                elif info.opcode == CORE_TOPICS['SUB_DISCONNECT']:
                    self.__handle_sub_disconnect(info)
                elif info.opcode == CORE_TOPICS['MED_TERMINATE']:
                    logging.info("Received MED_TERMINATE")
                    self.shutdown()
                else:
                    logging.error("Unknown opcode: " + str(info.opcode))

            pubs_to_shutdown = []
            for topic in self.pubs:
                for pub in self.pubs[topic]:
                    if pub._shutdown_flag:
                        pubs_to_shutdown.append(pub)
                        continue
                    pub._run_once()
            for pub in pubs_to_shutdown:
                self.__deregister_publisher(pub)
                self.pubs[pub.component_info.topic.decode("utf-8")].remove(pub)
            
            subs_to_shutdown = []
            for topic in self.subs:
                for sub in self.subs[topic]:
                    if sub._shutdown_flag:
                        subs_to_shutdown.append(sub)
                        continue
                    sub._run_once()
            for sub in subs_to_shutdown:
                self.__deregister_subscriber(sub)
                self.subs[sub.component_info.topic.decode("utf-8")].remove(sub)

    def __register_publisher(self, publisher: IPublisher) -> bool:
        info = Info()
        info.error = 0
        info.opcode = CORE_TOPICS['PUB_REGISTER']
        info.component_info = publisher.component_info
        info.component_info.machine_id = self.machine_id
        info.contact_id = publisher._get_id()

        self.mutex.acquire()
        status = self.client.send(info.encode())
        self.mutex.release()

        if status < 0:
            logging.error("Failed to send PUB_REGISTER")
            return False
        return True


    def __register_subscriber(self, subscriber: ISubscriber) -> bool:
        info = Info()
        info.error = 0
        info.opcode = CORE_TOPICS['SUB_REGISTER']
        info.component_info = subscriber.component_info
        info.component_info.machine_id = self.machine_id
        info.contact_id = subscriber._get_id()

        self.mutex.acquire()
        status = self.client.send(info.encode())
        self.mutex.release()

        if status < 0:
            logging.error("Failed to send SUB_REGISTER")
            return False
        return True

    def __deregister_publisher(self, publisher: IPublisher) -> bool:
        info = Info()
        info.error = 0
        info.opcode = CORE_TOPICS['PUB_DEREGISTER']
        info.component_info = publisher.component_info
        info.component_info.machine_id = self.machine_id

        self.mutex.acquire()
        status = self.client.send(info.encode())
        self.mutex.release()

        if status < 0:
            logging.error("Failed to send PUB_DEREGISTER")
            return False
        return True

    def __deregister_subscriber(self, subscriber: ISubscriber) -> bool:
        info = Info()
        info.error = 0
        info.opcode = CORE_TOPICS['SUB_DEREGISTER']
        info.component_info = subscriber.component_info
        info.component_info.machine_id = self.machine_id

        self.mutex.acquire()
        status = self.client.send(info.encode())
        self.mutex.release()

        if status < 0:
            logging.error("Failed to send SUB_DEREGISTER")
            return False
        return True

    def __handle_pub_notify(self, info: IPublisher) -> None:
        if info.error != 0:
            logging.error("PUB_NOTIFY error: " + str(info.error))
            return
        
        topic = info.component_info.topic.decode("utf-8")
        for p in self.pubs[topic]:
            if p.component_info.component_id == info.component_info.component_id:
                p._add_subscriber(info.contact_id)
                return


    def __handle_sub_notify(self, info: ISubscriber) -> None:
        if info.error != 0:
            logging.error("PUB_NOTIFY error: " + str(info.error))
            return
        
        topic = info.component_info.topic.decode("utf-8")
        for s in self.subs[topic]:
            if s.component_info.component_id == info.component_info.component_id:
                s._add_publisher(info.contact_id)
                return

    def __handle_pub_disconnect(self, info: IPublisher) -> None:
        topic = info.component_info.topic.decode("utf-8")
        for p in self.pubs[topic]:
            if p.component_info.component_id == info.component_info.component_id:
                p._remove_subscriber(info.contact_id)
                return

    def __handle_sub_disconnect(self, info: ISubscriber) -> None:
        topic = info.component_info.topic.decode("utf-8")
        for s in self.subs[topic]:
            if s.component_info.component_id == info.component_info.component_id:
                s._remove_publisher(info.contact_id)
                return