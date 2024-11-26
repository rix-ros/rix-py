import cv2
import signal
import time
import ctypes
import argparse

from rixcore.common import Protocol, get_local_ip, RIX_HUB_PORT
from rixcore.node import Node
from rixcore.publisher import Publisher
from rixmsg.sensor.Image import ImageTemplate
from rixmsg.sensor.CompressedImage import CompressedImageTemplate
from rixmsg.sensor.Image import ImageTemplate

# Define default WIDTH, HEIGHT
WIDTH = 1280
HEIGHT = 720

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

    # Open the default camera
    cam = cv2.VideoCapture(CAMERA_INDEX)
    jpg_msg = CompressedImage()
    raw_msg = Image()

    while node.ok():
        ret, frame = cam.read()
        if not ret:
            print("Error reading frame")
            break

        # Resize the frame
        frame = cv2.resize(frame, (WIDTH, HEIGHT))

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

    # Release the capture and writer objects
    cam.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()