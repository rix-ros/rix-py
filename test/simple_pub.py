from rixcore.node import Node
from rixcore.publisher import Publisher
from rixmsg.standard.Header import Header

from time import time_ns, sleep


def main():
    if not Node.init("test", "127.0.0.1"):
        print("Failed to initialize node")
        return

    pub = Node.advertise(Header, "test_topic")
    if pub is None:
        print("Failed to advertise publisher")
        Node.shutdown()
        return

    Node.spin(False)

    while Node.ok():
        msg = Header()
        current_time = time_ns()
        msg.frame_id = "test"
        msg.stamp.sec = current_time // 1000000000
        msg.stamp.nsec = current_time % 1000000000
        pub.publish(msg)
        sleep(1)


if __name__ == "__main__":
    main()
