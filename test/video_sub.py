import cv2
import numpy as np
import argparse
from threading import Lock

from rixcore.common import RIX_HUB_PORT
from rixcore.node import Node
from rixcore.publisher import Publisher
from rixmsg.sensor.CompressedImage import CompressedImage
from rixmsg.sensor.Image import Image

frame = None
frame_mutex = Lock()


def storeFrame(msg: "CompressedImage") -> None:
    global frame
    frame_mutex.acquire()
    arr = np.array(msg.data, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    frame_mutex.release()
    if frame is None:
        print("Error decoding frame")
        return


def main():
    parser = argparse.ArgumentParser(description="Video Subscriber")
    parser.add_argument(
        "-i", "--ip", type=str, default="127.0.0.1", help="Hub IP address"
    )
    args = parser.parse_args()

    hubIP = args.ip
    if not Node.init("video_sub", hubIP):
        print("Failed to initialize node")
        return

    sub = Node.subscribe(CompressedImage, "video", storeFrame)
    if sub is None:
        print("Failed to subscribe to video")
        return

    Node.spin(False)

    while Node.ok():
        frame_mutex.acquire()
        if frame is not None:
            cv2.imshow("video", frame)
        frame_mutex.release()

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
