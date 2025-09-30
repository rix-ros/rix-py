import numpy as np
from scipy.spatial.transform import Rotation as R
from rix.core import Node
from rix.msg.geometry import TF, Point, Pose, Quaternion
from rix.msg.sensor import PointCloud
from rix.tf.frame_graph import FrameGraph


class TransformListener:
    def __init__(self, node: Node, duration: float = 0.1):
        self.node = node
        self.sub = node.create_subscriber(TF, "/tf", self.tf_callback)
        self.frame_graph = FrameGraph("world", duration)

    def tf_callback(self, msg: TF) -> None:
        self.frame_graph.update_from_tf(msg)

    def get_transform(
        self, target_frame: str, source_frame: str, time: float
    ) -> np.ndarray | None:
        return self.frame_graph.get_transform(target_frame, source_frame, time)

    def transform_point(
        self, target_frame: str, source_frame: str, point: Point, time: float
    ) -> Point | None:
        transform = self.get_transform(target_frame, source_frame, time)
        if transform is None:
            return None
        point_homogeneous = np.array([point.x, point.y, point.z, 1.0])
        transformed_point = transform @ point_homogeneous
        point = Point()
        point.x = transformed_point[0]
        point.y = transformed_point[1]
        point.z = transformed_point[2]
        return point

    def transform_pose(
        self, target_frame: str, source_frame: str, pose: Pose, time: float
    ) -> Pose | None:
        transform = self.get_transform(target_frame, source_frame, time)
        if transform is None:
            return None
        pose_matrix = np.eye(4)
        pose_matrix[0:3, 3] = [pose.position.x, pose.position.y, pose.position.z]
        rot = R.from_quat(
            [
                pose.orientation.x,
                pose.orientation.y,
                pose.orientation.z,
                pose.orientation.w,
            ]
        )
        pose_matrix[0:3, 0:3] = rot.as_matrix()
        transformed_matrix = transform @ pose_matrix
        transformed_pose = Pose()
        transformed_pose.position.x = transformed_matrix[0, 3]
        transformed_pose.position.y = transformed_matrix[1, 3]
        transformed_pose.position.z = transformed_matrix[2, 3]
        rot_transformed = R.from_matrix(transformed_matrix[0:3, 0:3])
        quat = rot_transformed.as_quat()  # Returns [x, y, z, w]
        transformed_pose.orientation.x = quat[0]
        transformed_pose.orientation.y = quat[1]
        transformed_pose.orientation.z = quat[2]
        transformed_pose.orientation.w = quat[3]
        return transformed_pose

    def transform_quat(
        self, target_frame: str, source_frame: str, quat: Quaternion, time: float
    ) -> Quaternion | None:
        transform = self.get_transform(target_frame, source_frame, time)
        if transform is None:
            return None
        rot = R.from_quat([quat.x, quat.y, quat.z, quat.w])
        rot_matrix = rot.as_matrix()
        transform_rot = transform[0:3, 0:3]
        transformed_rot = transform_rot @ rot_matrix
        rot_transformed = R.from_matrix(transformed_rot)
        quat_transformed = rot_transformed.as_quat()  # Returns [x, y, z, w]
        transformed_quat = Quaternion()
        transformed_quat.x = quat_transformed[0]
        transformed_quat.y = quat_transformed[1]
        transformed_quat.z = quat_transformed[2]
        transformed_quat.w = quat_transformed[3]
        return transformed_quat

    def transform_point_cloud(
        self, target_frame: str, source_frame: str, cloud: PointCloud, time: float
    ) -> PointCloud | None:
        transform = self.get_transform(target_frame, source_frame, time)
        if transform is None:
            return None
        transformed_cloud = PointCloud()
        transformed_cloud.header = cloud.header
        for point in cloud.points:
            transformed_point = self.transform_point(
                target_frame, source_frame, point, time
            )
            if transformed_point is not None:
                transformed_cloud.points.append(transformed_point)
        return transformed_cloud
