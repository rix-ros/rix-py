from rix.core import Node, Timer
from rix.msg.standard import Header

from time import time_ns


def main():
    node = Node("simple_publisher")
    if not node.ok():
        print("Error! Failed to initialize node.")
        return

    pub = node.create_publisher(Header, "/chatter")
    if not pub.ok():
        print("Error! Failed to create publisher.")
        return

    def timer_callback(event: Timer.Event):
        msg = Header()
        current_time = time_ns()
        msg.frame_id = "test"
        msg.stamp.sec = current_time // 1000000000
        msg.stamp.nsec = current_time % 1000000000
        pub.publish(msg)

    node.create_timer(1, timer_callback)
    node.spin()


if __name__ == "__main__":
    main()
