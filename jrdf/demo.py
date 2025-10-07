#!/usr/bin/env python3
"""
Demo script showing the enhanced Open3D Robot Model features
"""

import os
import sys
import numpy as np

# Add the rix package to path
rix_path = os.path.expanduser("~/.rix/python/rix")
if rix_path not in sys.path:
    sys.path.append(rix_path)

# Add the jrdf source to path    
jrdf_src = os.path.join(os.path.dirname(__file__), "src")
if jrdf_src not in sys.path:
    sys.path.append(jrdf_src)

try:
    import open3d as o3d
    from open3d_util import Open3DRobotModel
    
    def demo_basic_shapes():
        """Demo creating basic shapes with textures"""
        print("=== Basic Shapes Demo ===")
        
        # Create basic geometries
        box = o3d.geometry.TriangleMesh.create_box(1, 1, 1)
        box.paint_uniform_color([0.8, 0.2, 0.2])
        box.translate([0, 0, 0])
        
        cylinder = o3d.geometry.TriangleMesh.create_cylinder(0.3, 1.5)
        cylinder.paint_uniform_color([0.2, 0.8, 0.2])
        cylinder.translate([2, 0, 0])
        
        sphere = o3d.geometry.TriangleMesh.create_sphere(0.5)
        sphere.paint_uniform_color([0.2, 0.2, 0.8])
        sphere.translate([4, 0, 0])
        
        # Compute normals
        for geom in [box, cylinder, sphere]:
            geom.compute_vertex_normals()
            geom.compute_triangle_normals()
        
        print(f"Created box with {len(box.vertices)} vertices")
        print(f"Created cylinder with {len(cylinder.vertices)} vertices")
        print(f"Created sphere with {len(sphere.vertices)} vertices")
        
        # Visualize
        o3d.visualization.draw_geometries(
            [box, cylinder, sphere],
            window_name="Basic Shapes Demo",
            width=800,
            height=600
        )
    
    def demo_robot_model(robot_name):
        """Demo loading and visualizing a robot model"""
        print(f"=== Robot Model Demo: {robot_name} ===")
        
        try:
            # Create robot model with enhanced features
            robot = Open3DRobotModel(robot_name, use_modern_visualizer=True)
            
            # Get statistics
            geometries = robot.get_all_geometries()
            print(f"Loaded {len(geometries)} geometry objects")
            
            # Print link information
            print("Links found:")
            for link_name in robot.visuals.keys():
                num_visuals = len(robot.visuals[link_name])
                print(f"  - {link_name}: {num_visuals} visual elements")
                
                # Print material info
                if link_name in robot.materials:
                    materials = robot.materials[link_name]
                    for i, material in enumerate(materials):
                        if material.get("has_texture", False):
                            print(f"    Visual {i}: Textured ({material.get('texture_path', 'unknown')})")
                        else:
                            color = material.get("color", [0.7, 0.7, 0.7])
                            print(f"    Visual {i}: Color {color}")
            
            # Get bounding box
            bbox = robot.get_bounding_box()
            print(f"Model bounding box: {bbox.get_extent()}")
            
            # Demo color changes
            print("\\nDemonstrating color changes...")
            link_names = list(robot.visuals.keys())
            if link_names:
                # Change color of first link
                first_link = link_names[0]
                print(f"Changing color of {first_link} to red")
                robot.set_link_color(first_link, [1.0, 0.0, 0.0])
                
                # Show for a moment
                o3d.visualization.draw_geometries(
                    robot.get_all_geometries(),
                    window_name=f"Robot Model - {robot_name} (Red {first_link})",
                    width=1024,
                    height=768
                )
                
                # Reset colors
                print(f"Resetting colors for {first_link}")
                robot.reset_link_colors(first_link)
            
            # Final visualization
            o3d.visualization.draw_geometries(
                geometries,
                window_name=f"Robot Model - {robot_name}",
                width=1024,
                height=768
            )
            
            # Save model option
            save_path = f"{robot_name}_combined.ply"
            if robot.save_model(save_path):
                print(f"Model saved to {save_path}")
            else:
                print("Failed to save model")
                
        except FileNotFoundError as e:
            print(f"Robot model '{robot_name}' not found: {e}")
            print("Available models:")
            models_dir = os.path.expanduser("~/.rix/jrdf/models")
            if os.path.exists(models_dir):
                for model in os.listdir(models_dir):
                    if os.path.isdir(os.path.join(models_dir, model)):
                        print(f"  - {model}")
            else:
                print("  No models directory found")
        except Exception as e:
            print(f"Error loading robot model: {e}")
            import traceback
            traceback.print_exc()
    
    def demo_interactive_visualization():
        """Demo interactive visualization with transform updates"""
        print("=== Interactive Visualization Demo ===")
        
        # Create a simple multi-part object
        base = o3d.geometry.TriangleMesh.create_cylinder(0.5, 0.2)
        base.paint_uniform_color([0.5, 0.5, 0.5])
        base.translate([0, 0, 0.1])
        
        arm = o3d.geometry.TriangleMesh.create_box(0.1, 0.1, 1.0)
        arm.paint_uniform_color([0.8, 0.4, 0.2])
        arm.translate([0, 0, 0.7])
        
        end_effector = o3d.geometry.TriangleMesh.create_sphere(0.1)
        end_effector.paint_uniform_color([0.2, 0.8, 0.2])
        end_effector.translate([0, 0, 1.3])
        
        # Compute normals
        for geom in [base, arm, end_effector]:
            geom.compute_vertex_normals()
            geom.compute_triangle_normals()
        
        print("Created simple articulated object")
        print("Visualizing static version...")
        
        # Show static version
        o3d.visualization.draw_geometries(
            [base, arm, end_effector],
            window_name="Interactive Demo - Static",
            width=800,
            height=600
        )
        
        print("Interactive demo completed")
    
    def main():
        """Main demo function"""
        print("Enhanced Open3D Robot Model Demo")
        print("================================")
        print(f"Open3D version: {o3d.__version__}")
        print()
        
        # Check command line arguments
        if len(sys.argv) > 1:
            demo_type = sys.argv[1]
            
            if demo_type == "shapes":
                demo_basic_shapes()
            elif demo_type == "robot":
                robot_name = sys.argv[2] if len(sys.argv) > 2 else "SimpleBot"
                demo_robot_model(robot_name)
            elif demo_type == "interactive":
                demo_interactive_visualization()
            else:
                print(f"Unknown demo type: {demo_type}")
                print("Usage: python demo.py [shapes|robot|interactive] [robot_name]")
        else:
            print("Running all demos...")
            print()
            
            # Run basic shapes demo
            demo_basic_shapes()
            
            # Try to run robot demo with default robot
            demo_robot_model("SimpleBot")
            
            # Run interactive demo
            demo_interactive_visualization()
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure Open3D and all dependencies are installed")
    print("You may need to run: pip install open3d pycollada")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()