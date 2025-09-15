import cv2
import time
import argparse

from rixcore.common import RIXHUB_PORT
from rixcore.node import Node
from rixcore.publisher import Publisher
from rixmsg.sensor.Image import Image
from rixmsg.sensor.CompressedImage import CompressedImage
from rixmsg.sensor.Image import Image


def main(args):
    hubIP = args.ip
    camIndex = args.camera

    node = Node("video_pub", (hubIP, RIXHUB_PORT))
    if not node.ok():
        print("Error! Failed to create node.")
        return

    pub = node.create_publisher(CompressedImage, "/video")
    if not pub.ok():
        print("Error! Failed to create publisher.")
        return

    cam = cv2.VideoCapture(camIndex)
    msg = CompressedImage()

    def timer_callback(event):
        ret, frame = cam.read()
        if not ret:
            print("Error! Failed to read frame.")
            return

        # Encode the frame as a JPEG image
        ret, frame = cv2.imencode(".jpg", frame)
        if not ret:
            print("Error! Failed to encode frame.")
            return

        msg.data = frame.flatten()
        pub.publish(msg)

    node.create_timer(1 / 60, timer_callback)
    node.spin()

    cam.release()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Video Publisher")
    parser.add_argument(
        "-i", "--ip", type=str, default="127.0.0.1", help="Hub IP address"
    )
    parser.add_argument("-c", "--camera", type=int, default=0, help="Camera index")
    args = parser.parse_args()
    main(args)
