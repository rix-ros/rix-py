import cv2
import argparse

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

        # Get 800x640 frame for performance
        fx_ = 1#400 / frame.shape[1]
        fy_ = 1#320 / frame.shape[0]

        frame = cv2.resize(frame, (0, 0), fx=fx_, fy=fy_)
        print(f"Frame size: {frame.shape[1]}x{frame.shape[0]}")

        # Encode the frame as a JPEG image
        ret, frame = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
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
