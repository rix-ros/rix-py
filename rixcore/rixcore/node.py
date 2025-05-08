import logging
import random
import os
import signal
import struct

from rixcore.publisher import Publisher
from rixcore.subscriber import Subscriber
from rixcore.service import Service
from rixcore.service_client import ServiceClient
from rixcore.impl.node_impl import NodeImpl
from rixcore.impl.pub_impl import PubImplBase, PubImplTCP
from rixcore.impl.sub_impl import SubImplBase, SubImplTCP
from rixcore.impl.srv_impl import SrvImplBase, SrvImplTCP
from rixcore.impl.srv_cli_impl import SrvCliImplBase, SrvCliImplTCP
from rixmsg.standard.UInt32 import UInt32


class Node:
    _impl = None  # static NodeImpl
    _initialized = False

    @staticmethod
    def init(name: str, hubIP: str) -> bool:
        if Node._initialized:
            logging.error("Node already initialized")
            return False

        logging.basicConfig(
            level=logging.INFO,
            format=f"[%(asctime)s] [%(levelname)s] [{name}] %(message)s",
        )

        signal.signal(signal.SIGINT, Node._sigint_handler)
        signal.signal(signal.SIGTERM, Node._sigint_handler)
        signal.signal(signal.SIGPIPE, Node._sigint_handler)

        random.seed(None)
        nodeID = Node._generateID()
        machineID = Node._getMachineID()

        Node._impl = NodeImpl()
        Node._initialized = Node._impl.init(nodeID, machineID, name, hubIP)
        return Node._initialized

    @staticmethod
    def spin(block: bool = True) -> None:
        Node._impl.spin(block)

    @staticmethod
    def shutdown() -> None:
        Node._impl.shutdown()

    @staticmethod
    def ok() -> bool:
        return Node._impl.ok()

    @staticmethod
    def advertise(TMsg: any, topic: str, TImpl=PubImplTCP) -> Publisher:
        pubID = Node._generateID()
        msgHash = TMsg().hash()
        pubImpl = TImpl(pubID, Node._impl.info.id, topic, msgHash)
        return Node._impl.advertise(pubImpl)

    @staticmethod
    def subscribe(TMsg: any, topic: str, cb: callable, TImpl=SubImplTCP) -> Subscriber:
        subID = Node._generateID()
        msgHash = TMsg().hash()

        def _cb(buffer):
            msg = TMsg()
            msg.deserialize(buffer, {"offset": 0})
            cb(msg)

        subImpl = TImpl(subID, Node._impl.info.id, topic, msgHash, _cb)
        return Node._impl.subscribe(subImpl)

    @staticmethod
    def advertiseService(
        TReq: any, TRes: any, srvName: str, cb: callable, TImpl=SrvImplTCP
    ) -> Service:
        srvID = Node._generateID()
        reqHash = TReq().hash()
        resHash = TRes().hash()

        def _cb(reqBuffer) -> bytearray | None:
            req = TReq()
            req.deserialize(reqBuffer, {"offset": 0})
            res = cb(req)
            resBuffer = bytearray()
            sizeMsg = UInt32()
            sizeMsg.data = res.size()
            sizeMsg.serialize(resBuffer)
            res.serialize(resBuffer)
            return resBuffer

        srvImpl = SrvImplTCP(srvID, Node._impl.info.id, srvName, reqHash, resHash, _cb)
        return Node._impl.advertiseService(srvImpl)

    @staticmethod
    def serviceClient(
        TReq: any, TRes: any, srvName: str, TImpl=SrvCliImplTCP
    ) -> ServiceClient:
        srvCliID = Node._generateID()
        reqHash = TReq().hash()
        resHash = TRes().hash()
        srvCliImpl = SrvCliImplTCP(
            srvCliID, Node._impl.info.id, srvName, reqHash, resHash
        )
        return Node._impl.serviceClient(srvCliImpl)

    @staticmethod
    def _sigint_handler(sig, frame):
        if sig == signal.SIGINT or sig == signal.SIGTERM:
            if Node._impl is None:
                return
            Node._impl.shutdown()

    @staticmethod
    def _getMachineID() -> int | None:
        ROOT = os.getenv("HOME", os.path.expanduser("~"))
        machine_id_path = ROOT + "/.rix/.machine_id"
        try:
            if not os.path.exists(machine_id_path):
                os.makedirs(os.path.dirname(machine_id_path), exist_ok=True)
                with open(machine_id_path, "wb") as f:
                    random_bytes = random.randbytes(8)
                    f.write(random_bytes)
            with open(machine_id_path, "rb") as f:
                data = f.read()
                return struct.unpack("Q", data)[0]
        except Exception as e:
            logging.error(f"Failed to read machine id: {e}")
            return 0

    @staticmethod
    def _generateID() -> int:
        return random.getrandbits(64)
