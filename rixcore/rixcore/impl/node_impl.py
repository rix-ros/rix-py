import socket
import threading
from rixcore.common import PROTOCOL, OPCODE, RIX_HUB_PORT
from rixmsg.mediator.NodeInfo import NodeInfo
from rixmsg.mediator.PubNotify import PubNotify
from rixmsg.mediator.SubNotify import SubNotify
from rixmsg.mediator.SrvRequest import SrvRequest
from rixmsg.mediator.SrvResponse import SrvResponse
from rixmsg.mediator.Operation import Operation
from rixmsg.mediator.Status import Status
from rixcore.publisher import Publisher
from rixcore.subscriber import Subscriber
from rixcore.service import Service
from rixcore.service_client import ServiceClient


class NodeImpl:
    def __init__(self):
        self.spinning = False
        self.shutdownFlag = True
        self.mutex = threading.Lock()
        self.server = None
        self.spinThread = None
        self.publishers = {}
        self.subscribers = {}
        self.services = {}
        self.serviceClients = {}

    def init(self, id, machineId, name, hubIP):
        self.server = socket.create_server(("", 0))
        self.server.settimeout(0.25)
        self.info = NodeInfo()
        self.info.name = name
        self.info.id = id
        self.info.machine_id = machineId
        self.info.protocol = PROTOCOL["TCP"]
        ep = self.server.getsockname()
        self.info.endpoint.address = ep[0]
        self.info.endpoint.port = ep[1]
        self.hubEp = (hubIP, RIX_HUB_PORT)

        if not self._registerNode():
            return False

        self.shutdownFlag = False
        return True

    def ok(self):
        return not self.shutdownFlag

    def advertise(self, impl):
        if self.shutdownFlag:
            return None
        info = impl.getInfo()
        if not self._registerPub(info):
            return None

        pub = Publisher(impl)
        self.publishers[info.id] = pub
        return pub

    def subscribe(self, impl):
        if self.shutdownFlag:
            return None
        info = impl.getInfo()
        if not self._registerSub(info):
            return None

        sub = Subscriber(impl)
        self.subscribers[info.id] = sub
        return sub

    def advertiseService(self, impl):
        if self.shutdownFlag:
            return None
        info = impl.getInfo()
        if not self._registerSrv(info):
            return None

        service = Service(impl)
        self.services[info.id] = service
        return service

    def serviceClient(self, impl):
        if self.shutdownFlag:
            return None
        request = impl.getRequest()
        response = self._requestSrv(request)
        if response is None:
            return None
        ep = (response.srv_info.endpoint.address, response.srv_info.endpoint.port)
        impl.setEndpoint(ep)
        client = ServiceClient(impl)
        self.serviceClients[request.id] = client
        return client

    def shutdown(self, obj=None):
        if obj == None:
            self.shutdownFlag = True
            if self.spinThread and self.spinThread.is_alive():
                self.spinThread.join()
            self._deregisterNode()
            if self.server:
                self.server.close()

            for pub in self.publishers.values():
                pub.impl.shutdown()
            self.publishers.clear()

            for sub in self.subscribers.values():
                sub.impl.shutdown()
            self.subscribers.clear()

            for srv in self.services.values():
                srv.impl.shutdown()
            self.services.clear()

            for srvCli in self.serviceClients.values():
                srvCli.impl.shutdown()
            self.serviceClients.clear()

        elif isinstance(obj, Publisher):
            self._deregisterPub(obj)
        elif isinstance(obj, Subscriber):
            self._deregisterSub(obj)
        elif isinstance(obj, Service):
            self._deregisterSrv(obj)
        else:
            pass

    def spin(self, block=True):
        if not self.ok():
            return
        self.spinning = True
        self.spinThread = threading.Thread(target=self._run)
        self.spinThread.start()
        if block and self.spinThread.is_alive():
            self.spinThread.join()

    def _run(self):
        while self.ok():
            try:
                sock, _ = self.server.accept()
            except TimeoutError as e:
                continue
            except Exception as e:
                return

            opMsg = Operation()
            recvSize = opMsg.size()
            buffer = sock.recv(recvSize)
            opMsg.deserialize(buffer, {"offset": 0})
            recvSize = opMsg.len
            buffer = sock.recv(opMsg.len)
            self._handleMsg(opMsg, buffer)
            sock.close()

    def _handleMsg(self, opMsg, buffer):
        if opMsg.opcode == OPCODE.PUB_NOTIFY:
            pubNotify = PubNotify()
            pubNotify.deserialize(buffer, {"offset": 0})
            self._handlePubNotify(pubNotify)
        elif opMsg.opcode == OPCODE.SUB_NOTIFY:
            subNotify = SubNotify()
            subNotify.deserialize(buffer, {"offset": 0})
            self._handleSubNotify(subNotify)
        elif opMsg.opcode == OPCODE.TERMINATE:
            self.shutdownFlag = True
        else:
            pass

    def _registerNode(self):
        opMsg = Operation()
        opMsg.opcode = OPCODE.NODE_REGISTER
        opMsg.len = self.info.size()
        buffer = bytearray()
        opMsg.serialize(buffer)
        self.info.serialize(buffer)
        return self._sendRegister(buffer)

    def _registerPub(self, info):
        opMsg = Operation()
        opMsg.opcode = OPCODE.PUB_REGISTER
        opMsg.len = info.size()
        buffer = bytearray()
        opMsg.serialize(buffer)
        info.serialize(buffer)
        return self._sendRegister(buffer)

    def _registerSub(self, info):
        opMsg = Operation()
        opMsg.opcode = OPCODE.SUB_REGISTER
        opMsg.len = info.size()
        buffer = bytearray()
        opMsg.serialize(buffer)
        info.serialize(buffer)
        return self._sendRegister(buffer)

    def _registerSrv(self, info):
        opMsg = Operation()
        opMsg.opcode = OPCODE.SRV_REGISTER
        opMsg.len = info.size()
        buffer = bytearray()
        opMsg.serialize(buffer)
        info.serialize(buffer)
        return self._sendRegister(buffer)

    def _requestSrv(self, request):
        opMsg = Operation()
        opMsg.opcode = OPCODE.SRV_REQUEST
        opMsg.len = request.size()
        buffer = bytearray()
        opMsg.serialize(buffer)
        request.serialize(buffer)
        return self._sendSrvRequest(buffer)

    def _deregisterNode(self):
        opMsg = Operation()
        opMsg.opcode = OPCODE.NODE_DEREGISTER
        opMsg.len = self.info.size()
        buffer = bytearray()
        opMsg.serialize(buffer)
        self.info.serialize(buffer)
        return self._sendDeregister(buffer)

    def _deregisterPub(self, pub):
        opMsg = Operation()
        opMsg.opcode = OPCODE.PUB_DEREGISTER
        opMsg.len = pub.info.size()
        buffer = bytearray()
        opMsg.serialize(buffer)
        pub.info.serialize(buffer)
        return self._sendDeregister(buffer)

    def _deregisterSub(self, sub):
        opMsg = Operation()
        opMsg.opcode = OPCODE.SUB_DEREGISTER
        opMsg.len = sub.info.size()
        buffer = bytearray()
        opMsg.serialize(buffer)
        sub.info.serialize(buffer)
        return self._sendDeregister(buffer)

    def _deregisterSrv(self, srv):
        opMsg = Operation()
        opMsg.opcode = OPCODE.SRV_DEREGISTER
        opMsg.len = srv.info.size()
        buffer = bytearray()
        opMsg.serialize(buffer)
        srv.info.serialize(buffer)
        return self._sendDeregister(buffer)

    def _handlePubNotify(self, pubNotify):
        pub = self.publishers.get(pubNotify.id)
        if pub == None:
            return
        if pubNotify.connect == True:
            pub._addSubscribers(pubNotify.subscribers)
        else:
            pub._removeSubscribers(pubNotify.subscribers)

    def _handleSubNotify(self, subNotify):
        sub = self.subscribers.get(subNotify.id)
        if sub == None:
            return

        if subNotify.connect == True:
            sub._addPublishers(subNotify.publishers)
        else:
            sub._removePublishers(subNotify.publishers)

    def _sendRegister(self, buffer):
        sock = None
        try:
            sock = socket.create_connection((self.hubEp[0], self.hubEp[1]))
            sock.send(buffer)

            statusMsg = Status()
            recvSize = statusMsg.size()
            rdBuffer = bytearray(recvSize)
            sock.recv_into(rdBuffer, recvSize)
            statusMsg.deserialize(rdBuffer, {"offset": 0})

            sock.close()
            return statusMsg.error == 0
        except Exception as e:
            if sock is not None:
                sock.close()
            return False

    def _sendSrvRequest(self, buffer):
        sock = None
        try:
            sock = socket.create_connection((self.hubEp[0], self.hubEp[1]))
            sock.send(buffer)

            opMsg = Operation()
            recvSize = opMsg.size()
            opMsgBuffer = bytearray(recvSize)
            sock.recv_into(opMsgBuffer, recvSize)
            opMsg.deserialize(opMsgBuffer, {"offset": 0})
            recvSize = opMsg.len
            resBuffer = bytearray(recvSize)
            sock.recv_into(resBuffer, recvSize)

            res = SrvResponse()
            res.deserialize(resBuffer, {"offset": 0})

            sock.close()
            return res
        except Exception as e:
            if sock is not None:
                sock.close()
            return None

    def _sendDeregister(self, buffer):
        sock = None
        try:
            sock = socket.create_connection((self.hubEp[0], self.hubEp[1]))
            sock.send(buffer)
            sock.close()
            return True
        except Exception as e:
            if sock is not None:
                sock.close()
            return False
