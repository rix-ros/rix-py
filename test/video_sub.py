import cv2
import signal
import time
import ctypes
import numpy as np
import argparse

from rixcore.common import Protocol, get_local_ip, RIX_HUB_PORT
from rixcore.node import Node
from rixcore.publisher import Publisher
from rixmsg.sensor.CompressedImage import CompressedImageTemplate
from rixmsg.sensor.Image import ImageTemplate

# Define default WIDTH, HEIGHT
WIDTH = 1920
HEIGHT = 1080
Image = ImageTemplate(WIDTH, HEIGHT, 3)
COMPRESSED_MAX_SIZE = WIDTH * HEIGHT * 3 // 8
CompressedImage = CompressedImageTemplate(COMPRESSED_MAX_SIZE)

frame = None
frame_rates = []
last_frame_time = None

def show_raw_cb(msg: 'Image') -> None:
    global frame, frame_rate, last_frame_time

    # Calculate running average frame rate
    current_time = time.time()
    if last_frame_time is not None:
        time_diff = current_time - last_frame_time
        frame_rates.append(1.0 / time_diff)
        if len(frame_rates) > 10:
            frame_rates.pop(0)
    last_frame_time = current_time

    print(f"\rCurrent frame rate: {np.mean(frame_rates):.2f}", end="")

    # Convert the ctypes array to a numpy array
    data_array = np.ctypeslib.as_array(msg.data, shape=(msg.width * msg.height * msg.channels,))

    # Reshape the data array into an image
    frame = data_array.reshape((msg.height, msg.width, msg.channels))
    if frame is None:
        print("Error reshaping frame")
        return

def show_jpg_cb(msg: 'CompressedImage') -> None:
    global frame, frame_rate, last_frame_time

    # Calculate running average frame rate
    current_time = time.time()
    if last_frame_time is not None:
        time_diff = current_time - last_frame_time
        frame_rates.append(1.0 / time_diff)
        if len(frame_rates) > 10:
            frame_rates.pop(0)
    last_frame_time = current_time

    print(f"\rCurrent frame rate: {np.mean(frame_rates):.2f}", end="")
    
    # Convert the ctypes array to a numpy array
    data_array = np.ctypeslib.as_array(msg.data, shape=(msg.num_bytes,))

    # Decode the JPEG image
    frame = cv2.imdecode(data_array, cv2.IMREAD_COLOR)
    if frame is None:
        print("Error decoding frame")
        return

def main():
    parser = argparse.ArgumentParser(description='Video Subscriber')
    parser.add_argument('--use_jpg', action='store_true', help='Use compressed JPEG image format')
    args = parser.parse_args()

    USE_JPG = args.use_jpg

    node = Node()
    node.init('video_pub', get_local_ip(), RIX_HUB_PORT)

    frame_sub = None
    name = None
    if USE_JPG:
        frame_sub = node.subscribe(CompressedImage, "video_jpg", show_jpg_cb, Protocol['TCP'])
        name = "video_jpg"
    else:
        frame_sub = node.subscribe(Image, "video_raw", show_raw_cb, Protocol['TCP'])
        name = "video_raw"

    node.spin(False)

    while node.ok():
        if frame is not None:
            cv2.imshow(name, frame)
            if cv2.waitKey(100) & 0xFF == ord('q'):
                break

    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
