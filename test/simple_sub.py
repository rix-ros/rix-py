from rixcore.node import Node
from rixcore.subscriber import Subscriber
from rixmsg.standard.Header import Header


def callback(msg: Header) -> None:
    print(f"Received: {msg.frame_id}: {msg.stamp.sec}.{msg.stamp.nsec}")


def main():
    if not Node.init("test", "127.0.0.1"):
        print("Failed to initialize node")
        return

    sub = Node.subscribe(Header, "test_topic", callback)
    if sub is None:
        print("Failed to subscribe")
        Node.shutdown()
        return
    Node.spin(True)


if __name__ == "__main__":
    main()
