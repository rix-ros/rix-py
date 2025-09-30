import os
import numpy as np
import open3d as o3d
from rix.rob.robot_model import RobotModel
from rix.rob.link import Link, Material, GeometryType

HOME = os.path.expanduser("~")


class Open3DRobotModel:
    def __init__(self, robot_model: RobotModel, vis: o3d.visualization.Visualizer):
        self.visual_transforms = {}
        self.visuals = {}  # link name to entity mapping
        self.visual_origins = {}  # map of visual visual_origins

        self.original_colors = {}  # store original colors for restoring after hover

        for _, link in robot_model.links.items():
            materials = {}
            for material in robot_model.materials.values():
                materials[material.name] = material

            link_name, visuals, visual_origins = self.parse_link(link, materials)

            for e in visuals:
                vis.add_geometry(e)

            self.visuals[link_name] = visuals
            self.visual_transforms[link_name] = [np.eye(4) for _ in range(len(visuals))]
            self.visual_origins[link_name] = visual_origins

        # Set initial transforms using FK from root to each link
        tdict = {}
        cdict = {}
        append_cdict = cdict.setdefault  # local binding for speed

        # Append the world to root transform
        append_cdict("world", []).append(robot_model.root.name)
        tdict[robot_model.root.name] = robot_model.world_to_root

        # Build the transform and child dictionaries
        for joint in robot_model.joints.values():
            parent = joint.parent
            child = joint.child
            tdict[child] = joint.origin @ joint.transform()
            append_cdict(parent, []).append(child)

        global_tf = {}
        mstack = [np.eye(4)]
        self.fk_recursive("world", mstack, tdict, cdict, global_tf)

        for link_name, visuals in self.visuals.items():
            if link_name in global_tf:
                link_tf = global_tf[link_name]
                for i in range(len(visuals)):
                    visual_origin = self.visual_origins[link_name][i]
                    visual_tf = link_tf @ visual_origin
                    self.visual_transforms[link_name][i] = visual_tf
                    visuals[i].transform(visual_tf)

    def fk_recursive(
        self,
        link: str,
        mstack: list[np.ndarray],
        tdict: dict[str, np.ndarray],
        cdict: dict[str, list[str]],
        global_tf: dict[str, np.ndarray],
    ) -> None:
        children = cdict.get(link)
        if children is None:
            return

        base_transform = mstack[-1]
        for child in children:
            child_tf = base_transform @ tdict[child]
            mstack.append(child_tf)
            global_tf[child] = child_tf
            self.fk_recursive(child, mstack, tdict, cdict, global_tf)
            mstack.pop()

    def parse_geometry(self, geometry: dict):
        mesh = None
        if geometry.type == GeometryType.BOX:
            size = geometry.size
            mesh = o3d.geometry.TriangleMesh.create_box(
                width=size[0], height=size[1], depth=size[2]
            )
            mesh.compute_vertex_normals()
        elif geometry.type == GeometryType.CYLINDER:
            radius = geometry.radius
            length = geometry.length
            mesh = o3d.geometry.TriangleMesh.create_cylinder(
                radius=radius, height=length
            )
            mesh.compute_vertex_normals()
        elif geometry.type == GeometryType.SPHERE:
            radius = geometry.radius
            mesh = o3d.geometry.TriangleMesh.create_sphere(radius=radius)
            mesh.compute_vertex_normals()
        elif geometry.type == GeometryType.MESH:
            filename = HOME + "/.rix/models/" + geometry.filename
            mesh = o3d.io.read_triangle_mesh(filename)
            if mesh.is_empty():
                raise ValueError(f"Failed to load mesh from file: {filename}")
            if geometry.scale is not None:
                scale = geometry.scale
                mesh.vertices = o3d.utility.Vector3dVector(
                    np.asarray(mesh.vertices) * np.array(scale)
                )
            mesh.compute_vertex_normals()
            mesh.compute_triangle_normals()
        else:
            raise ValueError(f"Unsupported geometry type: {geometry.type}")

        return mesh

    def parse_link(self, link: Link, materials: dict[str, Material]):
        link_name = link.name
        visuals = []
        visual_origins = []
        default_color = [70 / 255, 70 / 255, 70 / 255]
        if link.visuals is not None:
            for visual in link.visuals:
                material = None
                if visual.material.name in materials:
                    material = materials[visual.material.name]
                else:
                    material = visual.material

                visual_origins.append(visual.origin)

                # Call the parse geometry function.
                mesh = self.parse_geometry(visual.geometry)
                if material is not None:
                    if len(material.texture_filename) > 0:
                        if np.asarray(mesh.triangle_uvs).size == 0:
                            mesh.paint_uniform_color(default_color)
                        else:
                            texture_path = (
                                HOME + "/.rix/models/" + material.texture_filename
                            )
                            texture = o3d.io.read_image(texture_path)
                            mesh.textures = [o3d.geometry.Image(texture)]
                    else:
                        mesh.paint_uniform_color(material.color[:3])

                visuals.append(mesh)

        return link_name, visuals, visual_origins
