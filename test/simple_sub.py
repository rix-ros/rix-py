from rixcore.node import Node
from rixcore.subscriber import Subscriber
from rixmsg.standard.Header import Header


def callback(msg: Header) -> None:
    print(f"Received: {msg.frame_id}: {msg.stamp.sec}.{msg.stamp.nsec}")


def main():
    node = Node.create("simple_subscriber")
    sub = node.create_subscriber(Header, "/chatter", callback)
    if not sub.ok():
        print("Error! Failed to advertise subscriber.")
        return

    node.spin()


if __name__ == "__main__":
    main()
