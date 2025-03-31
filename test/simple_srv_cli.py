from rixcore.common import RIX_HUB_PORT
from rixcore.node import Node
from rixcore.service_client import ServiceClient
from rixmsg.standard.String import String
from rixmsg.standard.UInt32 import UInt32
from time import sleep


def main():
    if not Node.init("simple_srv_cli", "127.0.0.1", RIX_HUB_PORT):
        print("Failed to initialize node")
        return

    srvCli = Node.serviceClient(String, UInt32, "alphabet")
    if srvCli is None:
        print("Failed to create service client")
        Node.shutdown()
        return

    Node.spin(False)

    i = 0
    while Node.ok():
        req = UInt32()
        req.data = i
        res = String()
        srvCli.call(req, res)
        print(f"Request: {req.data}, Response: {res.data}")
        i += 1
        sleep(1)


if __name__ == "__main__":
    main()
