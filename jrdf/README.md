# URDF to JSON Converter (`jrdf`)

This tool converts [URDF](http://wiki.ros.org/urdf) (Unified Robot Description Format) files into a JSON format for enhanced readability and provides utilities for working with robot models.

---

## Features

- Parses URDF files using [`urdf_parser_py`](https://github.com/ros/urdf_parser_py)
- Converts robot links, joints, visuals, collisions, inertial properties, and materials to JSON
- Supports mesh, box, cylinder, and sphere geometries
- Handles multiple visuals and collisions per link
- Looks up mesh files in `~/.rix/models/`
- Outputs a `.json` file with the same name as the input `.urdf`
- Installs mesh files to the local model directory
- Validates JRDF JSON files
- Visualizes robot models from JRDF JSON files

---

## Requirements

- Python 3.12
- `urdf_parser_py`
- `open3d` (for visualization)

---

## Usage

```sh
jrdf <function> [arguments]
```

### Functions

- `convert <input.urdf> [output.json]`  
  Convert a URDF file to JSON.

- `mesh <name> <mesh file/dir>`  
  Install mesh files to `~/.rix/models/<name>/`.

- `validate <input.json>`  
  Validate a JRDF JSON file.

- `visualize <input.json>`  
  Visualize a JRDF JSON file.

---

## Notes

- Mesh files referenced in the URDF should be placed in `~/.rix/models/`.
- Warnings are printed if mesh files cannot be found.
- Visualization requires `open3d` to be installed.

---

## Examples

Convert URDF to JSON:
```sh
jrdf convert my_robot.urdf
# Output: my_robot.json
```

Install mesh files:
```sh
jrdf mesh my_robot meshes/
```

Validate a JRDF file:
```sh
jrdf validate my_robot.json
```

Visualize a robot model:
```sh
jrdf visualize my_robot.json
```

---

## License

See [LICENSE.md](LICENSE.md) for details.

---