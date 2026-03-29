import os
import importlib

import yaml

from rix.core import Node
from rix.msg.message_base import Message
from rix.msg.types import (
    ArithmeticProperty,
    ArithmeticVectorProperty,
    ArithmeticArrayProperty,
    StringProperty,
    StringVectorProperty,
    StringArrayProperty,
    MessageProperty,
    MessageVectorProperty,
    MessageArrayProperty,
    PointerProperty,
    PointerVectorProperty,
    PointerArrayProperty,
)
from rix.sys_msgs import SystemInfo

ROOT = os.getenv("HOME")


def hash_to_str(hash: list[int]) -> str:
    return "".join(f"{part:016x}" for part in hash)


def init_node() -> Node | None:
    node = Node("rixinfo")
    if not node.ok():
        print("Error: Failed to initialize node.")
        return None
    return node


def fetch_system_info(node: Node) -> SystemInfo | None:
    system_info = SystemInfo()
    if not node.get_system_info(system_info):
        print("Error: Failed to get system info.")
        return None
    return system_info


def load_topic_index() -> dict[str, str]:
    topics_by_hash: dict[str, str] = {}
    index_path = os.path.join(ROOT, ".rix", "rixmsg", "index.txt")
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    hash_val, topic = line.split()
                    topics_by_hash[hash_val] = topic
    return topics_by_hash


def resolve_message_class(message_name: str, use_msg_prefix: bool = False):
    try:
        package, name = message_name.split("/")
    except ValueError:
        print("Error: Message name must be in the form <package>/<name>.")
        return None

    if use_msg_prefix:
        module_path = f"rix.msg.{package}.{name}"
    else:
        module_path = f"rix.{package}.{name}"

    try:
        module = importlib.import_module(module_path)
        return getattr(module, name)
    except (ModuleNotFoundError, AttributeError):
        print(f"Error: Could not import '{name}' from {module_path}.")
        return None


_PRIMITIVE_DESCRIPTORS = (
    ArithmeticProperty,
    ArithmeticVectorProperty,
    ArithmeticArrayProperty,
    StringProperty,
    StringVectorProperty,
    StringArrayProperty,
)
_MESSAGE_DESCRIPTORS = (
    MessageProperty,
    MessageVectorProperty,
    MessageArrayProperty,
)
_POINTER_DESCRIPTORS = (
    PointerProperty,
    PointerVectorProperty,
    PointerArrayProperty,
)


def message_to_dict(msg: Message) -> dict:
    """Convert a RIX Message to a nested Python dictionary."""
    result = {}
    property_names = getattr(msg, "_property_names", [])
    cls = type(msg)
    for name in property_names:
        descriptor = cls.__dict__.get(name)
        value = getattr(msg, name)

        if descriptor is not None and isinstance(descriptor, _MESSAGE_DESCRIPTORS):
            if isinstance(descriptor, MessageProperty):
                result[name] = message_to_dict(value)
            else:
                result[name] = [message_to_dict(item) for item in value]
        elif descriptor is not None and isinstance(descriptor, _POINTER_DESCRIPTORS):
            if value is None:
                result[name] = None
            elif isinstance(value, (memoryview, bytes, bytearray)):
                result[name] = f"<{len(value)} bytes>"
            elif isinstance(value, list):
                result[name] = [f"<{len(v)} bytes>" if isinstance(v, (memoryview, bytes, bytearray)) else str(v) for v in value]
            else:
                result[name] = str(value)
        else:
            result[name] = value
    return result


def message_to_yaml(msg: Message) -> str:
    """Convert a RIX Message to a YAML string."""
    return yaml.dump(message_to_dict(msg), default_flow_style=False, sort_keys=False).rstrip()
