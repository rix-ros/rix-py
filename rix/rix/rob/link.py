import json
from enum import Enum
import numpy as np
from rix.rob.joint import convert_json_origin


class GeometryType(Enum):
    SPHERE = "SPHERE"
    BOX = "BOX"
    CYLINDER = "CYLINDER"
    MESH = "MESH"


class Geometry:
    def __init__(self, type: GeometryType):
        self.type = type

    @staticmethod
    def from_json(data: dict) -> "Geometry":
        if data is None:
            raise ValueError("Geometry data is None")
        geom_type = GeometryType[data["type"].upper()]
        if geom_type == GeometryType.SPHERE:
            return Sphere(radius=data["radius"])
        elif geom_type == GeometryType.BOX:
            return Box(size=np.array(data["size"]))
        elif geom_type == GeometryType.CYLINDER:
            return Cylinder(radius=data["radius"], length=data["length"])
        elif geom_type == GeometryType.MESH:
            return Mesh(
                filename=data["filename"], scale=np.array(data.get("scale", [1, 1, 1]))
            )
        else:
            raise ValueError(f"Unknown geometry type: {data['type']}")


class Sphere(Geometry):
    def __init__(self, radius: float):
        super().__init__(GeometryType.SPHERE)
        self.radius = radius


class Box(Geometry):
    def __init__(self, size: np.ndarray):
        super().__init__(GeometryType.BOX)
        self.size = size  # size should be a numpy array of shape (3,)


class Cylinder(Geometry):
    def __init__(self, radius: float, length: float):
        super().__init__(GeometryType.CYLINDER)
        self.radius = radius
        self.length = length


class Mesh(Geometry):
    def __init__(self, filename: str, scale: np.ndarray):
        super().__init__(GeometryType.MESH)
        self.filename = filename
        self.scale = scale  # scale should be a numpy array of shape (3,)


class Material:
    def __init__(self, name: str, color: np.ndarray, texture_filename: str = ""):
        self.name = name
        self.color = color
        self.texture_filename = texture_filename

    @staticmethod
    def from_json(data: dict) -> "Material":
        if data is None:
            return Material("default", np.array([0.8, 0.8, 0.8, 1.0]), "")
        name = data.get("name", "")
        color = np.array(data.get("color", [0.8, 0.8, 0.8, 1.0]))
        texture_filename = data.get("texture_filename", "")
        return Material(name, color, texture_filename)


class Inertial:
    def __init__(
        self,
        origin: np.ndarray,
        mass: float,
        ixx: float,
        ixy: float,
        ixz: float,
        iyy: float,
        iyz: float,
        izz: float,
    ):
        self.origin = origin  # origin should be a numpy array of shape (4,4) representing a transformation matrix
        self.mass = mass
        self.ixx = ixx
        self.ixy = ixy
        self.ixz = ixz
        self.iyy = iyy
        self.iyz = iyz
        self.izz = izz

    @staticmethod
    def from_json(data: dict) -> "Inertial":
        if data is None:
            return Inertial(np.eye(4), 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 1.0)
        origin = convert_json_origin(data.get("origin", None))
        mass = data.get("mass", 0.0)
        inertia = data.get("inertia", {})
        ixx = inertia.get("ixx", 0.0)
        ixy = inertia.get("ixy", 0.0)
        ixz = inertia.get("ixz", 0.0)
        iyy = inertia.get("iyy", 0.0)
        iyz = inertia.get("iyz", 0.0)
        izz = inertia.get("izz", 0.0)
        return Inertial(origin, mass, ixx, ixy, ixz, iyy, iyz, izz)


class Visual:
    def __init__(self, origin: np.ndarray, geometry: Geometry, material: Material):
        self.origin = origin  # origin should be a numpy array of shape (4,4) representing a transformation matrix
        self.geometry = geometry
        self.material = material

    @staticmethod
    def from_json(data: dict) -> "Visual":
        origin = convert_json_origin(data.get("origin", None))
        geometry = Geometry.from_json(data.get("geometry", None))
        material = Material.from_json(data.get("material", None))
        return Visual(origin, geometry, material)


class Collision:
    def __init__(self, origin: np.ndarray, geometry: Geometry):
        self.origin = origin  # origin should be a numpy array of shape (4,4) representing a transformation matrix
        self.geometry = geometry

    @staticmethod
    def from_json(data: dict) -> "Collision":
        origin = convert_json_origin(data.get("origin", None))
        geometry = Geometry.from_json(data.get("geometry", None))
        return Collision(origin, geometry)


class Link:
    def __init__(
        self,
        visuals: list[Visual] | None = None,
        collisions: list[Collision] | None = None,
        inertial: Inertial | None = None,
        name: str = "",
        parent: str = "",
        children: list[str] | None = None,
    ):
        self.visuals = visuals if visuals is not None else []
        self.collisions = collisions if collisions is not None else []
        self.inertial = inertial
        self.name = name
        self.parent = parent
        self.children = children if children is not None else []

    @staticmethod
    def from_json(data: dict) -> "Link":
        visuals = [Visual.from_json(v) for v in data.get("visuals", [])]
        collisions = [Collision.from_json(c) for c in data.get("collisions", [])]
        inertial = Inertial.from_json(data["inertial"]) if "inertial" in data else None
        name = data.get("name", "")
        return Link(visuals, collisions, inertial, name)

    def is_root(self) -> bool:
        return self.parent == ""

    def is_end_effector(self) -> bool:
        return len(self.children) == 0
