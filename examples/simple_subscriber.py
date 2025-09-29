from rix.core import Node
from rix.msg.standard import Header


def main():
    node = Node("simple_publisher")
    if not node.ok():
        print("Error! Failed to initialize node.")

    def callback(msg: Header) -> None:
        print(f"Received: {msg.frame_id}: {msg.stamp.sec}.{msg.stamp.nsec}")

    sub = node.create_subscriber(Header, "/chatter", callback)
    if not sub.ok():
        print("Error! Failed to create subscriber.")
        return

    node.spin()


if __name__ == "__main__":
    main()
