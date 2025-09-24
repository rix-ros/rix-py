import cv2
import numpy as np
import argparse
from threading import Lock

from rixcore.node import Node
from rixcore.timer import Timer
from rixmsg.sensor.CompressedImage import CompressedImage

frame = None
frame_mutex = Lock()


def storeFrame(msg: CompressedImage) -> None:
    global frame
    with frame_mutex:
        arr = np.array(msg.data, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        print("Error! Failed to decode frame.")
        return


def main():
    node = Node("video_sub")
    if not node.ok():
        print("Error! Failed to create node.")
        return

    sub = node.create_subscriber(CompressedImage, "/video", storeFrame)
    if not sub.ok():
        print("Error! Failed to create subscriber.")
        return

    def timer_callback(event: Timer.Event) -> None:
        frame_mutex.acquire()
        if frame is not None:
            cv2.imshow("/video", frame)
        frame_mutex.release()

        if cv2.waitKey(1) & 0xFF == ord("q"):
            cv2.destroyAllWindows()
            return

    node.create_timer(1 / 120, timer_callback)
    node.spin()


if __name__ == "__main__":
    main()
