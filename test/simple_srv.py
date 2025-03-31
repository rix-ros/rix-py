from rixcore.common import RIX_HUB_PORT
from rixcore.node import Node
from rixcore.service import Service
from rixmsg.standard.String import String
from rixmsg.standard.UInt32 import UInt32

from time import time_ns, sleep


def alphabet(req: UInt32) -> String:
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    res = String()
    res.data = alphabet[req.data % 26]
    return res


def main():
    if not Node.init("simple_srv", "127.0.0.1", RIX_HUB_PORT):
        print("Failed to initialize node")
        return

    srv = Node.advertiseService(UInt32, String, "alphabet", alphabet)
    if srv is None:
        print("Failed to advertise service")
        Node.shutdown()
        return

    Node.spin(True)


if __name__ == "__main__":
    main()
