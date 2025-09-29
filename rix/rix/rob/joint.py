import numpy as np
from scipy.spatial.transform import Rotation as R
from rix.msg.sensor import JointState
import enum

def convert_json_origin(origin: dict) -> np.ndarray:
    """Convert a JSON origin dictionary to a 4x4 transformation matrix."""
    xyz = origin.get("xyz", [0.0, 0.0, 0.0])
    rpy = origin.get("rpy", [0.0, 0.0, 0.0])
    translation = np.array(xyz)
    rotation = R.from_euler("xyz", rpy).as_matrix()
    matrix = np.eye(4)
    matrix[0:3, 0:3] = rotation
    matrix[0:3, 3] = translation
    return matrix

class JointType(enum.Enum):
    UNKNOWN = ""
    FIXED = "FIXED"
    CONTINUOUS = "CONTINUOUS"
    REVOLUTE = "REVOLUTE"
    PRISMATIC = "PRISMATIC"


class JointDynamics:
    def __init__(self, damping: float = 0.0, friction: float = 0.0):
        self.damping = damping
        self.friction = friction

    @staticmethod
    def from_json(data: dict) -> "JointDynamics":
        damping = data.get("damping", 0.0)
        friction = data.get("friction", 0.0)
        return JointDynamics(damping, friction)


class JointLimits:
    def __init__(
        self,
        lower: float = 0.0,
        upper: float = 0.0,
        effort: float = 0.0,
        velocity: float = 0.0,
    ):
        self.lower = lower
        self.upper = upper
        self.effort = effort
        self.velocity = velocity

    @staticmethod
    def from_json(data: dict) -> "JointLimits":
        lower = data.get("lower", 0.0)
        upper = data.get("upper", 0.0)
        effort = data.get("effort", 0.0)
        velocity = data.get("velocity", 0.0)
        return JointLimits(lower, upper, effort, velocity)


class JointMimic:
    def __init__(
        self, offset: float = 0.0, multiplier: float = 1.0, name: str = "", joint: "Joint | None" = None
    ):
        self.offset = offset
        self.multiplier = multiplier
        self.name = name
        self.joint = joint

    @staticmethod
    def from_json(data: dict) -> "JointMimic":
        offset = data.get("offset", 0.0)
        multiplier = data.get("multiplier", 1.0)
        # Note: 'joint' reference will be resolved after all joints are created
        return JointMimic(offset, multiplier, None)


class Joint:
    def __init__(
        self,
        axis: np.ndarray,
        origin: np.ndarray,
        type: JointType,
        limits: JointLimits,
        dynamics: JointDynamics,
        mimic: JointMimic,
        name: str,
        parent: str,
        child: str,
    ):
        self.axis = axis
        self.origin = origin
        self.type = type
        self.limits = limits
        self.dynamics = dynamics
        self.mimic = mimic
        self.name = name
        self.parent = parent
        self.child = child
        self.position = 0.0
        self.velocity = 0.0
        self.effort = 0.0

    def is_mimic(self) -> bool:
        return self.mimic.name != ""

    def in_bounds(self, position: float) -> bool:
        return self.limits.lower <= position <= self.limits.upper

    def clamp(self, position: float) -> float:
        if self.type == JointType.CONTINUOUS:
            position = (position + np.pi) % (2 * np.pi) - np.pi
        return max(self.limits.lower, min(self.limits.upper, position))

    def transform(self) -> np.ndarray:
        T = np.eye(4)
        if self.type == JointType.FIXED:
            pass
        elif self.type == JointType.REVOLUTE or self.type == JointType.CONTINUOUS:
            R_mat = R.from_rotvec(self.axis * self.position).as_matrix()
            T[:3, :3] = R_mat
        elif self.type == JointType.PRISMATIC:
            T[:3, 3] = self.axis * self.position
        else:
            raise ValueError("Unknown joint type")
        return T

    def get_state(self) -> JointState:
        state = JointState()
        state.name = self.name
        state.position = self.position
        state.velocity = self.velocity
        state.effort = self.effort
        return state

    def set_state(self, state: JointState) -> None:
        self.position = state.position
        self.velocity = state.velocity
        self.effort = state.effort

    @staticmethod
    def from_json(data: dict) -> "Joint":
        axis = np.array(data.get("axis", [1.0, 0.0, 0.0]))
        origin = convert_json_origin(data.get("origin", {}))
        type_str = data.get("type", "UNKNOWN").upper()
        try:
            type = JointType(type_str)
        except ValueError:
            type = JointType.UNKNOWN
        limits = JointLimits.from_json(data.get("limits", {}))
        dynamics = JointDynamics.from_json(data.get("dynamics", {}))
        mimic = JointMimic.from_json(data.get("mimic", {}))
        name = data.get("name", "")
        parent = data.get("parent", "")
        child = data.get("child", "")
        return Joint(axis, origin, type, limits, dynamics, mimic, name, parent, child)
    

