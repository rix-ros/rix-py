from rixcore.node import Node
from rixcore.publisher import Publisher
from rixmsg.standard.Header import Header
from threading import Thread

from time import time_ns, sleep


def main():
    node = Node.create("simple_publisher")

    pub = node.create_publisher(Header, "/chatter")
    if not pub.ok():
        print("Error! Failed to advertise publisher.")
        return

    thr = Thread(target=lambda: node.spin())
    thr.start()

    try:
        while node.ok():
            msg = Header()
            current_time = time_ns()
            msg.frame_id = "test"
            msg.stamp.sec = current_time // 1000000000
            msg.stamp.nsec = current_time % 1000000000
            pub.publish(msg)
            sleep(1)
    except KeyboardInterrupt as e:
        node.shutdown()

    thr.join()


if __name__ == "__main__":
    main()
