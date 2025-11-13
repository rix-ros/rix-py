#!/usr/bin/env python3
"""
Laser Scan Visualizer

Subscribes to a LaserScan topic using RIX and visualizes the data
in real-time using matplotlib.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from rix.core import Node
from rix.sensor_msgs import LaserScan


class LaserScanVisualizer:
    def __init__(self, topic="/scan", max_range=10.0):
        """
        Initialize the visualizer.

        Args:
            topic: The LaserScan topic to subscribe to
            max_range: Maximum range for the plot (in meters)
        """
        self.topic = topic
        self.max_range = max_range

        # Setup the plot
        self.fig, self.ax = plt.subplots(
            subplot_kw={"projection": "polar"}, figsize=(10, 10)
        )
        self.ax.set_ylim(0, self.max_range)  # Fixed range limit
        self.ax.set_title("Laser Scan Visualization", pad=20)
        self.ax.grid(True)

        # Initialize scatter plot
        self.scatter = self.ax.scatter([], [], c=[], s=50, cmap="viridis", alpha=0.6)
        self.colorbar = plt.colorbar(self.scatter, ax=self.ax, label="Intensity")

        self.current_scan = None
        self.node = None
        self.subscriber = None

    def laser_scan_callback(self, msg: LaserScan) -> None:
        """
        Callback function for receiving LaserScan messages.

        Args:
            msg: The received LaserScan message
        """
        self.current_scan = msg
        print(f"Received scan with {len(msg.ranges)} points")

    def update_plot(self, frame):
        """
        Update the plot with new laser scan data.
        Called by matplotlib animation.
        """
        # Spin the node to process callbacks
        if self.node is not None:
            self.node.spin_once()

        # Update the plot if we have data
        if self.current_scan is not None:
            # Calculate angles for each range point
            angles = np.arange(
                self.current_scan.angle_min,
                self.current_scan.angle_max + self.current_scan.angle_increment,
                self.current_scan.angle_increment
            )
            
            # Ensure we have the same number of angles as ranges
            angles = angles[:len(self.current_scan.ranges)]
            
            # Filter out invalid ranges (inf, nan, or out of bounds)
            valid_mask = np.array(self.current_scan.ranges) > 0
            
            valid_angles = angles[valid_mask]
            valid_ranges = np.array(self.current_scan.ranges)[valid_mask]
            
            # Handle intensities if available
            if len(self.current_scan.intensities) > 0:
                valid_intensities = np.array(self.current_scan.intensities)[valid_mask]
            else:
                valid_intensities = np.ones_like(valid_ranges)
            
            # Update scatter plot
            self.scatter.set_offsets(np.c_[valid_angles, valid_ranges])
            self.scatter.set_array(valid_intensities)

        return (self.scatter,)

    def run(self):
        """Start the visualizer and run the animation loop."""
        # Create RIX node
        self.node = Node("laser_scan_visualizer")
        if not self.node.ok():
            print("Error! Failed to initialize node.")
            return

        print(f"Node initialized successfully.")
        
        # Create subscriber
        self.subscriber = self.node.create_subscriber(
            LaserScan, self.topic, self.laser_scan_callback
        )
        if not self.subscriber.ok():
            print(f"Error! Failed to create subscriber to topic '{self.topic}'.")
            return

        print(f"Subscribed to topic '{self.topic}'.")
        print("Starting visualization... Close the plot window to exit.")

        # Create animation
        ani = FuncAnimation(
            self.fig, self.update_plot, interval=50, blit=True, cache_frame_data=False
        )

        try:
            plt.show()
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup node resources."""
        if self.node:
            self.node.shutdown()
            print("Node shutdown")


def main():
    # Parse command line arguments
    topic = "/laserscan"
    max_range = 10.0

    if len(sys.argv) > 1:
        topic = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            max_range = float(sys.argv[2])
        except ValueError:
            print(f"Invalid max_range: {sys.argv[2]}, using default: {max_range}")

    print(f"Laser Scan Visualizer")
    print(f"Subscribing to topic: {topic}")
    print(f"Fixed plot range: 0 to {max_range} meters")
    print("Press Ctrl+C or close the plot window to exit")
    print("-" * 50)

    # Create and run visualizer
    visualizer = LaserScanVisualizer(topic, max_range)
    visualizer.run()


if __name__ == "__main__":
    main()
