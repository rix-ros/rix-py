# `jrdf`: JSON Robot Description Format CLI

JRDF is a command-line tool for managing robot models in the JSON Robot Description Format (JRDF). It supports conversion from URDF, validation, visualization, and asset management for robot models.

---
## Features

- **Convert URDF to JRDF:** Easily convert existing URDF files to JRDF format.
- **List Models:** Show all available JRDF models.
- **Validate Models:** Check the structure of JRDF JSON files.
- **Visualize Models:** Render robot models using Open3D.

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

### Materials

Materials can be defined globally or per visual element, supporting either RGBA color or texture filename.

### Expressions

Numeric fields may accept either a number or an expression string. The expression string must only use simple operators (`+`, `-`, `*`, and `/`). Parentheses are permitted. The following table contains predefined mathematical constants that can be used in JRDF.

| Name       | Value        |
|------------|--------------|
| M_PI       | pi           |
| M_PI_2     | pi / 2       |
| M_PI_4     | pi / 4       |
| M_1_PI     | 1 / pi       |
| M_2_PI     | 2 / pi       |
| M_2_SQRTPI | 2 / sqrt(pi) |
| M_SQRT2    | sqrt(2)      |
| M_SQRT1_2  | 1 / sqrt(2)  |
| M_E        | e            |
| M_LOG2E    | log2(e)      |
| M_LOG10E   | log10(e)     |
| M_LN2      | ln(2)        |
| M_LN10     | ln(10)       |

### Example

```json
{
  "name": "MyRobot",
  "materials": [
    {
      "name": "dark_blue",
      "color": [0, 0.15294, 0.29804, 1]
    }
  ],
  "constants": [
    {
      "name": "x",
      "value": 0.5
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
            "size": ["x", "x", 1]
          },
          "material": {
            "name": "dark_blue"
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
            "xyz": ["x/2", "x/2", 1.25],
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