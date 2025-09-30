from typing import Tuple
import numpy as np
from rix.rob.msg_util import (
    interpolate_transform,
    transform_to_matrix,
)
from rix.msg.geometry import TF, TransformStamped

class TransformBuffer:
    def __init__(self, duration: float = 0.1):
        self.duration = duration
        self.buffer: list[Tuple[float, np.ndarray]] = [] # Sorted list of (timestamp, transform matrix)

    def size(self) -> int:
        return len(self.buffer)
    
    def empty(self) -> bool:
        return len(self.buffer) == 0
    
    def clear(self):
        self.buffer.clear()

    def insert(self, timestamp: float, transform: np.ndarray):
        self.buffer.append((timestamp, transform))
        self.buffer.sort(key=lambda x: x[0])  # Keep buffer sorted by timestamp
        self._prune_old_entries(timestamp)

    def _prune_old_entries(self, current_time: float):
        while self.buffer and (current_time - self.buffer[0][0]) > self.duration:
            self.buffer.pop(0)

    def get(self, timestamp: float) -> np.ndarray | None:
        if self.empty():
            return None
        
        # Use binary search to find the closest timestamps
        low, high = 0, len(self.buffer) - 1
        while low <= high:
            mid = (low + high) // 2
            if self.buffer[mid][0] < timestamp:
                low = mid + 1
            elif self.buffer[mid][0] > timestamp:
                high = mid - 1
            else:
                return self.buffer[mid][1]  # Exact match
            
        # Now low is the index of the first element greater than timestamp
        # and high is the index of the last element less than timestamp
        if high < 0:
            return self.buffer[0][1]  # Return the earliest
        if low >= len(self.buffer):
            return self.buffer[-1][1]  # Return the latest
        # Interpolate between buffer[high] and buffer[low]
        t0, tf0 = self.buffer[high]
        t1, tf1 = self.buffer[low]
        return interpolate_transform(tf0, tf1, (timestamp - t0) / (t1 - t0))
        

class Frame:
    def __init__(self, name: str, parent: str | None = None):
        self.name = name
        self.parent = parent
        self.children: list[str] = []
        self.buffer = TransformBuffer()

class FrameGraph:
    def __init__(self, root: str, duration: float = 0.1):
        self.root = root
        self.duration = duration
        self.frames: dict[str, Frame] = {root: Frame(root)}

    def exists(self, name: str) -> bool:
        return name in self.frames
    
    def get_leaves(self) -> list[str]:
        return [name for name, frame in self.frames.items() if len(frame.children) == 0]
    
    def get_root(self) -> Frame:
        return self.frames[self.root]
    
    def find(self, name: str) -> Frame | None:
        return self.frames.get(name, None)
    
    def find_nearest_ancestor(self, frame_a: str, frame_b: str) -> str | None:
        ancestors_a: set[str] = set()
        current = self.find(frame_a)
        while current is not None:
            ancestors_a.add(current.name)
            if current.parent is None:
                break
            current = self.find(current.parent)
        
        current = self.find(frame_b)
        while current is not None:
            if current.name in ancestors_a:
                return current.name
            if current.parent is None:
                break
            current = self.find(current.parent)
        
        return None

    def update_from_transform(self, transform: TransformStamped) -> bool:
        parent = transform.header.frame_id
        child = transform.child_frame_id
        timestamp = transform.header.stamp.sec + transform.header.stamp.nsec * 1e-9
        matrix = transform_to_matrix(transform.transform)

        if parent not in self.frames:
            self.frames[parent] = Frame(parent)
        if child not in self.frames:
            self.frames[child] = Frame(child, parent)
            self.frames[parent].children.append(child)

        self.frames[child].buffer.insert(timestamp, matrix)
        return True

    def update_from_tf(self, tf: TF) -> bool:
        for transform in tf.transforms:
            if not self.update_from_transform(transform):
                return False
        return True
    
    def get_transform(self, target_frame: str, source_frame: str, time: float) -> np.ndarray | None:
        if not self.exists(target_frame) or not self.exists(source_frame):
            return None
        
        if target_frame == source_frame:
            return np.eye(4)

        ancestor = self.find_nearest_ancestor(target_frame, source_frame)
        if ancestor is None:
            return None
        
        # chain transforms from target to ancestor
        target_to_ancestor = np.eye(4)
        current = self.find(target_frame)
        if current is None:
            return None
        while current.name != ancestor:
            parent = self.get_parent(current)
            if parent is None:
                return None
            tform = current.buffer.get(time)
            if tform is None:
                return None
            target_to_ancestor = tform @ target_to_ancestor
            current = parent

        # chain transforms from source to ancestor
        source_to_ancestor = np.eye(4)
        current = self.find(source_frame)
        if current is None:
            return None
        while current.name != ancestor:
            parent = self.get_parent(current)
            if parent is None:
                return None
            tform = current.buffer.get(time)
            if tform is None:
                return None
            source_to_ancestor = tform @ source_to_ancestor
            current = parent

        ancestor_to_source = np.linalg.inv(source_to_ancestor)
        target_to_source = ancestor_to_source @ target_to_ancestor
        return target_to_source
    
    def get_parent(self, frame: Frame) -> Frame | None:
        if frame.parent is None:
            return None
        return self.frames.get(frame.parent, None)
    
    def get_children(self, frame: Frame) -> list[Frame]:
        return [self.frames[child] for child in frame.children if child in self.frames]
    