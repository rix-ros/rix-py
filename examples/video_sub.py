import cv2
import numpy as np
import time
from threading import Lock

from rix.core import Node, TimerCallback
from rix.sensor_msgs import CompressedImage

frame = None
frame_mutex = Lock()
last_time = None
frame_count = 0
fps = 0.0


def store_frame(msg: CompressedImage) -> None:
    global frame, last_time, frame_count, fps

    current_time = time.time()

    with frame_mutex:
        # Fast: direct conversion without copying
        np_arr = np.frombuffer(msg.data, np.uint8)
        print(f"Received frame size: {len(msg.data)} bytes")
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if frame is None:
        print("Error! Failed to decode frame.")
        return

    # Calculate FPS
    if last_time is not None:
        frame_count += 1
        elapsed = current_time - last_time

        # Update FPS every second
        if elapsed >= 1.0:
            fps = frame_count / elapsed
            print(f"FPS: {fps:.2f}")
            frame_count = 0
            last_time = current_time
    else:
        last_time = current_time


def main():
    node = Node("video_sub")
    if not node.ok():
        print("Error! Failed to create node.")
        return

    sub = node.create_subscriber(CompressedImage, "/video", store_frame)
    if not sub.ok():
        print("Error! Failed to create subscriber.")
        return

    def timer_callback(event: TimerCallback.Event) -> None:
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
