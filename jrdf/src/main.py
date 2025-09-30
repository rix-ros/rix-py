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
  convert <input.urdf> [output.json] - Convert a URDF file to JSON
  mesh <name> <mesh file/dir>        - Install mesh files to ~/.rix/models/<name>/
  validate <input.json>              - Validate a JRDF JSON file
  visualize <input.json>             - Visualize a JRDF JSON file
  info <input.json>                  - Print information about a JRDF JSON file
"""


def find_file(filename: str, path: str) -> str | None:
    for entry in os.listdir(path):
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path):
            return find_file(filename, full_path)
        elif full_path.endswith(filename):
            return full_path
    return None


def find_model_file(filename: str) -> str | None:
    path = find_file(os.path.basename(filename), HOME + "/.rix/models/")
    if path is None:
        return None
    return path.split(HOME + "/.rix/models/")[1]


def convert(urdf_file: str, output_file: str | None) -> None:
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
                    filename = find_model_file(visual.geometry.filename)
                    if filename is None:
                        print(
                            'Warning! Unable to find model "'
                            + visual.geometry.filename
                            + '". Have you moved the meshes to ~/.rix/models yet?'
                        )
                        filename = ""

                    geometry = {
                        "type": geom_type,
                        "filename": filename,
                        "scale": list(visual.geometry.scale or [1, 1, 1]),
                    }
                elif geom_type == "box":
                    geometry = {"type": geom_type, "size": list(visual.geometry.size)}
                elif geom_type == "cylinder":
                    geometry = {"type": geom_type, "size": list(visual.geometry.size)}
                elif geom_type == "sphere":
                    geometry = {"type": geom_type, "size": list(visual.geometry.size)}

                origin = {
                    "xyz": list(visual.origin.xyz),
                    "rpy": list(visual.origin.rpy),
                }

                material = {}
                if visual.material:
                    material["name"] = visual.material.name
                    if visual.material.texture:
                        material["filename"] = visual.material.texture.filename
                    if visual.material.color:
                        material["color"] = list(visual.material.color)

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
                    filename = find_model_file(visual.geometry.filename)
                    if filename is None:
                        print(
                            'Warning! Unable to find model "'
                            + visual.geometry.filename
                            + '". Have you moved the meshes to ~/.rix/models yet?'
                        )
                        filename = ""

                    geometry = {
                        "type": geom_type,
                        "filename": filename,
                        "scale": list(visual.geometry.scale or [1, 1, 1]),
                    }
                elif geom_type == "box":
                    geometry = {
                        "type": geom_type,
                        "size": list(collision.geometry.size),
                    }
                elif geom_type == "cylinder":
                    geometry = {
                        "type": geom_type,
                        "size": list(collision.geometry.size),
                    }
                elif geom_type == "sphere":
                    geometry = {
                        "type": geom_type,
                        "size": list(collision.geometry.size),
                    }

                origin = {
                    "xyz": list(collision.origin.xyz),
                    "rpy": list(collision.origin.rpy),
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
                        list(inertial.origin.xyz)
                        if inertial.origin is not None
                        else [0, 0, 0]
                    ),
                    "rpy": (
                        list(inertial.origin.rpy)
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
                "xyz": list(joint.origin.xyz) if joint.origin else [0, 0, 0],
                "rpy": list(joint.origin.rpy) if joint.origin else [0, 0, 0],
            },
            "axis": list(joint.axis),
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

    if output_file is not None:
        output_filename = output_file
    else:
        output_filename = urdf_file.replace(".urdf", ".json")
    with open(output_filename, "w") as out:
        json.dump(jrdf, out, indent=2)


def mesh(name: str, mesh_path: str) -> None:
    dest_dir = os.path.join(HOME, ".rix", "models", name)
    os.makedirs(dest_dir, exist_ok=True)

    if os.path.isdir(mesh_path):
        for entry in os.listdir(mesh_path):
            full_path = os.path.join(mesh_path, entry)
            if os.path.isfile(full_path):
                dest_path = os.path.join(dest_dir, entry)
                with open(full_path, "rb") as src_file:
                    with open(dest_path, "wb") as dest_file:
                        dest_file.write(src_file.read())
        print(f"Installed all files from directory '{mesh_path}' to '{dest_dir}'")
    elif os.path.isfile(mesh_path):
        dest_path = os.path.join(dest_dir, os.path.basename(mesh_path))
        with open(mesh_path, "rb") as src_file:
            with open(dest_path, "wb") as dest_file:
                dest_file.write(src_file.read())
        print(f"Installed file '{mesh_path}' to '{dest_path}'")
    else:
        print(f"Error: '{mesh_path}' is neither a file nor a directory.")


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


def visualize(jrdf_file: str) -> None:
    try:
        print(f"Visualizing JRDF file '{jrdf_file}'...")
        robot_model = RobotModel(jrdf_file)
        vis = o3d.visualization.Visualizer()
        vis.create_window(window_name="JRDF Visualizer", width=800, height=600)
        o3d_robot = Open3DRobotModel(robot_model, vis)

        vis.run()
        vis.destroy_window()

    except Exception as e:
        print(f"Error visualizing JRDF file '{jrdf_file}': {e}")


def main(args: argparse.Namespace) -> None:
    function = args.function

    if function == "convert":
        urdf_file = args.arg
        if not urdf_file:
            print("Error! 'convert' requires an input URDF file as an argument.")
            return
        output_file = None
        if len(args.extra) > 0:
            output_file = args.extra[0]
        convert(urdf_file, output_file)
        return

    if function == "mesh":
        if not args.arg or len(args.extra) == 0:
            print(
                "Error! 'mesh' requires a name and a mesh file or directory as arguments."
            )
            return
        name = args.arg
        mesh_path = args.extra[0]
        mesh(name, mesh_path)
        return

    if function == "validate":
        jrdf_file = args.arg
        if not jrdf_file:
            print("Error! 'validate' requires an input JRDF file as an argument.")
            return
        validate(jrdf_file)
        return

    if function == "visualize":
        jrdf_file = args.arg
        if not jrdf_file:
            print("Error! 'visualize' requires an input JRDF file as an argument.")
            return
        visualize(jrdf_file)
        return

    print("Error! Unknown function:", function)
    print(USAGE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="jrdf CLI", usage=USAGE)
    parser.add_argument("-v", "--version", action="version", version="jrdf 1.0")
    parser.add_argument("function", type=str, help="Function to call (convert, mesh)")
    parser.add_argument(
        "arg", type=str, nargs="?", help="Primary argument for the function"
    )
    parser.add_argument("extra", nargs="*", help="Extra arguments for the function")
    args = parser.parse_args()
    main(args)
