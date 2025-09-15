from rixcore.node import Node
from rixmsg.standard.String import String
from rixmsg.standard.UInt32 import UInt32


def alphabet(req: UInt32, res: String) -> None:
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    res.data = str(alphabet[req.data % 26])
    print("Received request: " + str(req.data))
    print("Sending response: " + res.data)


def main():
    node = Node("simple_service")
    if not node.ok():
        print("Failed to initialize node")
        return

    srv = node.create_service(UInt32, String, "/alphabet", alphabet)
    if not srv.ok():
        print("Failed to advertise service")
        return

    try:
        node.spin()
    except KeyboardInterrupt as e:
        return


if __name__ == "__main__":
    main()
