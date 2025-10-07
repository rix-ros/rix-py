import os
import collada
import numpy as np
import open3d as o3d
from typing import List, Dict, Tuple, Optional, Union
from rix.rob.robot_model import RobotModel
from rix.rob.link import Link, Material, GeometryType, Geometry

HOME = os.path.expanduser("~")


class Open3DRobotModel:
    def __init__(self, name: str, use_modern_visualizer: bool = True):
        self.name = name
        self.use_modern_visualizer = use_modern_visualizer
        self.visual_transforms: Dict[str, List[np.ndarray]] = {}
        self.visuals: Dict[str, List[Union[o3d.geometry.TriangleMesh, o3d.geometry.LineSet]]] = {}
        self.visual_origins: Dict[str, List[np.ndarray]] = {}
        self.original_colors: Dict[str, List[np.ndarray]] = {}
        
        # Material and texture management
        self.materials: Dict[str, List[Dict]] = {}
        self.textures: Dict[str, o3d.geometry.Image] = {}
        
        robot_model = RobotModel(HOME + "/.rix/jrdf/models/" + name + "/model.json")
        
        # Parse all links and their visuals
        for _, link in robot_model.links.items():
            link_name, visuals, visual_origins, materials = self.parse_link(link)
            
            self.visuals[link_name] = visuals
            self.visual_transforms[link_name] = [np.eye(4) for _ in range(len(visuals))]
            self.visual_origins[link_name] = visual_origins
            self.materials[link_name] = materials
            
            # Store original colors for restoration
            self.original_colors[link_name] = []
            for visual in visuals:
                if hasattr(visual, 'vertex_colors') and len(visual.vertex_colors) > 0:
                    self.original_colors[link_name].append(np.asarray(visual.vertex_colors))
                else:
                    self.original_colors[link_name].append(None)

        # Set initial transforms using FK from root to each link
        tdict = {}
        cdict = {}
        append_cdict = cdict.setdefault

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
    
    def get_all_geometries(self) -> List[Union[o3d.geometry.TriangleMesh, o3d.geometry.LineSet]]:
        """Get all geometry objects for visualization with validation"""
        all_geometries = []
        for link_name, visuals in self.visuals.items():
            for i, visual in enumerate(visuals):
                # Validate geometry before adding
                if self._is_valid_geometry(visual):
                    all_geometries.append(visual)
                else:
                    print(f"Warning: Skipping invalid geometry in link '{link_name}' (index {i})")
        return all_geometries
    
    def _is_valid_geometry(self, geometry: Union[o3d.geometry.TriangleMesh, o3d.geometry.LineSet]) -> bool:
        """Check if a geometry object is valid for visualization"""
        try:
            if isinstance(geometry, o3d.geometry.TriangleMesh):
                # Check if mesh has vertices and triangles
                return (len(geometry.vertices) > 0 and 
                       len(geometry.triangles) > 0 and
                       not geometry.is_empty())
            elif isinstance(geometry, o3d.geometry.LineSet):
                # Check if line set has points and lines
                return (len(geometry.points) > 0 and 
                       len(geometry.lines) > 0)
            else:
                # Unknown geometry type
                return hasattr(geometry, 'is_empty') and not geometry.is_empty()
        except Exception as e:
            print(f"Error validating geometry: {e}")
            return False
    
    def get_link_geometries(self, link_name: str) -> List[Union[o3d.geometry.TriangleMesh, o3d.geometry.LineSet]]:
        """Get geometries for a specific link"""
        return self.visuals.get(link_name, [])
    
    def update_link_transform(self, link_name: str, transform: np.ndarray) -> None:
        """Update the transform of a specific link"""
        if link_name not in self.visuals:
            return
            
        visuals = self.visuals[link_name]
        visual_origins = self.visual_origins[link_name]
        
        for i, visual in enumerate(visuals):
            # Reset to original position
            if i < len(self.visual_transforms[link_name]):
                # Inverse of current transform
                current_transform = self.visual_transforms[link_name][i]
                visual.transform(np.linalg.inv(current_transform))
                
                # Apply new transform
                visual_origin = visual_origins[i] if i < len(visual_origins) else np.eye(4)
                new_transform = transform @ visual_origin
                visual.transform(new_transform)
                
                # Store new transform
                self.visual_transforms[link_name][i] = new_transform
    
    def set_link_color(self, link_name: str, color: List[float]) -> None:
        """Set the color of all geometries in a link"""
        if link_name not in self.visuals:
            return
            
        for visual in self.visuals[link_name]:
            if hasattr(visual, 'paint_uniform_color'):
                visual.paint_uniform_color(color)
    
    def reset_link_colors(self, link_name: str) -> None:
        """Reset link colors to original"""
        if link_name not in self.visuals or link_name not in self.original_colors:
            return
            
        visuals = self.visuals[link_name]
        original_colors = self.original_colors[link_name]
        
        for i, visual in enumerate(visuals):
            if i < len(original_colors) and original_colors[i] is not None:
                visual.vertex_colors = o3d.utility.Vector3dVector(original_colors[i])
            else:
                # Use material color if available
                if link_name in self.materials and i < len(self.materials[link_name]):
                    material = self.materials[link_name][i]
                    if not material.get("has_texture", False):
                        visual.paint_uniform_color(material.get("color", [0.7, 0.7, 0.7]))
    
    def get_bounding_box(self) -> o3d.geometry.AxisAlignedBoundingBox:
        """Get the bounding box of all geometries"""
        all_geometries = self.get_all_geometries()
        if not all_geometries:
            return o3d.geometry.AxisAlignedBoundingBox()
            
        # Combine all bounding boxes
        combined_box = all_geometries[0].get_axis_aligned_bounding_box()
        for geom in all_geometries[1:]:
            geom_box = geom.get_axis_aligned_bounding_box()
            combined_box += geom_box
            
        return combined_box
    
    def save_model(self, filename: str) -> bool:
        """Save the entire model to a file (PLY format)"""
        try:
            all_geometries = self.get_all_geometries()
            if not all_geometries:
                return False
                
            # Combine all triangle meshes
            combined_mesh = o3d.geometry.TriangleMesh()
            vertex_offset = 0
            
            for geom in all_geometries:
                if isinstance(geom, o3d.geometry.TriangleMesh):
                    # Add vertices
                    vertices = np.asarray(geom.vertices)
                    if len(combined_mesh.vertices) == 0:
                        combined_mesh.vertices = o3d.utility.Vector3dVector(vertices)
                    else:
                        combined_vertices = np.vstack([np.asarray(combined_mesh.vertices), vertices])
                        combined_mesh.vertices = o3d.utility.Vector3dVector(combined_vertices)
                    
                    # Add triangles with offset
                    triangles = np.asarray(geom.triangles) + vertex_offset
                    if len(combined_mesh.triangles) == 0:
                        combined_mesh.triangles = o3d.utility.Vector3iVector(triangles)
                    else:
                        combined_triangles = np.vstack([np.asarray(combined_mesh.triangles), triangles])
                        combined_mesh.triangles = o3d.utility.Vector3iVector(combined_triangles)
                    
                    vertex_offset += len(vertices)
            
            combined_mesh.compute_vertex_normals()
            combined_mesh.compute_triangle_normals()
            
            return o3d.io.write_triangle_mesh(filename, combined_mesh)
            
        except Exception as e:
            print(f"Error saving model: {e}")
            return False

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

    def parse_geometry(self, geometry: Geometry) -> List[Union[o3d.geometry.TriangleMesh, o3d.geometry.LineSet]]:
        """Parse geometry with enhanced support for textures and multiple primitive types"""
        geometries = []
        
        if geometry.type == GeometryType.BOX:
            size = geometry.size
            mesh = o3d.geometry.TriangleMesh.create_box(size[0], size[1], size[2])
            mesh.compute_vertex_normals()
            mesh.compute_triangle_normals()
            # Generate UV coordinates for box
            self._generate_box_uv_coordinates(mesh, size)
            geometries.append(mesh)
            
        elif geometry.type == GeometryType.CYLINDER:
            radius = geometry.radius
            length = geometry.length
            mesh = o3d.geometry.TriangleMesh.create_cylinder(radius, length)
            mesh.compute_vertex_normals()
            mesh.compute_triangle_normals()
            # Generate UV coordinates for cylinder
            self._generate_cylinder_uv_coordinates(mesh, radius, length)
            geometries.append(mesh)
            
        elif geometry.type == GeometryType.SPHERE:
            radius = geometry.radius
            mesh = o3d.geometry.TriangleMesh.create_sphere(radius)
            mesh.compute_vertex_normals()
            mesh.compute_triangle_normals()
            # Generate UV coordinates for sphere
            self._generate_sphere_uv_coordinates(mesh, radius)
            geometries.append(mesh)
            
        elif geometry.type == GeometryType.MESH:
            print(f"Loading mesh: {geometry.filename}")
            filename = f"{HOME}/.rix/jrdf/models/{self.name}/assets/{geometry.filename}"

            if not os.path.isfile(filename):
                raise FileNotFoundError(f"Mesh file not found: {filename}")

            loaded_geometries = []
            if geometry.filename.lower().endswith(".dae"):
                loaded_geometries = self.parse_dae_mesh(filename)
            else:
                loaded_mesh = o3d.io.read_triangle_mesh(filename)
                if not loaded_mesh.is_empty():
                    loaded_geometries = [loaded_mesh]

            if not loaded_geometries or all(g.is_empty() if hasattr(g, 'is_empty') else False for g in loaded_geometries):
                raise ValueError(f"Failed to load mesh from file: {filename}")

            # Apply scaling if specified
            if geometry.scale is not None:
                scale = geometry.scale
                for geom in loaded_geometries:
                    if hasattr(geom, 'vertices'):
                        geom.vertices = o3d.utility.Vector3dVector(
                            np.asarray(geom.vertices) * scale
                        )
            
            geometries.extend(loaded_geometries)
        else:
            raise ValueError(f"Unsupported geometry type: {geometry.type}")

        # Ensure all triangle meshes have proper normals
        for geom in geometries:
            if isinstance(geom, o3d.geometry.TriangleMesh):
                geom.compute_vertex_normals()
                geom.compute_triangle_normals()
                
        return geometries
    
    def _generate_box_uv_coordinates(self, mesh: o3d.geometry.TriangleMesh, size: List[float]) -> None:
        """Generate UV coordinates for a box mesh"""
        # This is a simplified UV mapping for boxes
        vertices = np.asarray(mesh.vertices)
        uv_coords = []
        
        for vertex in vertices:
            # Simple planar projection based on dominant axis
            u = (vertex[0] / size[0] + 0.5) % 1.0
            v = (vertex[1] / size[1] + 0.5) % 1.0
            uv_coords.append([u, v])
        
        # Store UV coordinates as vertex attribute (for modern Open3D)
        if hasattr(mesh, 'triangle_uvs'):
            # For triangle-based UV mapping
            triangles = np.asarray(mesh.triangles)
            triangle_uvs = []
            for triangle in triangles:
                for vertex_idx in triangle:
                    triangle_uvs.append(uv_coords[vertex_idx])
            mesh.triangle_uvs = o3d.utility.Vector2dVector(triangle_uvs)
    
    def _generate_cylinder_uv_coordinates(self, mesh: o3d.geometry.TriangleMesh, radius: float, length: float) -> None:
        """Generate UV coordinates for a cylinder mesh"""
        vertices = np.asarray(mesh.vertices)
        uv_coords = []
        
        for vertex in vertices:
            # Cylindrical UV mapping
            u = np.arctan2(vertex[1], vertex[0]) / (2 * np.pi) + 0.5
            v = vertex[2] / length + 0.5
            uv_coords.append([u, v])
        
        if hasattr(mesh, 'triangle_uvs'):
            triangles = np.asarray(mesh.triangles)
            triangle_uvs = []
            for triangle in triangles:
                for vertex_idx in triangle:
                    triangle_uvs.append(uv_coords[vertex_idx])
            mesh.triangle_uvs = o3d.utility.Vector2dVector(triangle_uvs)
    
    def _generate_sphere_uv_coordinates(self, mesh: o3d.geometry.TriangleMesh, radius: float) -> None:
        """Generate UV coordinates for a sphere mesh"""
        vertices = np.asarray(mesh.vertices)
        uv_coords = []
        
        for vertex in vertices:
            # Spherical UV mapping
            normalized = vertex / np.linalg.norm(vertex)
            u = np.arctan2(normalized[1], normalized[0]) / (2 * np.pi) + 0.5
            v = np.arcsin(normalized[2]) / np.pi + 0.5
            uv_coords.append([u, v])
        
        if hasattr(mesh, 'triangle_uvs'):
            triangles = np.asarray(mesh.triangles)
            triangle_uvs = []
            for triangle in triangles:
                for vertex_idx in triangle:
                    triangle_uvs.append(uv_coords[vertex_idx])
            mesh.triangle_uvs = o3d.utility.Vector2dVector(triangle_uvs)

    def parse_link(self, link: Link) -> Tuple[str, List[Union[o3d.geometry.TriangleMesh, o3d.geometry.LineSet]], List[np.ndarray], List[Dict]]:
        """Parse a link with enhanced material and texture support"""
        link_name = link.name
        visuals = []
        visual_origins = []
        materials = []
        default_color = [70 / 255, 70 / 255, 70 / 255]
        
        if link.visuals is not None:
            for visual in link.visuals:
                material = visual.material
                geometries = self.parse_geometry(visual.geometry)
                
                for geometry in geometries:
                    material_info = {"has_texture": False, "color": default_color}
                    
                    if material is not None:
                        if len(material.texture_filename) > 0:
                            texture_path = (
                                HOME + "/.rix/jrdf/models/" + self.name + 
                                "/assets/" + material.texture_filename
                            )
                            
                            if os.path.exists(texture_path):
                                print(f"Loading texture: {texture_path}")
                                success = self._apply_texture_to_geometry(geometry, texture_path, material)
                                material_info["has_texture"] = success
                                material_info["texture_path"] = texture_path
                                
                                if not success:
                                    print(f"Failed to apply texture, using color instead")
                                    if isinstance(geometry, o3d.geometry.TriangleMesh):
                                        geometry.paint_uniform_color(material.color[:3])
                                    material_info["color"] = material.color[:3]
                            else:
                                print(f"Texture file not found: {texture_path}")
                                if isinstance(geometry, o3d.geometry.TriangleMesh):
                                    geometry.paint_uniform_color(material.color[:3])
                                material_info["color"] = material.color[:3]
                        else:
                            # No texture, use color
                            if isinstance(geometry, o3d.geometry.TriangleMesh):
                                geometry.paint_uniform_color(material.color[:3])
                            elif isinstance(geometry, o3d.geometry.LineSet):
                                geometry.paint_uniform_color(material.color[:3])
                            material_info["color"] = material.color[:3]
                    else:
                        # No material specified, use default color
                        if isinstance(geometry, o3d.geometry.TriangleMesh):
                            geometry.paint_uniform_color(default_color)
                        elif isinstance(geometry, o3d.geometry.LineSet):
                            geometry.paint_uniform_color(default_color)
                        material_info["color"] = default_color

                    visuals.append(geometry)
                    visual_origins.append(visual.origin)
                    materials.append(material_info)

        return link_name, visuals, visual_origins, materials
    
    def _apply_texture_to_geometry(self, geometry: Union[o3d.geometry.TriangleMesh, o3d.geometry.LineSet], 
                                  texture_path: str, material: Material) -> bool:
        """Apply texture to geometry with proper UV mapping and validation"""
        try:
            if not isinstance(geometry, o3d.geometry.TriangleMesh):
                return False  # Only triangle meshes support textures
                
            # Load texture image
            texture_image = o3d.io.read_image(texture_path)
            if texture_image.is_empty():
                print(f"Failed to load texture image: {texture_path}")
                return False
            
            # Store texture in cache
            self.textures[texture_path] = texture_image
            
            # Check if geometry has UV coordinates
            has_uvs = (hasattr(geometry, 'triangle_uvs') and 
                      len(geometry.triangle_uvs) > 0)
            
            if not has_uvs:
                print("Warning: No UV coordinates found, generating basic UV mapping")
                # Try to generate basic UV coordinates if missing
                self._generate_basic_uv_coordinates(geometry)
                has_uvs = (hasattr(geometry, 'triangle_uvs') and 
                          len(geometry.triangle_uvs) > 0)
            
            if not has_uvs:
                print("Warning: Could not create UV coordinates for textured mesh")
                return False
            
            # Apply texture using modern Open3D approach
            try:
                # Modern Open3D texture application
                geometry.textures = [texture_image]
                
                # Store additional texture metadata
                if not hasattr(geometry, 'texture_metadata'):
                    geometry.texture_metadata = {}
                geometry.texture_metadata['texture_path'] = texture_path
                geometry.texture_metadata['material'] = material
                
                print(f"Successfully applied texture: {texture_path}")
                return True
                
            except Exception as e:
                print(f"Failed to apply texture with modern method: {e}")
                # Fallback: just store the texture info for manual handling
                if not hasattr(geometry, 'texture_metadata'):
                    geometry.texture_metadata = {}
                geometry.texture_metadata['texture_path'] = texture_path
                geometry.texture_metadata['texture_image'] = texture_image
                geometry.texture_metadata['material'] = material
                return False
                
        except Exception as e:
            print(f"Error applying texture: {e}")
            return False
    
    def _generate_basic_uv_coordinates(self, mesh: o3d.geometry.TriangleMesh) -> None:
        """Generate basic UV coordinates for a mesh when none are available"""
        try:
            vertices = np.asarray(mesh.vertices)
            triangles = np.asarray(mesh.triangles)
            
            if len(vertices) == 0 or len(triangles) == 0:
                return
            
            # Simple spherical projection for UV mapping
            uv_coords = []
            for vertex in vertices:
                # Normalize vertex
                norm = np.linalg.norm(vertex)
                if norm > 0:
                    normalized = vertex / norm
                    # Spherical coordinates
                    u = 0.5 + np.arctan2(normalized[2], normalized[0]) / (2 * np.pi)
                    v = 0.5 - np.arcsin(normalized[1]) / np.pi
                else:
                    u, v = 0.5, 0.5
                uv_coords.append([u, v])
            
            # Map to triangles
            triangle_uvs = []
            for triangle in triangles:
                for vertex_idx in triangle:
                    if vertex_idx < len(uv_coords):
                        triangle_uvs.append(uv_coords[vertex_idx])
                    else:
                        triangle_uvs.append([0.0, 0.0])
            
            if triangle_uvs:
                mesh.triangle_uvs = o3d.utility.Vector2dVector(triangle_uvs)
                
        except Exception as e:
            print(f"Error generating basic UV coordinates: {e}")

    def parse_dae_mesh(self, filename: str) -> List[Union[o3d.geometry.TriangleMesh, o3d.geometry.LineSet]]:
        """Enhanced Collada parser supporting multiple primitive types"""
        try:
            import collada.triangleset
            import collada.polylist
            import collada.lineset
        except ImportError:
            print("Warning: Full collada support not available, using basic parsing")
            return self._parse_dae_basic(filename)
            
        try:
            mesh = collada.Collada(
                filename, ignore=[collada.DaeBrokenRefError, collada.DaeError]
            )
        except Exception as e:
            print(f"Error loading Collada file: {e}")
            return []

        if len(mesh.geometries) == 0:
            return []

        geometries_o3d = []
        
        for geometry in mesh.geometries:
            for prim in geometry.primitives:
                try:
                    if isinstance(prim, collada.triangleset.TriangleSet):
                        # Handle triangle sets directly
                        geom = self._convert_triangle_set(prim)
                        if geom is not None:
                            geometries_o3d.append(geom)
                            
                    elif isinstance(prim, collada.polylist.Polylist):
                        # Convert polylist to triangles
                        try:
                            triangle_set = prim.triangleset()
                            geom = self._convert_triangle_set(triangle_set)
                            if geom is not None:
                                geometries_o3d.append(geom)
                        except Exception as e:
                            print(f"Error converting polylist to triangles: {e}")
                            
                    elif hasattr(collada, 'lineset') and isinstance(prim, collada.lineset.LineSet):
                        # Handle line sets
                        geom = self._convert_line_set(prim)
                        if geom is not None:
                            geometries_o3d.append(geom)
                            
                    elif hasattr(prim, 'triangleset'):
                        # Try to convert other primitives to triangles
                        try:
                            triangle_set = prim.triangleset()
                            geom = self._convert_triangle_set(triangle_set)
                            if geom is not None:
                                geometries_o3d.append(geom)
                        except Exception as e:
                            print(f"Error converting {type(prim)} to triangles: {e}")
                    else:
                        print(f"Skipping unsupported primitive type: {type(prim)}")
                        
                except Exception as e:
                    print(f"Error processing primitive {type(prim)}: {e}")
                    continue

        return geometries_o3d
    
    def _convert_triangle_set(self, triangle_set) -> Optional[o3d.geometry.TriangleMesh]:
        """Convert a triangle set to Open3D TriangleMesh"""
        try:
            vertices = triangle_set.vertex.reshape(-1, 3).astype(np.float64)
            indices = triangle_set.vertex_index.astype(np.int32)
            
            if len(vertices) == 0 or len(indices) == 0:
                return None

            # Create mesh
            mesh_o3d = o3d.geometry.TriangleMesh()
            mesh_o3d.vertices = o3d.utility.Vector3dVector(vertices)
            mesh_o3d.triangles = o3d.utility.Vector3iVector(indices.reshape(-1, 3))
            
            # Add normals if available
            if hasattr(triangle_set, 'normal') and triangle_set.normal is not None:
                normals = triangle_set.normal.reshape(-1, 3).astype(np.float64)
                if len(normals) == len(vertices):
                    mesh_o3d.vertex_normals = o3d.utility.Vector3dVector(normals)
            
            # Add texture coordinates if available
            if hasattr(triangle_set, 'texcoord') and triangle_set.texcoord is not None:
                try:
                    texcoords = triangle_set.texcoord.reshape(-1, 2).astype(np.float64)
                    if len(texcoords) > 0:
                        # Map UV coordinates to triangles
                        if hasattr(triangle_set, 'texcoord_index'):
                            uv_indices = triangle_set.texcoord_index.astype(np.int32)
                            triangle_uvs = []
                            for tri_idx in range(len(indices) // 3):
                                for i in range(3):
                                    idx = tri_idx * 3 + i
                                    if idx < len(uv_indices):
                                        uv_idx = uv_indices[idx]
                                        if uv_idx < len(texcoords):
                                            triangle_uvs.append(texcoords[uv_idx])
                                        else:
                                            triangle_uvs.append([0.0, 0.0])
                                    else:
                                        triangle_uvs.append([0.0, 0.0])
                            
                            if len(triangle_uvs) > 0:
                                mesh_o3d.triangle_uvs = o3d.utility.Vector2dVector(triangle_uvs)
                except Exception as e:
                    print(f"Warning: Could not process texture coordinates: {e}")
            
            mesh_o3d.compute_vertex_normals()
            mesh_o3d.compute_triangle_normals()
            return mesh_o3d
            
        except Exception as e:
            print(f"Error converting triangle set: {e}")
            return None
    
    def _convert_line_set(self, line_set) -> Optional[o3d.geometry.LineSet]:
        """Convert a line set to Open3D LineSet with validation"""
        try:
            vertices = line_set.vertex.reshape(-1, 3).astype(np.float64)
            
            if len(vertices) == 0:
                print("Warning: Empty line set vertices, skipping")
                return None
            
            # Create line set
            line_set_o3d = o3d.geometry.LineSet()
            line_set_o3d.points = o3d.utility.Vector3dVector(vertices)
            
            lines = []
            
            # Create lines from vertex indices
            if hasattr(line_set, 'vertex_index') and line_set.vertex_index is not None:
                indices = line_set.vertex_index.astype(np.int32)
                for i in range(0, len(indices) - 1, 2):
                    if i + 1 < len(indices):
                        idx1, idx2 = indices[i], indices[i + 1]
                        # Validate indices are within bounds
                        if 0 <= idx1 < len(vertices) and 0 <= idx2 < len(vertices) and idx1 != idx2:
                            lines.append([idx1, idx2])
            else:
                # Create sequential lines if no indices provided
                for i in range(len(vertices) - 1):
                    lines.append([i, i + 1])
            
            # Only create LineSet if we have valid lines
            if lines:
                line_set_o3d.lines = o3d.utility.Vector2iVector(lines)
                return line_set_o3d
            else:
                print("Warning: No valid lines found in line set, skipping")
                return None
            
        except Exception as e:
            print(f"Error converting line set: {e}")
            return None
    
    def _parse_dae_basic(self, filename: str) -> List[o3d.geometry.TriangleMesh]:
        """Basic Collada parser fallback"""
        try:
            mesh = collada.Collada(
                filename, ignore=[collada.DaeBrokenRefError, collada.DaeError]
            )
            
            if len(mesh.geometries) == 0:
                return []

            meshes_o3d = []
            for geometry in mesh.geometries:
                for prim in geometry.primitives:
                    try:
                        # Try to get vertices and indices using basic attributes
                        vertices = None
                        indices = None
                        
                        if hasattr(prim, 'vertex'):
                            vertices = prim.vertex.reshape(-1, 3).astype(np.float64)
                        if hasattr(prim, 'vertex_index'):
                            indices = prim.vertex_index.astype(np.int32)
                            
                        if vertices is not None and indices is not None and len(vertices) > 0:
                            mesh_o3d = o3d.geometry.TriangleMesh()
                            mesh_o3d.vertices = o3d.utility.Vector3dVector(vertices)
                            mesh_o3d.triangles = o3d.utility.Vector3iVector(indices.reshape(-1, 3))
                            mesh_o3d.compute_vertex_normals()
                            mesh_o3d.compute_triangle_normals()
                            meshes_o3d.append(mesh_o3d)
                            
                    except Exception as e:
                        print(f"Error in basic DAE parsing: {e}")
                        continue
                        
            return meshes_o3d
            
        except Exception as e:
            print(f"Error in basic Collada parsing: {e}")
            return []
