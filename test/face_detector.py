import face_recognition
import cv2
import numpy as np
import argparse
from threading import Lock

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
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
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

    sub = Node.subscribe(CompressedImage, "cam/rear/jpg", storeFrame)
    if sub is None:
        print("Failed to subscribe to video")
        return

    Node.spin(False)

    while Node.ok():
        frame_mutex.acquire()
        if frame is not None:
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_frame = small_frame[:, :, ::-1]
            face_locations = face_recognition.face_locations(rgb_frame)

            for top, right, bottom, left in face_locations:
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
            cv2.imshow("Video", frame)
        frame_mutex.release()

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
