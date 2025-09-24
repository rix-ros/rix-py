from rixcore.node import Node
from rixmsg.standard.Header import Header
from rixcore.timer import Timer
from rixcore.common import RIXHUB_IP, DEFAULT_IP, RIXHUB_PORT

from time import time_ns
import argparse

DEFAULT_PORT = 8004


def main(args: argparse.Namespace):
    node = Node("simple_publisher", (args.rixhub, RIXHUB_PORT))
    if not node.ok():
        print("Error! Failed to initialize node.")
        return

    pub = node.create_publisher(Header, "/chatter", (args.default_ip, args.port))
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--rixhub", default=RIXHUB_IP, help="RixHub IP address")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="RixHub port")
    parser.add_argument(
        "--default_ip", default=DEFAULT_IP, help="Default IP address for publisher"
    )
    args = parser.parse_args()
    main(args)
