import signal
import time
import ctypes
import argparse
from picamera2 import Picamera2, Preview
import cv2
import numpy as np

from rixcore.common import Protocol, get_local_ip, RIX_HUB_PORT
from rixcore.node import Node
from rixcore.publisher import Publisher
from rixmsg.sensor.Image import ImageTemplate
from rixmsg.sensor.CompressedImage import CompressedImageTemplate

# Define default WIDTH, HEIGHT
WIDTH = 1920
HEIGHT = 1080

# Define the Image and CompressedImage message types
Image = ImageTemplate(WIDTH, HEIGHT, 3)
COMPRESSED_MAX_SIZE = WIDTH * HEIGHT * 3 // 8
CompressedImage = CompressedImageTemplate(COMPRESSED_MAX_SIZE)

def main():
    parser = argparse.ArgumentParser(description='Video Publisher')
    parser.add_argument('--hub_ip', type=str, default=get_local_ip(), help='Hub IP address')
    parser.add_argument('--camera', type=int, default=0, help='Camera index')
    args = parser.parse_args()

    hub_ip = args.hub_ip
    CAMERA_INDEX = args.camera

    node = Node()
    node.init('video_pub', hub_ip, RIX_HUB_PORT)
    raw_pub = node.advertise(Image, "video_raw", Protocol['TCP'])
    jpg_pub = node.advertise(CompressedImage, "video_jpg", Protocol['TCP'])

    node.spin(False)

    # Initialize Picamera2
    picam2 = Picamera2()
    config = picam2.create_still_configuration(main={"size": (WIDTH, HEIGHT)})
    picam2.configure(config)
    picam2.start()

    jpg_msg = CompressedImage()
    raw_msg = Image()

    while node.ok():
        frame = picam2.capture_array()
        if frame is None:
            print("Error reading frame")
            break

        # Resize the frame (if necessary)
        frame = cv2.resize(frame, (WIDTH, HEIGHT))

        # Flip the frame vertically
        frame = cv2.flip(frame, 0)

        # Convert the frame to a ctypes array
        flat_frame = frame.flatten()
        ctypes_array = (ctypes.c_uint8 * flat_frame.size).from_buffer_copy(flat_frame)
        ctypes.memmove(raw_msg.data, ctypes_array, flat_frame.nbytes)

        raw_msg.width = WIDTH
        raw_msg.height = HEIGHT
        raw_msg.channels = 3
        raw_pub.publish(raw_msg)

        # Encode the frame as a JPEG image
        ret, jpg_frame = cv2.imencode('.jpg', frame)
        if not ret:
            print("Error encoding frame")
            continue

        if jpg_frame.nbytes > COMPRESSED_MAX_SIZE:
            print(f"Compressed image size exceeds maximum size, {jpg_frame.nbytes} > {COMPRESSED_MAX_SIZE}")
            continue

        # Convert the jpg_frame to a ctypes array
        jpg_frame = jpg_frame.flatten()
        ctypes_array = (ctypes.c_uint8 * jpg_frame.size).from_buffer_copy(jpg_frame)
        ctypes.memmove(jpg_msg.data, ctypes_array, jpg_frame.nbytes)
        jpg_msg.num_bytes = len(jpg_frame)
        jpg_pub.publish(jpg_msg)

    # Stop the camera
    picam2.stop()

if __name__ == '__main__':
    main()
