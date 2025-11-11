import numpy as np
import json
from scipy.spatial.transform import Rotation as R
from time import time_ns
from rix.rob.joint import Joint
from rix.rob.link import Link, Material
from rix.rob.msg_util import (
    matrix_to_transform,
)
from rix.geometry_msgs import TF, TransformStamped
from rix.sensor_msgs import JS
from rix.std_msgs import Time
import os

HOME = os.path.expanduser("~")


class RobotModel:
    def __init__(self, filename: str):
        self.links: dict[str, Link] = {}
        self.joints: dict[str, Joint] = {}
        self.root: Link | None = None
        self.world_to_root: np.ndarray = np.eye(4)
        self.from_json(filename)

    def from_model(self, name: str) -> None:
        filename = os.path.join(HOME, ".rix", "jrdf", "models", name, "model.json")
        self.from_json(filename)

    def from_json(self, filename: str) -> None:
        with open(filename, "r") as f:
            data = json.load(f)

        # Parse links
        for link_data in data.get("links", []):
            link = Link.from_json(link_data)
            self.links[link.name] = link

        # Parse joints
        for joint_data in data.get("joints", []):
            joint = Joint.from_json(joint_data)
            self.joints[joint.name] = joint

        # Resolve mimic references
        for joint in self.joints.values():
            if joint.is_mimic():
                mimic_name = joint.mimic.name
                if mimic_name in self.joints:
                    joint.mimic.joint = self.joints[mimic_name]
                else:
                    raise ValueError(
                        f"Mimic joint '{mimic_name}' not found for joint '{joint.name}'"
                    )

        # Resolve Link parent-child relationships
        for joint in self.joints.values():
            if joint.parent in self.links and joint.child in self.links:
                self.links[joint.parent].children.append(joint.name)
                self.links[joint.child].parent = joint.name
            else:
                raise ValueError(
                    f"Joint '{joint.name}' has invalid parent '{joint.parent}' or child '{joint.child}' link."
                )

        # Identify root link
        for link in self.links.values():
            if link.is_root():
                self.root = link
                break

        if self.root is None:
            raise ValueError("No root link found in the robot model.")

    def get_joint_states(self) -> JS:
        js = JS()
        for joint in self.joints.values():
            js.joint_states.append(joint.get_state())
        return js

    def get_transforms(self) -> TF:
        if self.root is None:
            raise ValueError("Robot model has no root link defined.")

        tf = TF()
        stamp = Time()
        total_nanoseconds = time_ns()
        stamp.sec = total_nanoseconds // 1_000_000_000
        stamp.nsec = total_nanoseconds % 1_000_000_000
        tf.transforms = [TransformStamped() for _ in range(len(self.joints) + 1)]

        tf.transforms[0].header.stamp = stamp
        tf.transforms[0].header.seq = 0
        tf.transforms[0].header.frame_id = "world"
        tf.transforms[0].child_frame_id = self.root.name
        tf.transforms[0].transform = matrix_to_transform(self.world_to_root)

        index = 1
        link_stack = [self.root]
        while len(link_stack) > 0:
            current_link = link_stack.pop()
            for child_joint in current_link.children:
                joint = self.joints[child_joint]
                child_link = self.links[joint.child]

                tf.transforms[index].header.stamp = stamp
                tf.transforms[index].header.seq = index
                tf.transforms[index].header.frame_id = current_link.name
                tf.transforms[index].child_frame_id = child_link.name

                tf.transforms[index].transform = matrix_to_transform(
                    joint.origin @ joint.transform()
                )
                index += 1

                link_stack.append(child_link)
        return tf

    def get_static_transforms(self) -> TF:
        if self.root is None:
            raise ValueError("Robot model has no root link defined.")

        tf = TF()
        stamp = Time()
        total_nanoseconds = time_ns()
        stamp.sec = total_nanoseconds // 1_000_000_000
        stamp.nsec = total_nanoseconds % 1_000_000_000
        tf.transforms = []

        i = 0
        for link in self.links.values():
            tf.transforms.append(TransformStamped())
            tf.transforms[i].header.stamp = stamp
            tf.transforms[i].header.seq = i
            tf.transforms[i].header.frame_id = link.name
            tf.transforms[i].child_frame_id = link.name + "/inertial"
            tform = link.inertial.origin if link.inertial else np.eye(4)
            tf.transforms[i].transform = matrix_to_transform(tform)
            i += 1

            j = 0
            for visual in link.visuals:
                tf.transforms.append(TransformStamped())
                tf.transforms[i].header.stamp = stamp
                tf.transforms[i].header.seq = i
                tf.transforms[i].header.frame_id = link.name
                tf.transforms[i].child_frame_id = link.name + "/visual_" + str(j)
                tform = visual.origin
                tf.transforms[i].transform = matrix_to_transform(tform)
                i += 1
                j += 1

            j = 0
            for collision in link.collisions:
                tf.transforms.append(TransformStamped())
                tf.transforms[i].header.stamp = stamp
                tf.transforms[i].header.seq = i
                tf.transforms[i].header.frame_id = link.name
                tf.transforms[i].child_frame_id = link.name + "/collision_" + str(j)
                tform = collision.origin
                tf.transforms[i].transform = matrix_to_transform(tform)
                i += 1
                j += 1
        return tf

    def set_joint_states(self, js: JS) -> None:
        for state in js.joint_states:
            if state.name in self.joints:
                self.joints[state.name].set_state(state)
            else:
                raise ValueError(f"Joint '{state.name}' not found in robot model.")
