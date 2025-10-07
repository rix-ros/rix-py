# `jrdf`: JSON Robot Description Format CLI

JRDF is a command-line tool for managing robot models in the JSON Robot Description Format (JRDF). It supports conversion from URDF, validation, visualization, and asset management for robot models.

---
## Features

- **Convert URDF to JRDF:** Easily convert existing URDF files to JRDF format.
- **List Models:** Show all available JRDF models.
- **Validate Models:** Check the structure of JRDF JSON files.
- **Visualize Models:** Render robot models using Open3D.
- **Advanced Texture Mapping:** Proper UV coordinate generation and texture application
- **Multiple Collada Primitive Types:** Support for TriangleSets, PolygonLists, and LineSets
- **Modern Visualization:** Upgraded visualization system with better texture support
- **Enhanced Material System:** Comprehensive material and texture management
- **Interactive Model Manipulation:** Runtime transform updates and color changes

---
## Installation

Ensure you have Python 3.12 and the required dependencies installed:

- `open3d`
- `urdf_parser_py`
- `pycollada`
- RIX-PY core libraries (installed via the main RIX-PY install script)

---
## Usage

Run the CLI with:

```sh
jrdf <function> [arguments]
```

### Functions

- `create <name> <json | urdf> [asset directory]`  
  Create a JRDF model from a JSON or URDF file. Optionally copy assets.

- `list`  
  List all JRDF models in `~/.rix/jrdf/models`.

- `validate <input.json>`  
  Validate a JRDF JSON file.

- `visualize <name>`  
  Visualize a JRDF model using Open3D.

### Examples

**Convert a URDF to JRDF:**
```sh
jrdf create my_robot my_robot.urdf ./assets
```

**List models:**
```sh
jrdf list
```

**Validate a model:**
```sh
jrdf validate ~/.rix/jrdf/models/my_robot/model.json
```

**Visualize a model:**
```sh
jrdf visualize my_robot
```

---
## Open3D Robot Model

### Features

- **Automatic UV Coordinate Generation** for primitive shapes (box, cylinder, sphere)
- **Collada Texture Extraction** from DAE files when available
- **Fallback Texture Handling** for missing or failed textures
- **Multiple Texture Formats**: PNG, JPG, BMP, TGA
- **TriangleSets, PolygonLists, LineSets**: Direct conversion from Collada
- **Modern Visualization**: Open3D 0.13+ API
- **Interactive Features**: Runtime transform and color updates
- **Robust Error Handling**: Continues processing even if some primitives fail

### Usage Examples

**Basic Visualization**
```python
from jrdf.src.open3d_util import Open3DRobotModel

# Create robot model
robot = Open3DRobotModel("fetch", use_modern_visualizer=True)

# Get all geometries
geometries = robot.get_all_geometries()

# Simple visualization
import open3d as o3d
o3d.visualization.draw_geometries(geometries, window_name="My Robot")
```

**Advanced Material Handling**
```python
# Access material information
for link_name, materials in robot.materials.items():
    for i, material in enumerate(materials):
        if material["has_texture"]:
            print(f"Link {link_name} geometry {i} has texture: {material['texture_path']}")
        else:
            print(f"Link {link_name} geometry {i} uses color: {material['color']}")
```

**Custom Visualization Loop**
```python
import open3d as o3d
import numpy as np

# Create visualizer
vis = o3d.visualization.Visualizer()
vis.create_window(window_name="Interactive Robot Viewer", width=1200, height=800)

# Add geometries
geometries = robot.get_all_geometries()
for geom in geometries:
    vis.add_geometry(geom)

# Animation loop
def animate_joint():
    angle = 0
    while True:
        # Update joint angle
        transform = np.eye(4)
        transform[:3, :3] = rotation_matrix_z(angle)
        robot.update_link_transform("joint_link", transform)
        
        # Update visualization
        vis.update_geometry()
        vis.poll_events()
        vis.update_renderer()
        
        angle += 0.01
        if angle > 2 * np.pi:
            angle = 0

# Run animation
animate_joint()
```

### Error Handling

```python
try:
    robot = Open3DRobotModel("my_robot")
    geometries = robot.get_all_geometries()
    
    if not geometries:
        print("No geometries loaded")
    else:
        print(f"Successfully loaded {len(geometries)} geometries")
        
except FileNotFoundError as e:
    print(f"Robot model files not found: {e}")
except ValueError as e:
    print(f"Invalid robot model: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Performance Considerations

1. **Large Models**: The system handles large models by streaming geometry data
2. **Texture Memory**: Textures are cached to avoid reloading
3. **UV Generation**: UV coordinates are generated on-demand for primitive shapes
4. **Fallback Mechanisms**: Multiple fallback paths ensure robustness

### Compatibility

- **Open3D Versions**: Compatible with Open3D 0.13+ (with fallbacks for older versions)
- **Python**: Requires Python 3.8+
- **Dependencies**: NumPy, Open3D, Collada (pycollada)

### Troubleshooting

**Common Issues**

1. **"visualization" not found**: Your Open3D installation may not include GUI support
   - Solution: Install Open3D with GUI: `pip install open3d[gui]`

2. **Textures not displaying**: 
   - Check if texture files exist in the assets directory
   - Verify Open3D version supports textures
   - Enable modern visualizer: `use_modern_visualizer=True`

3. **Collada import errors**:
   - Install pycollada: `pip install pycollada`
   - Check DAE file format compatibility

**Debug Information**

Enable debug output:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

robot = Open3DRobotModel("robot_name", use_modern_visualizer=True)
```

This will provide detailed information about texture loading, geometry parsing, and visualization setup.

---
## JRDF File Format

JRDF files must conform to the [JRDF JSON Schema](./jrdf_schema.json). The format is designed to describe robot models in a structured and extensible way. Below are the key requirements and structure:

### Top-Level Structure

A valid JRDF file is a JSON object with the following required fields:

- `name`: The robot's name (string, must match `^[a-zA-Z_][a-zA-Z0-9_]*$`).
- `joints`: Array of joint objects.
- `links`: Array of link objects.

Optional fields include:

- `constants`: Array of named constants (for parameterization).
- `materials`: Array of global material definitions.

### Links

Each link object must have:

- `name`: Unique link name.
- Optional `inertial`: Mass, inertia matrix, and origin.
- Optional `visuals`: Array of visual elements (geometry, origin, material).
- Optional `collisions`: Array of collision elements (geometry, origin).

### Joints

Each joint object must have:

- `name`: Unique joint name.
- `parent`: Name of the parent link.
- `child`: Name of the child link.
- `type`: Joint type (`fixed`, `revolute`, `continuous`, or `prismatic`).

Depending on the joint type, additional fields may be required:
- For `revolute` and `prismatic` joints: `axis` and `limits` are required.
- For `continuous` joints: `axis` is required.
- For `fixed` joints: `axis`, `limits`, `dynamics`, and `safety` must not be present.

### Geometry

Supported geometry types for visuals and collisions:

- `box`: Requires `size` (3-element array).
- `cylinder`: Requires `radius` and `length`.
- `sphere`: Requires `radius`.
- `mesh`: Requires `filename`, optional `scale`.

#### Supported Mesh Formats
- **STL**: Standard Tessellation Language
- **OBJ**: Wavefront OBJ
- **PLY**: Polygon File Format
- **DAE**: Collada

#### Supported Texture Formats
- **PNG**: Portable Network Graphics
- **JPG/JPEG**: Joint Photographic Experts Group
- **BMP**: Bitmap
- **TGA**: Targa

### Macros

Use [`jsonmacros`](https://github.com/rix-ros/jsonmacros) to parse parameterized or simple macro definitions and file includes.

### Example

```json
{
  "name": "MyRobot",
  "$macros": [
    {
      "name": "dark_blue",
      "body": [0, 0.15294, 0.29804, 1]
    },
    {
        "name": "x",
        "body": 0.5
    }
  ],
  "joints": [
    {
      "name": "waist",
      "parent": "base",
      "child": "arm",
      "type": "fixed"
    }
  ],
  "links": [
    {
      "name": "base",
      "visuals": [
        {
          "geometry": {
            "type": "box",
            "size": ["${x}", "${x}", 1]
          },
          "material": {
            "color": "${dark_blue}"
          }
        }
      ]
    },
    {
      "name": "arm",
      "visuals": [
        {
          "geometry": {
            "type": "cylinder",
            "radius": 0.25,
            "length": 0.5
          },
          "material": {
            "color": [1, 0.79608, 0.01961, 1]
          },
          "origin": {
            "xyz": ["${x/2}", "${x/2}", 1.25],
            "rpy": [0, 0, 0]
          }
        }
      ]
    }
  ]
}
```

See the provided JRDF [`SimpleBot.json`](../examples/SimpleBot.json) for a more complete example of all the features that JRDF supports!

---
## License

See [LICENSE.md](../../LICENSE.md) for details.

---