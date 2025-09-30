# URDF to JSON Converter

This tool converts [URDF](http://wiki.ros.org/urdf) (Unified Robot Description Format) files into a structured JSON format for easier integration with other systems.

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

- Python 3.10+
- `urdf_parser_py`
- `numpy`

Install dependencies:
```sh
pip install urdf_parser_py numpy
```

---

## Usage

```sh
python3 urdf_to_json.py <robot.urdf>
```

This will generate `<robot.json>` in the same directory.

---

## Notes

- Mesh files referenced in the URDF should be placed in `~/.rix/models/`.
- Warnings are printed if mesh files cannot be found.

---

## Example

```sh
python urdf_to_json.py my_robot.urdf
# Output: my_robot.json
```
---

## License

See [LICENSE.md](LICENSE.md) for details.

---