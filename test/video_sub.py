import cv2
import numpy as np
import argparse
from threading import Lock

from rixcore.common import RIXHUB_PORT
from rixcore.node import Node
from rixcore.publisher import Publisher
from rixcore.timer import Timer
from rixmsg.sensor.CompressedImage import CompressedImage
from rixmsg.sensor.Image import Image

frame = None
frame_mutex = Lock()


def storeFrame(msg: CompressedImage) -> None:
    global frame
    frame_mutex.acquire()
    arr = np.array(msg.data, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    frame_mutex.release()
    if frame is None:
        print("Error! Failed to decode frame.")
        return


def main(args):
    hubIP = args.ip
    node = Node("video_sub", (hubIP, RIXHUB_PORT))
    if not node.ok():
        print("Error! Failed to create node.")
        return

    sub = node.create_subscriber(CompressedImage, "/video", storeFrame)
    if sub is None:
        print("Error! Failed to create subscriber.")
        return

    timer = None

    def timer_callback(event: Timer.Event) -> None:
        frame_mutex.acquire()
        if frame is not None:
            cv2.imshow("/video", frame)
        frame_mutex.release()

        if cv2.waitKey(1) & 0xFF == ord("q"):
            cv2.destroyAllWindows()
            timer.set_callback(None)
            return

    timer = node.create_timer(1 / 120, timer_callback)
    node.spin()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Video Subscriber")
    parser.add_argument(
        "-i", "--ip", type=str, default="127.0.0.1", help="Hub IP address"
    )
    args = parser.parse_args()
    main(args)
