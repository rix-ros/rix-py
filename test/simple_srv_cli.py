from rixcore.node import Node
from rixcore.service_client import ServiceClient
from rixmsg.standard.String import String
from rixmsg.standard.UInt32 import UInt32
from threading import Thread
from time import sleep


def main():
    node = Node.create("simple_service_client")
    if not node.ok():
        print("Failed to initialize node")
        return

    service_client = node.create_service_client(UInt32, String, "/alphabet")
    if not service_client.ok():
        print("Failed to create service client")
        node.shutdown()
        return

    thr = Thread(target=lambda: node.spin())
    thr.start()

    i = 0
    try:
        while node.ok():
            req = UInt32()
            req.data = i
            res = String()
            service_client.call(req, res)
            print(f"Request: {req.data}, Response: {res.data}")
            i += 1
            sleep(1)
    except KeyboardInterrupt as e:
        node.shutdown()


if __name__ == "__main__":
    main()
