# JRDF: JSON Robot Description Format CLI

JRDF is a command-line tool for managing robot models in the JSON Robot Description Format (JRDF). It supports conversion from URDF, validation, visualization, and asset management for robot models.

## Features

- **Convert URDF to JRDF:** Easily convert existing URDF files to JRDF format.
- **List Models:** Show all available JRDF models.
- **Validate Models:** Check the structure of JRDF JSON files.
- **Visualize Models:** Render robot models using Open3D.

## Installation

Ensure you have Python 3.12 and the required dependencies installed:

- `open3d`
- `urdf_parser_py`
- `pycollada`
- RIX-PY core libraries (installed via the main RIX-PY install script)

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

## File Structure

- Models are stored in: `~/.rix/jrdf/models/<name>/model.json`
- Assets are stored in: `~/.rix/jrdf/models/<name>/assets/`

## License

See [LICENSE.md](../../LICENSE.md) for details.

---