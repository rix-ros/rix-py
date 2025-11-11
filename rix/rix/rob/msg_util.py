from rix.geometry_msgs import Transform, Vector3, Quaternion
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.spatial.transform import Slerp


def transform_to_matrix(transform: Transform) -> np.ndarray:
    """Convert a Transform message to a 4x4 transformation matrix."""
    translation = transform.translation
    rotation = transform.rotation
    rot = R.from_quat([rotation.x, rotation.y, rotation.z, rotation.w])
    matrix = np.eye(4)
    matrix[0:3, 0:3] = rot.as_matrix()
    matrix[0:3, 3] = [translation.x, translation.y, translation.z]
    return matrix


def matrix_to_transform(matrix: np.ndarray) -> Transform:
    """Convert a 4x4 transformation matrix to a Transform message."""
    if matrix.shape != (4, 4):
        raise ValueError("Input matrix must be 4x4.")

    rot = R.from_matrix(matrix[0:3, 0:3])
    quat = rot.as_quat()  # Returns [x, y, z, w]

    transform = Transform()
    transform.translation.x = matrix[0, 3]
    transform.translation.y = matrix[1, 3]
    transform.translation.z = matrix[2, 3]
    transform.rotation.x = quat[0]
    transform.rotation.y = quat[1]
    transform.rotation.z = quat[2]
    transform.rotation.w = quat[3]
    return transform


def quat_msg_to_array(quat: Quaternion) -> np.ndarray:
    """Convert a Quaternion message to a numpy array [x, y, z, w]."""
    return np.array([quat.x, quat.y, quat.z, quat.w])


def array_to_quat_msg(arr: np.ndarray) -> Quaternion:
    """Convert a numpy array [x, y, z, w] to a Quaternion message."""
    if arr.shape != (4,):
        raise ValueError("Input array must be of shape (4,).")
    quat = Quaternion()
    quat.x = arr[0]
    quat.y = arr[1]
    quat.z = arr[2]
    quat.w = arr[3]
    return quat


def vec3_msg_to_array(vec: Vector3) -> np.ndarray:
    """Convert a Vector3 message to a numpy array [x, y, z]."""
    return np.array([vec.x, vec.y, vec.z])


def array_to_vec3_msg(arr: np.ndarray) -> Vector3:
    """Convert a numpy array [x, y, z] to a Vector3 message."""
    if arr.shape != (3,):
        raise ValueError("Input array must be of shape (3,).")
    vec = Vector3()
    vec.x = arr[0]
    vec.y = arr[1]
    vec.z = arr[2]
    return vec


def interpolate_vec3_msg(v1: Vector3, v2: Vector3, t: float) -> Vector3:
    """Linearly interpolate between two Vector3 messages."""
    arr1 = vec3_msg_to_array(v1)
    arr2 = vec3_msg_to_array(v2)
    interp_arr = (1 - t) * arr1 + t * arr2
    return array_to_vec3_msg(interp_arr)


def interpolate_vec3(v1: np.ndarray, v2: np.ndarray, t: float) -> np.ndarray:
    """Linearly interpolate between two numpy arrays representing vectors."""
    if v1.shape != (3,) or v2.shape != (3,):
        raise ValueError("Input arrays must be of shape (3,).")
    return (1 - t) * v1 + t * v2


def interpolate_quat_msg(q1: Quaternion, q2: Quaternion, t: float) -> Quaternion:
    """Spherically interpolate between two Quaternion messages."""
    arr1 = quat_msg_to_array(q1)
    arr2 = quat_msg_to_array(q2)
    rot1 = R.from_quat(arr1)
    rot2 = R.from_quat(arr2)
    slerp_rot = R.slerp(0, 1, [rot1, rot2])(t)
    interp_arr = slerp_rot.as_quat()
    return array_to_quat_msg(interp_arr)


def interpolate_quat(q1: np.ndarray, q2: np.ndarray, t: float) -> np.ndarray:
    """Spherically interpolate between two numpy arrays representing quaternions."""
    if q1.shape != (4,) or q2.shape != (4,):
        raise ValueError("Input arrays must be of shape (4,).")
    rot1 = R.from_quat(q1)
    rot2 = R.from_quat(q2)
    slerp_rot = R.slerp(0, 1, [rot1, rot2])(t)
    return slerp_rot.as_quat()


def interpolate_transform_msg(t1: Transform, t2: Transform, t: float) -> Transform:
    """Interpolate between two Transform messages."""
    interp_translation = interpolate_vec3_msg(t1.translation, t2.translation, t)
    interp_rotation = interpolate_quat_msg(t1.rotation, t2.rotation, t)
    interp_transform = Transform()
    interp_transform.translation = interp_translation
    interp_transform.rotation = interp_rotation
    return interp_transform


def interpolate_transform(m1: np.ndarray, m2: np.ndarray, t: float) -> np.ndarray:
    """Interpolate between two 4x4 transformation matrices."""
    if m1.shape != (4, 4) or m2.shape != (4, 4):
        raise ValueError("Input matrices must be of shape (4, 4).")

    trans1 = m1[0:3, 3]
    trans2 = m2[0:3, 3]
    interp_trans = interpolate_vec3(trans1, trans2, t)

    rot1 = R.from_matrix(m1[0:3, 0:3])
    rot2 = R.from_matrix(m2[0:3, 0:3])
    # interp_rot = R.slerp(0, 1, [rot1, rot2])(t)
    slerp = Slerp([0, 1], R.concatenate([rot1, rot2]))
    interp_rot = slerp(t)

    interp_matrix = np.eye(4)
    interp_matrix[0:3, 3] = interp_trans
    interp_matrix[0:3, 0:3] = interp_rot.as_matrix()
    return interp_matrix
