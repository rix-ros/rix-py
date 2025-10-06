import urdf_parser_py.urdf as urdf
from typing import Any, Tuple
import os


class URDFConverter:
    def __init__(self):
        pass

    def convert(
        self, urdf_path: str, desc_dir: str | None = None
    ) -> Tuple[dict[str, Any], dict[str, str]]:
        # desc_dir is the actual directory containing the files specified in the urdf as package://<path>
        # To resolve the assets specified in the URDF to actual files, we need to remove "package://<base_dir>/" and
        # append the proceeding string to desc_dir

        jrdf: dict[str, Any] = {}  # The resulting JRDF dictionary
        assets: dict[str, str] = {}  # A mapping of valid asset filenames to their paths

        # Load assets from desc_dir
        if desc_dir is not None:
            assets = self._load_assets(desc_dir)

        # Load URDF file
        robot = urdf.URDF.from_xml_file(urdf_path)

        # Convert robot name
        jrdf["name"] = robot.name if robot.name else "unnamed_robot"

        # Convert links
        jrdf["links"] = [self._convert_link(link, assets) for link in robot.links]

        # Convert joints
        jrdf["joints"] = [self._convert_joint(joint) for joint in robot.joints]

        return jrdf, assets

    def _load_assets(self, asset_dir: str) -> dict[str, str]:
        if not os.path.isdir(asset_dir):
            raise ValueError(f"Asset directory '{asset_dir}' is invalid.")

        assets: dict[str, str] = {}
        for root, dirs, files in os.walk(asset_dir):
            for file in files:
                assets[os.path.join(root, file)] = os.path.relpath(
                    os.path.join(root, file), asset_dir
                )
            for dir in dirs:
                assets.update(self._load_assets(os.path.join(root, dir)))
        return assets

    def _resolve_asset(self, urdf_asset: str, assets: dict[str, str]) -> str:
        if urdf_asset.startswith("package://"):
            path_parts = urdf_asset[len("package://") :].split("/", 1)
            if len(path_parts) != 2:
                raise ValueError(f"Invalid package URI: {urdf_asset}")
            asset_path = path_parts[1]
            for asset, rel_path in assets.items():
                if asset.endswith(asset_path):
                    return rel_path
            raise ValueError(f"Asset '{asset_path}' not found in provided assets.")
        else:
            raise ValueError(f"Unsupported asset path format: {urdf_asset}")

    def _convert_material(
        self, urdf_material: urdf.Material, assets: dict[str, str]
    ) -> dict[str, Any]:
        if urdf_material.color is None and urdf_material.texture is None:
            raise ValueError("Material must have either color or texture defined.")
        material: dict[str, Any] = {}
        if urdf_material.color is not None:
            material["color"] = urdf_material.color.rgba
        elif (
            urdf_material.texture is not None
            and urdf_material.texture.filename is not None
        ):
            material["filename"] = self._resolve_asset(
                urdf_material.texture.filename, assets
            )
        return material

    def _convert_box(self, urdf_box: urdf.Box) -> dict[str, Any]:
        if urdf_box.size is None or len(urdf_box.size) != 3:
            raise ValueError("Box size must be a list of three numbers.")
        return {"size": urdf_box.size}

    def _convert_cylinder(self, urdf_cylinder: urdf.Cylinder) -> dict[str, Any]:
        if urdf_cylinder.radius is None or urdf_cylinder.length is None:
            raise ValueError("Cylinder must have both radius and length defined.")
        return {"radius": urdf_cylinder.radius, "length": urdf_cylinder.length}

    def _convert_sphere(self, urdf_sphere: urdf.Sphere) -> dict[str, Any]:
        if urdf_sphere.radius is None:
            raise ValueError("Sphere must have radius defined.")
        return {"radius": urdf_sphere.radius}

    def _convert_mesh(
        self, urdf_mesh: urdf.Mesh, assets: dict[str, str]
    ) -> dict[str, Any]:
        if urdf_mesh.filename is None:
            raise ValueError("Mesh must have filename defined.")
        mesh_dict: dict[str, Any] = {
            "filename": self._resolve_asset(urdf_mesh.filename, assets),
            "scale": urdf_mesh.scale if urdf_mesh.scale else [1, 1, 1],
        }
        return mesh_dict

    def _convert_origin(self, urdf_origin: urdf.Pose) -> list[float]:
        origin: list[float] = [0, 0, 0, 0, 0, 0]
        if urdf_origin.xyz is not None:
            origin[0:3] = urdf_origin.xyz
        if urdf_origin.rpy is not None:
            origin[3:6] = urdf_origin.rpy
        return origin

    def _convert_inertial(self, urdf_inertial: urdf.Inertial) -> dict[str, Any]:
        if urdf_inertial.mass is None or urdf_inertial.inertia is None:
            raise ValueError("Inertial must have both mass and inertia defined.")
        inertial: dict[str, Any] = {}
        inertial["mass"] = urdf_inertial.mass
        inertial["ixx"] = urdf_inertial.inertia.ixx
        inertial["ixy"] = urdf_inertial.inertia.ixy
        inertial["ixz"] = urdf_inertial.inertia.ixz
        inertial["iyy"] = urdf_inertial.inertia.iyy
        inertial["iyz"] = urdf_inertial.inertia.iyz
        inertial["izz"] = urdf_inertial.inertia.izz
        if urdf_inertial.origin is not None:
            inertial["origin"] = self._convert_origin(urdf_inertial.origin)
        return inertial

    def _convert_visual(
        self, urdf_visual: urdf.Visual, assets: dict[str, str]
    ) -> dict[str, Any]:
        if urdf_visual.geometry is None:
            raise ValueError("Visual must have geometry defined.")
        visual: dict[str, Any] = {}
        geom_type = type(urdf_visual.geometry).__name__.lower()
        visual["geometry"] = {"type": geom_type}
        if geom_type == "box":
            visual["geometry"].update(self._convert_box(urdf_visual.geometry))
        elif geom_type == "cylinder":
            visual["geometry"].update(self._convert_cylinder(urdf_visual.geometry))
        elif geom_type == "sphere":
            visual["geometry"].update(self._convert_sphere(urdf_visual.geometry))
        elif geom_type == "mesh":
            visual["geometry"].update(self._convert_mesh(urdf_visual.geometry, assets))
        else:
            raise ValueError(f"Unsupported geometry type: {geom_type}")
        if urdf_visual.origin is not None:
            visual["origin"] = self._convert_origin(urdf_visual.origin)
        if urdf_visual.material is not None:
            visual["material"] = self._convert_material(urdf_visual.material, assets)
        return visual

    def _convert_collision(
        self, urdf_collision: urdf.Collision, assets: dict[str, str]
    ) -> dict[str, Any]:
        if urdf_collision.geometry is None:
            raise ValueError("Collision must have geometry defined.")
        collision: dict[str, Any] = {}
        geom_type = type(urdf_collision.geometry).__name__.lower()
        collision["geometry"] = {"type": geom_type}
        if geom_type == "box":
            collision["geometry"].update(self._convert_box(urdf_collision.geometry))
        elif geom_type == "cylinder":
            collision["geometry"].update(
                self._convert_cylinder(urdf_collision.geometry)
            )
        elif geom_type == "sphere":
            collision["geometry"].update(self._convert_sphere(urdf_collision.geometry))
        elif geom_type == "mesh":
            collision["geometry"].update(
                self._convert_mesh(urdf_collision.geometry, assets)
            )
        else:
            raise ValueError(f"Unsupported geometry type: {geom_type}")
        if urdf_collision.origin is not None:
            collision["origin"] = self._convert_origin(urdf_collision.origin)
        return collision

    def _convert_link(
        self, urdf_link: urdf.Link, assets: dict[str, str]
    ) -> dict[str, Any]:
        if urdf_link.name is None:
            raise ValueError("Link must have a name defined.")
        link: dict[str, Any] = {"name": urdf_link.name}
        if urdf_link.inertial is not None:
            link["inertial"] = self._convert_inertial(urdf_link.inertial)
        if urdf_link.visuals:
            link["visuals"] = [
                self._convert_visual(v, assets)
                for v in urdf_link.visuals
                if v is not None
            ]
        if urdf_link.collisions:
            link["collisions"] = [
                self._convert_collision(c, assets)
                for c in urdf_link.collisions
                if c is not None
            ]
        return link

    def _convert_limit(self, urdf_limit: urdf.JointLimit) -> dict[str, Any]:
        if urdf_limit.effort is None or urdf_limit.velocity is None:
            raise ValueError("Limit must have both effort and velocity defined.")
        limit: dict[str, Any] = {
            "effort": urdf_limit.effort,
            "velocity": urdf_limit.velocity,
        }
        if urdf_limit.lower is not None:
            limit["lower"] = urdf_limit.lower
        if urdf_limit.upper is not None:
            limit["upper"] = urdf_limit.upper
        return limit

    def _convert_dynamics(self, urdf_dynamics: urdf.JointDynamics) -> dict[str, Any]:
        dynamics: dict[str, Any] = {}
        if urdf_dynamics.damping is not None:
            dynamics["damping"] = urdf_dynamics.damping
        if urdf_dynamics.friction is not None:
            dynamics["friction"] = urdf_dynamics.friction
        return dynamics

    def _convert_mimic(self, urdf_mimic: urdf.JointMimic) -> dict[str, Any]:
        if urdf_mimic.joint is None:
            raise ValueError("Mimic must have joint name defined.")
        mimic: dict[str, Any] = {"name": urdf_mimic.joint}
        if urdf_mimic.multiplier is not None:
            mimic["multiplier"] = urdf_mimic.multiplier
        if urdf_mimic.offset is not None:
            mimic["offset"] = urdf_mimic.offset
        return mimic

    def _convert_joint(self, urdf_joint: urdf.Joint) -> dict[str, Any]:
        if urdf_joint.name is None:
            raise ValueError("Joint must have a name defined.")
        if urdf_joint.type is None:
            raise ValueError("Joint must have a type defined.")
        if urdf_joint.parent is None:
            raise ValueError("Joint must have a parent defined.")
        if urdf_joint.child is None:
            raise ValueError("Joint must have a child defined.")
        joint: dict[str, Any] = {
            "name": urdf_joint.name,
            "type": urdf_joint.type,
            "parent": urdf_joint.parent,
            "child": urdf_joint.child,
        }
        if urdf_joint.origin is not None:
            joint["origin"] = self._convert_origin(urdf_joint.origin)
        if urdf_joint.type == "fixed":
            return joint  # Fixed joints have no other properties
        if urdf_joint.axis is not None:
            joint["axis"] = urdf_joint.axis
        if urdf_joint.dynamics is not None:
            joint["dynamics"] = self._convert_dynamics(urdf_joint.dynamics)
        if urdf_joint.mimic is not None:
            joint["mimic"] = self._convert_mimic(urdf_joint.mimic)
        if urdf_joint.limit is not None:
            joint["limits"] = self._convert_limit(urdf_joint.limit)
        return joint


if __name__ == "__main__":
    import json
    import os
    import sys

    HOME = os.path.expanduser("~")

    if len(sys.argv) < 2:
        print("Usage: python urdf_converter.py <urdf_file> [asset_dir]")
        sys.exit(1)

    urdf_file = sys.argv[1]
    asset_dir = sys.argv[2] if len(sys.argv) > 2 else None

    converter = URDFConverter()
    try:
        jrdf, assets = converter.convert(urdf_file, asset_dir)
        print(json.dumps(jrdf, indent=4))
        if assets:
            assets_dir = os.path.join(".", jrdf["name"].lower(), "assets")
            os.makedirs(assets_dir, exist_ok=True)
            for src_file, dest_file in assets.items():
                full_path = os.path.join(assets_dir, dest_file)
                print(f"Copying asset {src_file} to {full_path}")
                dir_name = os.path.dirname(full_path)
                if dir_name:
                    os.makedirs(dir_name, exist_ok=True)
                os.system(f"cp {src_file} {full_path}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
