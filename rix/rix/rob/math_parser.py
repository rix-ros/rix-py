import numpy as np
from scipy.spatial.transform import Rotation as R

MATH_BINDINGS: dict[str, float] = {
    "M_PI": np.pi,
    "M_PI_2": np.pi / 2,
    "M_PI_4": np.pi / 4,
    "M_1_PI": 1 / np.pi,
    "M_2_PI": 2 / np.pi,
    "M_2_SQRTPI": 2 / np.sqrt(np.pi),
    "M_SQRT2": np.sqrt(2),
    "M_SQRT1_2": 1 / np.sqrt(2),
    "M_E": np.e,
    "M_LOG2E": np.log2(np.e),
    "M_LOG10E": np.log10(np.e),
    "M_LN2": np.log(2),
    "M_LN10": np.log(10),
}


def parse_expression(expr: str, constants: dict[str, float]) -> float:
    """Parse a mathematical expression with given constants.

    Args:
        expr (str): The mathematical expression to parse.
        constants (dict): A dictionary of constants to use in the expression.

    Returns:
        float: The evaluated result of the expression.
    """
    try:
        # Evaluate the expression safely
        result = eval(expr, {"__builtins__": None}, constants)
    except Exception as e:
        raise ValueError(f"Error parsing expression '{expr}': {e}")

    return result

def parse_number_or_expression(e: str | float | int, constants: dict[str, float]) -> float:
    if isinstance(e, str):
        return parse_expression(e, constants)
    elif isinstance(e, float):
        return e
    elif isinstance(e, int):
        return float(e)
    else:
        raise ValueError(f"Invalid element type: {type(e)}. Must be str or float.")

def parse_vector3(vec: list[str | float | int] | None, constants: dict[str, float]) -> np.ndarray:
    """Parse a 3D vector with possible mathematical expressions.

    Args:
        vec (list): A list of three elements, each can be a float or a string expression.
        constants (dict): A dictionary of constants to use in the expressions.

    Returns:
        np.ndarray: A numpy array representing the 3D vector.
    """
    if vec is None:
        return np.array([0.0, 0.0, 0.0])
    
    if len(vec) != 3:
        raise ValueError("Input must be a list of three elements.")

    return np.array([parse_number_or_expression(e, constants) for e in vec])

def parse_vector4(vec: list[str | float | int] | None, constants: dict[str, float]) -> np.ndarray:
    """Parse a 4D vector with possible mathematical expressions.

    Args:
        vec (list): A list of four elements, each can be a float or a string expression.
        constants (dict): A dictionary of constants to use in the expressions.

    Returns:
        np.ndarray: A numpy array representing the 4D vector.
    """
    if vec is None:
        return np.array([0.0, 0.0, 0.0, 1.0])
    
    if len(vec) != 4:
        raise ValueError("Input must be a list of four elements.")

    return np.array([parse_number_or_expression(e, constants) for e in vec])

def parse_origin(origin: dict[str, any] | None, constants: dict[str, float]) -> np.ndarray:
    if origin is None:
        return np.eye(4)

    # Default values
    xyz = [0.0, 0.0, 0.0]
    rpy = [0.0, 0.0, 0.0]

    if "xyz" in origin:
        xyz = parse_vector3(origin["xyz"], constants)
    if "rpy" in origin:
        rpy = parse_vector3(origin["rpy"], constants)

    # Create transformation matrix
    T = np.eye(4)
    T[:3, 3] = xyz
    R_mat = R.from_euler("xyz", rpy).as_matrix()
    T[:3, :3] = R_mat

    return T