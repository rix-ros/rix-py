from enum import Enum
import numpy as np
from typing import Any
from rix.rob.joint import origin_from_json


class GeometryType(Enum):
    SPHERE = "SPHERE"
    BOX = "BOX"
    CYLINDER = "CYLINDER"
    MESH = "MESH"


class Geometry:
    def __init__(self, type: GeometryType):
        self.type = type

    @staticmethod
    def from_json(data: dict[str, Any] | None) -> "Geometry":
        """
        Create a Geometry object from a JSON dictionary. We make assumptions
        that PyLance doesn't like but we know it is safe because of the schema.
        """

        if data is None:
            raise ValueError("Geometry data is None")

        geom_type = GeometryType[data["type"].upper()]

        if geom_type == GeometryType.SPHERE:
            radius = data.get("radius", 0.0)
            return Sphere(radius)
        elif geom_type == GeometryType.BOX:
            size = np.array(data.get("size", None))
            return Box(size)
        elif geom_type == GeometryType.CYLINDER:
            radius = data.get("radius", 0.0)
            length = data.get("length", 0.0)
            return Cylinder(radius, length)
        elif geom_type == GeometryType.MESH:
            scale = np.array(data.get("scale", [1, 1, 1]))
            return Mesh(data["filename"], scale)
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
    def from_json(data: dict[str, Any] | None) -> "Material":
        if data is None:
            return Material("", np.array([0.8, 0.8, 0.8, 1.0]))

        name = data.get("name", "")
        color = data.get("color", [0.8, 0.8, 0.8, 1.0])
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
    def from_json(data: dict[str, Any] | None) -> "Inertial":
        if data is None:
            return Inertial(np.eye(4), 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 1.0)

        origin = origin_from_json(data.get("origin", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]))
        mass = data.get("mass", 0.0)
        ixx = data.get("ixx", 0.0)
        ixy = data.get("ixy", 0.0)
        ixz = data.get("ixz", 0.0)
        iyy = data.get("iyy", 0.0)
        iyz = data.get("iyz", 0.0)
        izz = data.get("izz", 0.0)
        return Inertial(origin, mass, ixx, ixy, ixz, iyy, iyz, izz)


class Visual:
    def __init__(self, origin: np.ndarray, geometry: Geometry, material: Material):
        self.origin = origin  # origin should be a numpy array of shape (4,4) representing a transformation matrix
        self.geometry = geometry
        self.material = material

    @staticmethod
    def from_json(data: dict[str, Any]) -> "Visual":
        origin = origin_from_json(data.get("origin", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]))
        geometry = Geometry.from_json(data.get("geometry", None))
        material = Material.from_json(data.get("material", None))
        return Visual(origin, geometry, material)


class Collision:
    def __init__(self, origin: np.ndarray, geometry: Geometry):
        self.origin = origin  # origin should be a numpy array of shape (4,4) representing a transformation matrix
        self.geometry = geometry

    @staticmethod
    def from_json(data: dict[str, Any]) -> "Collision":
        origin = origin_from_json(data.get("origin", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]))
        geometry = Geometry.from_json(data.get("geometry", None))
        return Collision(origin, geometry)


class Link:
    def __init__(
        self,
        name: str,
        visuals: list[Visual],
        collisions: list[Collision],
        inertial: Inertial,
    ):
        self.visuals = visuals
        self.collisions = collisions
        self.inertial = inertial
        self.name = name
        self.parent = ""
        self.children: list[str] = []

    @staticmethod
    def from_json(data: dict[str, Any]) -> "Link":
        name = data.get("name", "")
        visuals = [Visual.from_json(v) for v in data.get("visuals", [])]
        collisions = [Collision.from_json(c) for c in data.get("collisions", [])]
        inertial = Inertial.from_json(data.get("inertial", None))
        return Link(name, visuals, collisions, inertial)

    def is_root(self) -> bool:
        return self.parent == ""

    def is_end_effector(self) -> bool:
        return len(self.children) == 0
