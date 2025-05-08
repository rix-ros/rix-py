import cv2
import time
import argparse

from rixcore.node import Node
from rixcore.publisher import Publisher
from rixmsg.sensor.Image import Image
from rixmsg.sensor.CompressedImage import CompressedImage
from rixmsg.sensor.Image import Image


def main():
    parser = argparse.ArgumentParser(description="Video Publisher")
    parser.add_argument(
        "-i", "--ip", type=str, default="127.0.0.1", help="Hub IP address"
    )
    parser.add_argument("-c", "--camera", type=int, default=0, help="Camera index")
    args = parser.parse_args()

    hubIP = args.ip
    camIndex = args.camera

    Node.init("video_pub", hubIP)
    pub = Node.advertise(CompressedImage, "video")

    Node.spin(False)

    cam = cv2.VideoCapture(camIndex)
    msg = CompressedImage()

    while Node.ok():
        ret, frame = cam.read()
        if not ret:
            print("Error reading frame")
            break

        # Encode the frame as a JPEG image
        ret, frame = cv2.imencode(".jpg", frame)
        if not ret:
            print("Error encoding frame")
            continue

        msg.data = frame.flatten()
        pub.publish(msg)

    cam.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
