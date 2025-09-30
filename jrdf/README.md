# URDF to JSON Converter

This tool converts [URDF](http://wiki.ros.org/urdf) (Unified Robot Description Format) files into a JSON format for enhanced readability.

---

## Features

- Parses URDF files using [`urdf_parser_py`](https://github.com/ros/urdf_parser_py)
- Converts robot links, joints, visuals, collisions, inertial properties, and materials to JSON
- Supports mesh, box, cylinder, and sphere geometries
- Handles multiple visuals and collisions per link
- Looks up mesh files in `~/.rix/models/`
- Outputs a `.json` file with the same name as the input `.urdf`

---

## Requirements

- Python 3.12
- `urdf_parser_py`

---

## Usage

```sh
jrdf <robot.urdf>
```

This will generate `<robot.json>` in the same directory.

---

## Notes

- Mesh files referenced in the URDF should be placed in `~/.rix/models/`.
- Warnings are printed if mesh files cannot be found.

---

## Example

```sh
jrdf my_robot.urdf
# Output: my_robot.json
```
---

## License

See [LICENSE.md](LICENSE.md) for details.

---