import cv2
import argparse
import ctypes

from rix.core import Node, TimerCallback
from rix.sensor_msgs import CompressedImage


def main(args: argparse.Namespace):
    camIndex = args.camera

    node = Node("video_pub")
    if not node.ok():
        print("Error! Failed to create node.")
        return

    pub = node.create_publisher(CompressedImage, "/video")
    if not pub.ok():
        print("Error! Failed to create publisher.")
        return

    cam = cv2.VideoCapture(camIndex)
    msg = CompressedImage()
    msg.header.frame_id = "camera"
    msg.header.seq = 0

    def timer_callback(event: TimerCallback.Event):
        ret, frame = cam.read()
        if not ret:
            print("Error! Failed to read frame.")
            return

        # Encode the frame as a JPEG image
        ret, frame = cv2.imencode(".jpg", frame)
        if not ret:
            print("Error! Failed to encode frame.")
            return

        msg.header.seq = msg.header.seq + 1
        msg.data = memoryview(frame.tobytes())
        pub.publish(msg)

    node.create_timer(1 / 60, timer_callback)
    node.spin()

    cam.release()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Video Publisher")
    parser.add_argument("-c", "--camera", type=int, default=0, help="Camera index")
    args = parser.parse_args()
    main(args)
