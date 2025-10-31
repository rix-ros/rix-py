import numpy as np
from scipy.spatial.transform import Rotation as R
from rix.sensor_msgs import JointState
import enum
from typing import Any


def origin_from_json(data: list[float]) -> np.ndarray:
    if data is None:
        return np.eye(4)

    T = np.eye(4)
    T[0:3, 3] = data[0:3]
    R_mat = R.from_euler("xyz", data[3:6]).as_matrix()
    T[0:3, 0:3] = R_mat
    return T


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
    def from_json(data: dict[str, Any] | None) -> "JointDynamics":
        if data is None:
            return JointDynamics()
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
    def from_json(data: dict[str, Any] | None) -> "JointLimits":
        if data is None:
            return JointLimits()
        lower = data.get("lower", 0.0)
        upper = data.get("upper", 0.0)
        effort = data.get("effort", 0.0)
        velocity = data.get("velocity", 0.0)
        return JointLimits(lower, upper, effort, velocity)


class JointMimic:
    def __init__(
        self,
        offset: float = 0.0,
        multiplier: float = 1.0,
        name: str = "",
        joint: "Joint | None" = None,
    ):
        self.offset = offset
        self.multiplier = multiplier
        self.name = name
        self.joint = joint

    @staticmethod
    def from_json(data: dict[str, Any] | None) -> "JointMimic":
        if data is None:
            return JointMimic()
        offset = data.get("offset", 0.0)
        multiplier = data.get("multiplier", 1.0)
        name = data.get("name", "")
        return JointMimic(offset, multiplier, name)


class JointSafety:
    def __init__(
        self,
        soft_lower_limit: float = 0.0,
        soft_upper_limit: float = 0.0,
        k_position: float = 0.0,
        k_velocity: float = 0.0,
    ):
        self.soft_lower_limit = soft_lower_limit
        self.soft_upper_limit = soft_upper_limit
        self.k_position = k_position
        self.k_velocity = k_velocity

    @staticmethod
    def from_json(data: dict[str, Any] | None) -> "JointSafety":
        if data is None:
            return JointSafety()

        soft_lower_limit = data.get("soft_lower_limit", 0.0)
        soft_upper_limit = data.get("soft_upper_limit", 0.0)
        k_position = data.get("k_position", 0.0)
        k_velocity = data.get("k_velocity", 0.0)
        return JointSafety(soft_lower_limit, soft_upper_limit, k_position, k_velocity)


class Joint:
    def __init__(
        self,
        name: str,
        parent: str,
        child: str,
        axis: np.ndarray,
        origin: np.ndarray,
        type: JointType,
        limits: JointLimits,
        dynamics: JointDynamics,
        mimic: JointMimic,
        safety: JointSafety,
    ):
        self.name = name
        self.parent = parent
        self.child = child
        self.axis = axis
        self.origin = origin
        self.type = type
        self.limits = limits
        self.dynamics = dynamics
        self.mimic = mimic
        self.safety = safety
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
    def from_json(data: dict[str, Any]) -> "Joint":
        name = data.get("name", "")
        parent = data.get("parent", "")
        child = data.get("child", "")
        axis = np.array(data.get("axis", [0.0, 0.0, 0.0]))
        origin = origin_from_json(data.get("origin", None))

        try:
            type = JointType(data.get("type", "UNKNOWN").upper())
        except ValueError:
            type = JointType.UNKNOWN

        limits = JointLimits.from_json(data.get("limits", None))
        dynamics = JointDynamics.from_json(data.get("dynamics", None))
        mimic = JointMimic.from_json(data.get("mimic", None))
        safety = JointSafety.from_json(data.get("safety", None))
        return Joint(
            name, parent, child, axis, origin, type, limits, dynamics, mimic, safety
        )
