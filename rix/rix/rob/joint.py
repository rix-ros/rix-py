import numpy as np
from scipy.spatial.transform import Rotation as R
from rix.msg.sensor import JointState
import enum
from rix.rob.math_parser import (
    parse_origin,
    parse_vector3,
    parse_number_or_expression,
    parse_vector4,
)


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
    def from_json(
        data: dict[str, any] | None, constants: dict[str, float]
    ) -> "JointDynamics":
        if data is None:
            return JointDynamics()
        damping = parse_number_or_expression(data.get("damping", 0.0), constants)
        friction = parse_number_or_expression(data.get("friction", 0.0), constants)
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
    def from_json(
        data: dict[str, any] | None, constants: dict[str, float]
    ) -> "JointLimits":
        if data is None:
            return JointLimits()
        lower = parse_number_or_expression(data.get("lower", 0.0), constants)
        upper = parse_number_or_expression(data.get("upper", 0.0), constants)
        effort = parse_number_or_expression(data.get("effort", 0.0), constants)
        velocity = parse_number_or_expression(data.get("velocity", 0.0), constants)
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
    def from_json(
        data: dict[str, any] | None, constants: dict[str, float]
    ) -> "JointMimic":
        if data is None:
            return JointMimic()
        offset = parse_number_or_expression(data.get("offset", 0.0), constants)
        multiplier = parse_number_or_expression(data.get("multiplier", 1.0), constants)
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
    def from_json(
        data: dict[str, any] | None, constants: dict[str, float]
    ) -> "JointSafety":
        if data is None:
            return JointSafety()

        soft_lower_limit = parse_number_or_expression(
            data.get("soft_lower_limit", 0.0), constants
        )
        soft_upper_limit = parse_number_or_expression(
            data.get("soft_upper_limit", 0.0), constants
        )
        k_position = parse_number_or_expression(data.get("k_position", 0.0), constants)
        k_velocity = parse_number_or_expression(data.get("k_velocity", 0.0), constants)
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
    def from_json(data: dict[str, any], constants: dict[str, float]) -> "Joint":
        name = data.get("name", "")
        parent = data.get("parent", "")
        child = data.get("child", "")
        axis = parse_vector3(data.get("axis", None), constants)
        origin = parse_origin(data.get("origin", None), constants)
        type_str = data.get("type", "UNKNOWN").upper()
        try:
            type = JointType(type_str)
        except ValueError:
            type = JointType.UNKNOWN
        limits = JointLimits.from_json(data.get("limits", None), constants)
        dynamics = JointDynamics.from_json(data.get("dynamics", None), constants)
        mimic = JointMimic.from_json(data.get("mimic", None), constants)
        safety = JointSafety.from_json(data.get("safety", None), constants)
        return Joint(
            name, parent, child, axis, origin, type, limits, dynamics, mimic, safety
        )
