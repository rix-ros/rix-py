import os
import collada
import numpy as np
import open3d as o3d
from rix.rob.robot_model import RobotModel
from rix.rob.link import Link, Material, GeometryType

HOME = os.path.expanduser("~")


class Open3DRobotModel:
    def __init__(self, name: str, vis: o3d.visualization.Visualizer):
        self.name = name
        self.visual_transforms = {}
        self.visuals = {}  # link name to entity mapping
        self.visual_origins = {}  # map of visual visual_origins

        self.original_colors = {}  # store original colors for restoring after hover

        robot_model = RobotModel(HOME + "/.rix/jrdf/models/" + name + "/model.json")
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
        meshes = []
        if geometry.type == GeometryType.BOX:
            size = geometry.size
            meshes.append(
                o3d.geometry.TriangleMesh.create_box(
                    width=size[0], height=size[1], depth=size[2]
                )
            )
            meshes[-1].compute_vertex_normals()
        elif geometry.type == GeometryType.CYLINDER:
            radius = geometry.radius
            length = geometry.length
            meshes.append(
                o3d.geometry.TriangleMesh.create_cylinder(radius=radius, height=length)
            )
            meshes[-1].compute_vertex_normals()
        elif geometry.type == GeometryType.SPHERE:
            radius = geometry.radius
            meshes.append(o3d.geometry.TriangleMesh.create_sphere(radius=radius))
            meshes[-1].compute_vertex_normals()
        elif geometry.type == GeometryType.MESH:
            print(f"Loading mesh: {geometry.filename}")
            filename = f"{HOME}/.rix/jrdf/models/{self.name}/assets/{geometry.filename}"

            # If the file is stl or obj, use read_triangle_mesh
            if not os.path.isfile(filename):
                raise FileNotFoundError(f"Mesh file not found: {filename}")

            meshes_ = []
            if geometry.filename.lower().endswith(".dae"):
                meshes_ = self.parse_dae_mesh(filename)
            else:
                meshes_ = [o3d.io.read_triangle_mesh(filename)]

            if meshes_ is None or all(mesh.is_empty() for mesh in meshes_):
                raise ValueError(f"Failed to load mesh from file: {filename}")

            if geometry.scale is not None:
                scale = geometry.scale
                for mesh in meshes_:
                    mesh.vertices = o3d.utility.Vector3dVector(
                        np.asarray(mesh.vertices) * np.array(scale)
                    )
            meshes.extend(meshes_)
        else:
            raise ValueError(f"Unsupported geometry type: {geometry.type}")

        for mesh in meshes:
            mesh.compute_vertex_normals()
            mesh.compute_triangle_normals()
        return meshes

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

                # Call the parse geometry function.
                meshes = self.parse_geometry(visual.geometry)
                if material is not None:
                    for mesh in meshes:
                        if len(material.texture_filename) > 0:
                            if np.asarray(mesh.triangle_uvs).size == 0:
                                mesh.paint_uniform_color(default_color)
                            else:
                                texture_path = (
                                    HOME
                                    + "/.rix/jrdf/models/"
                                    + self.name
                                    + "/assets/"
                                    + material.texture_filename
                                )
                                texture = o3d.io.read_image(texture_path)
                                mesh.textures = [o3d.geometry.Image(texture)]
                        else:
                            mesh.paint_uniform_color(material.color[:3])

                visuals.extend(meshes)
                visual_origins.extend([visual.origin for _ in meshes])

        return link_name, visuals, visual_origins

    def parse_dae_mesh(self, filename: str) -> list[o3d.geometry.TriangleMesh] | None:
        mesh = collada.Collada(filename, ignore=[collada.DaeBrokenRefError])
        if len(mesh.geometries) == 0:
            return None

        meshes_o3d = []
        for geometry in mesh.geometries:
            for prim in geometry.primitives:

                prim_triangles = None
                if isinstance(prim, collada.triangleset.TriangleSet):
                    prim_triangles = prim
                elif isinstance(prim, collada.polylist.Polylist):
                    prim_triangles = prim.triangleset()
                else:
                    print(f"Skipping unsupported primitive type: {type(prim)}")
                    continue

                if prim_triangles is None:
                    return None

                vertices = prim_triangles.vertex.reshape(-1, 3).astype(np.float64)
                indices = prim_triangles.vertex_index.astype(np.int32)
                normals = prim_triangles.normal.reshape(-1, 3).astype(np.float64)

                if len(vertices) == 0:
                    raise ValueError("No triangles found in the .dae file.")

                # Convert to Open3D TriangleMesh
                mesh_o3d = o3d.geometry.TriangleMesh()
                mesh_o3d.vertices = o3d.utility.Vector3dVector(vertices)
                mesh_o3d.triangles = o3d.utility.Vector3iVector(indices.reshape(-1, 3))
                mesh_o3d.vertex_normals = o3d.utility.Vector3dVector(normals)

                meshes_o3d.append(mesh_o3d)

        return meshes_o3d
