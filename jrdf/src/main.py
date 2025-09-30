import json
import argparse
from urdf_parser_py.urdf import URDF

import os

HOME = os.path.expanduser("~")

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

def main(args):
    # Code here
    jrdf: dict = {
        "name": "",
        "links": [],
        "joints": [],
    }

    # Use URDF library to store data in the jrdf dict
    robot = URDF.from_xml_file(args.filename)

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

    output_filename = args.filename.replace(".urdf", ".json")
    with open(output_filename, "w") as out:
        json.dump(jrdf, out, indent=2)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog="jrdf", description="Convert URDF to JSON")
    parser.add_argument("filename")

    args = parser.parse_args()
    main(args)
