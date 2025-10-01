import sys
import os

# This is necessary for using dynamically loaded message types due to PyInstaller limitations
rix_path = os.path.expanduser("~/.rix/python/rix")
sys.path.append(rix_path)

from rix.rob import RobotModel
from open3d_util import Open3DRobotModel

import json
import argparse
import open3d as o3d
from urdf_parser_py.urdf import URDF


HOME = os.path.expanduser("~")
USAGE = """jrdf [-h] function [arg]

Functions:
  create <name> <json | urdf> [asset directory]    - Create a JRDF model
  list                                             - List all JRDF models
  validate <input.json>                            - Validate a JRDF JSON file
  visualize <name>                                 - Visualize a JRDF model
"""


def find_file(filename: str, path: str) -> str | None:
    for entry in os.listdir(path):
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path):
            return find_file(filename, full_path)
        elif full_path.endswith(filename):
            return full_path
    return None


def find_model_file(name: str, filename: str) -> str | None:
    path = find_file(
        os.path.basename(filename), HOME + "/.rix/jrdf/models/" + name + "/assets"
    )
    if path is None:
        return None
    return path.split(HOME + "/.rix/jrdf/models/" + name + "/assets/")[1]


def convert_urdf_to_jrdf(name: str, urdf_file: str) -> dict:
    # Code here
    jrdf: dict = {
        "name": "",
        "links": [],
        "joints": [],
    }

    # Use URDF library to store data in the jrdf dict
    robot = URDF.from_xml_file(urdf_file)

    jrdf["name"] = robot.name

    # Parse global materials
    if len(robot.materials) > 0:
        jrdf["materials"] = []
        for material in robot.materials:
            tmp_material = {"name": material.name}
            if material.color is not None:
                tmp_material["color"] = material.color
            if material.texture is not None:
                tmp_material["filename"] = material.texture.filename
            jrdf["materials"].append(tmp_material)

    # Use JSON library to write jrdf dict to file as JSON
    for link in robot.links:
        link_dict = {
            "name": link.name,
        }

        if link.visuals:
            # For each visual, add a visual object to the list within the link
            visuals_list = []
            for visual in link.visuals:
                geom_type = type(visual.geometry).__name__.lower()

                if geom_type == "mesh":
                    filename = find_model_file(name, visual.geometry.filename)
                    if filename is None:
                        print(
                            'Warning! Unable to find model "'
                            + visual.geometry.filename
                            + '".'
                        )
                        filename = ""

                    geometry = {
                        "type": geom_type,
                        "filename": filename,
                        "scale": (
                            visual.geometry.scale
                            if visual.geometry.scale
                            else [1, 1, 1]
                        ),
                    }
                elif geom_type == "box":
                    geometry = {"type": geom_type, "size": list(visual.geometry.size)}
                elif geom_type == "cylinder":
                    geometry = {
                        "type": geom_type,
                        "radius": visual.geometry.radius,
                        "length": visual.geometry.length,
                    }
                elif geom_type == "sphere":
                    geometry = {"type": geom_type, "radius": visual.geometry.radius}

                origin = {
                    "xyz": visual.origin.xyz if visual.origin else [0, 0, 0],
                    "rpy": visual.origin.rpy if visual.origin else [0, 0, 0],
                }

                material = {}
                if visual.material:
                    material["name"] = visual.material.name
                    if visual.material.texture:
                        material["filename"] = visual.material.texture.filename
                    if visual.material.color:
                        material["color"] = visual.material.color.rgba

                visual_obj = {
                    "geometry": geometry,
                    "origin": origin,
                    "material": material,
                }
                visuals_list.append(visual_obj)

            link_dict["visuals"] = visuals_list

        # Add support for multiple collision properties
        if link.collisions:
            collisions_list = []
            for collision in link.collisions:
                geom_type = type(collision.geometry).__name__.lower()

                if geom_type == "mesh":
                    filename = find_model_file(name, visual.geometry.filename)
                    if filename is None:
                        print(
                            'Warning! Unable to find model "'
                            + visual.geometry.filename
                            + '".'
                        )
                        filename = ""

                    geometry = {
                        "type": geom_type,
                        "filename": filename,
                        "scale": (
                            visual.geometry.scale
                            if visual.geometry.scale
                            else [1, 1, 1]
                        ),
                    }
                elif geom_type == "box":
                    geometry = {
                        "type": geom_type,
                        "size": collision.geometry.size,
                    }
                elif geom_type == "cylinder":
                    geometry = {
                        "type": geom_type,
                        "radius": collision.geometry.radius,
                        "length": collision.geometry.length,
                    }
                elif geom_type == "sphere":
                    geometry = {
                        "type": geom_type,
                    }

                origin = {
                    "xyz": collision.origin.xyz,
                    "rpy": collision.origin.rpy,
                }

                collision_obj = {
                    "geometry": geometry,
                    "origin": origin,
                    "material": material,
                }
                collisions_list.append(collision_obj)

            link_dict["collisions"] = collisions_list

        # Add support for intertia property
        if link.inertial:
            inertial = link.inertial
            link_dict["inertial"] = {
                "origin": {
                    "xyz": (
                        inertial.origin.xyz
                        if inertial.origin is not None
                        else [0, 0, 0]
                    ),
                    "rpy": (
                        inertial.origin.rpy
                        if inertial.origin is not None
                        else [0, 0, 0]
                    ),
                },
                "mass": inertial.mass,
                "inertia": {
                    "ixx": inertial.inertia.ixx,
                    "ixy": inertial.inertia.ixy,
                    "ixz": inertial.inertia.ixz,
                    "iyy": inertial.inertia.iyy,
                    "iyz": inertial.inertia.iyz,
                    "izz": inertial.inertia.izz,
                },
            }

        jrdf["links"].append(link_dict)

    # Parse joints
    for joint in robot.joints:
        joint_dict = {
            "name": joint.name,
            "type": joint.type,
            "parent": joint.parent,
            "child": joint.child,
            "origin": {
                "xyz": joint.origin.xyz if joint.origin else [0, 0, 0],
                "rpy": joint.origin.rpy if joint.origin else [0, 0, 0],
            },
            "axis": joint.axis if joint.axis else [1, 0, 0],
        }
        if joint.limit is not None:
            joint_dict["limits"] = {
                "effort": joint.limit.effort,
                "velocity": joint.limit.velocity,
            }
            if joint.limit.lower is not None:
                joint_dict["limits"]["lower"] = joint.limit.lower
            if joint.limit.upper is not None:
                joint_dict["limits"]["upper"] = joint.limit.upper

        if joint.dynamics is not None:
            joint_dict["dynamics"] = {}
            if joint.dynamics.damping is not None:
                joint_dict["dynamics"]["damping"] = joint.dynamics.damping
            if joint.dynamics.friction is not None:
                joint_dict["dynamics"]["friction"] = joint.dynamics.friction

        if joint.mimic is not None:
            joint_dict["mimic"] = {}
            if joint.mimic.multiplier is not None:
                joint_dict["mimic"]["multiplier"] = joint.mimic.multiplier
            if joint.mimic.offset is not None:
                joint_dict["mimic"]["offset"] = joint.mimic.offset
            if joint.mimic.joint is not None:
                joint_dict["mimic"]["name"] = joint.mimic.joint

        jrdf["joints"].append(joint_dict)

    return jrdf


def create(name: str, input_file: str, asset_dir: str | None) -> None:
    if not os.path.isfile(input_file):
        print(f"Error! Input file '{input_file}' does not exist.")
        return

    # If provided, copy asset files to ~/.rix/jrdf/models/<name>/assets/
    if asset_dir:
        if not os.path.isdir(asset_dir):
            print(f"Error! Asset directory '{asset_dir}' does not exist.")
            return
        os.system(f"mkdir -p {HOME}/.rix/jrdf/models/{name}/assets")
        os.system(f"cp -r {asset_dir} {HOME}/.rix/jrdf/models/{name}/assets")

    # Determine if input is JSON or URDF
    if not (
        input_file.lower().endswith(".json") or input_file.lower().endswith(".urdf")
    ):
        print("Error! Input file must be a .json or .urdf file.")
        return

    jrdf: dict = {}
    if input_file.lower().endswith(".json"):
        with open(input_file, "r") as f:
            jrdf = json.load(f)
    if input_file.lower().endswith(".urdf"):
        jrdf = convert_urdf_to_jrdf(name, input_file)

    # Copy json to ~/.rix/jrdf/models/<name>/model.json
    output_file = os.path.join(HOME, ".rix", "jrdf", "models", name, "model.json")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(jrdf, f, indent=4)


def list() -> None:
    models_dir = os.path.join(HOME, ".rix", "jrdf", "models")
    if not os.path.isdir(models_dir):
        print("No JRDF models found.")
        return

    model_names = [
        name
        for name in os.listdir(models_dir)
        if os.path.isdir(os.path.join(models_dir, name))
    ]

    if not model_names:
        print("No JRDF models found.")
        return

    for name in model_names:
        print(name)


def validate(jrdf_file: str) -> None:
    try:
        with open(jrdf_file, "r") as f:
            jrdf = json.load(f)

        # TODO: Implement full JSON schema validation
        if "name" not in jrdf or not isinstance(jrdf["name"], str):
            print("Invalid JRDF: Missing or invalid 'name' field.")
            return

        if "links" not in jrdf or not isinstance(jrdf["links"], list):
            print("Invalid JRDF: Missing or invalid 'links' field.")
            return

        if "joints" not in jrdf or not isinstance(jrdf["joints"], list):
            print("Invalid JRDF: Missing or invalid 'joints' field.")
            return

        print(f"JRDF file '{jrdf_file}' is valid.")
    except Exception as e:
        print(f"Error validating JRDF file '{jrdf_file}': {e}")


def visualize(name: str) -> None:
    try:
        print(f"Visualizing JRDF model '{name}'...")
        vis = o3d.visualization.Visualizer()
        vis.create_window(window_name="JRDF Visualizer", width=800, height=600)
        o3d_robot = Open3DRobotModel(name, vis)

        vis.run()
        vis.destroy_window()

    except Exception as e:
        print(f"Error visualizing JRDF model '{name}': {e}")


def main(args: argparse.Namespace) -> None:
    function = args.function

    if function == "create":
        if len(args.args) < 2:
            print("Error! 'create' requires at least 2 arguments: <name> <json | urdf>")
            return
        name = args.args[0]
        input_file = args.args[1]
        if not input_file:
            print("Error! 'create' requires an input JSON or URDF file as an argument.")
            return

        asset_dir = args.args[2] if len(args.args) > 2 else None
        create(name, input_file, asset_dir)
        return

    if function == "list":
        list()
        return

    if function == "validate":
        jrdf_file = args.arg
        if not jrdf_file:
            print("Error! 'validate' requires an input JRDF file as an argument.")
            return
        validate(jrdf_file)
        return

    if function == "visualize":
        name = args.args[0] if len(args.args) > 0 else None
        if not name:
            print("Error! 'visualize' requires an input JRDF file as an argument.")
            return
        visualize(name)
        return

    print("Error! Unknown function:", function)
    print(USAGE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="jrdf CLI", usage=USAGE)
    parser.add_argument("-v", "--version", action="version", version="jrdf 1.0")
    parser.add_argument("function", type=str, help="Function to call (convert, mesh)")
    parser.add_argument("args", type=str, nargs="*", help="Arguments for the function")
    args = parser.parse_args()
    main(args)
