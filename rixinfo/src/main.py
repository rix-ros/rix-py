import sys
import os

# This is necessary for using dynamically loaded message types due to PyInstaller limitations
rix_path = os.path.expanduser("~/.rix/python/rix")
sys.path.append(rix_path)

from rix.core import Node
from rix.core.socket import Socket
from rix.core.common import OPCODE
from rix.sys_msgs import SystemInfo, Status, Operation
from rix.std_msgs import Void

import importlib
import argparse
import time

ROOT = os.getenv("HOME", "")
os.environ["MPLCONFIGDIR"] = os.path.join(ROOT, ".rix", "rixinfo", ".matplotlib")
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import networkx as nx

USAGE = """rixinfo [-h] function [arg]

Functions:
  node
    list                    - List all active RIX nodes
    info <node>             - Print information about a node
    ping <node>             - Ping a node
  topic
    list                    - List all active RIX topics
    echo <topic>            - Print the messages of a topic
    hz <topic>              - Print the message rate of a topic
    bw <topic>              - Print the bandwidth of a topic
  service
    list                    - List all active RIX services
  graph                     - Display a runtime graph of the RIX environment
"""


def hash_to_str(hash: list[int]) -> str:
    return "".join(f"{part:016x}" for part in hash)


def node(args: list[str]) -> None:
    function = args[0] if len(args) > 0 else None
    if function not in ["list", "info", "ping"]:
        print("Error! node function must be one of: list, info, ping")
        return

    node = Node("rixinfo")
    if not node.ok():
        print("Error! Failed to initialize node.")
        return

    system_info = SystemInfo()
    if not node.get_system_info(system_info):
        print("Error! Failed to get system info.")
        return

    if function == "list":
        print("Active RIX nodes:")
        for n in system_info.nodes:
            print(f"  {n.name}")
        return

    if function == "info":
        arg = args[1] if len(args) > 1 else None
        if not arg:
            print("Error! 'info' requires a node name as an argument.")
            return
        node_name = arg
        node_info = next((n for n in system_info.nodes if n.name == node_name), None)
        if not node_info:
            print(f"Node '{node_name}' not found.")
            return
        print(f"Node: {node_info.name}")
        pub_topics: set[str] = set()
        sub_topics: set[str] = set()
        services: set[str] = set()
        for pub in system_info.publishers:
            if pub.node_id == node_info.id:
                pub_topics.add(pub.topic_info.name)
        for sub in system_info.subscribers:
            if sub.node_id == node_info.id:
                sub_topics.add(sub.topic_info.name)
        for srv in system_info.services:
            if srv.node_id == node_info.id:
                services.add(srv.name)

        if len(pub_topics) > 0:
            print(f"  Published Topics:")
            for topic in pub_topics:
                print(f"    {topic}")
        if len(sub_topics) > 0:
            print(f"  Subscribed Topics:")
            for topic in sub_topics:
                print(f"    {topic}")
        if len(services) > 0:
            print(f"  Services:")
            for service in services:
                print(f"    {service}")

        return

    if function == "ping":
        arg = args[1] if len(args) > 1 else None
        if not arg:
            print("Error! 'ping' requires a node name as an argument.")
            return
        node_name = arg
        node_info = next((n for n in system_info.nodes if n.name == node_name), None)
        if not node_info:
            print(f"Node '{node_name}' not found.")
            return
        print(f"Pinging node '{node_name}'...")
        endpoint = (node_info.endpoint.address, node_info.endpoint.port)

        client = Socket()
        if not client.connect(endpoint):
            print(f"Error! Failed to connect to node '{node_name}' at {endpoint}.")
            return

        msg = Void()
        if not client.send_message(OPCODE.PING, msg):
            print(f"Error! Failed to send ping to node '{node_name}'.")
            return

        status = Status()
        op = Operation()
        if not client.recv_message_with_opcode(op, status):
            print(f"Error! Failed to receive ping response from node '{node_name}'.")
            return

        if op.opcode != OPCODE.STATUS_RESPONSE:
            print(
                f"Error! Unexpected response opcode {op.opcode} from node '{node_name}'."
            )
            return

        print(f"Node '{node_name}' is alive. Status: {status.error}")
        return


def topic(args: list[str]) -> None:
    function = args[0] if len(args) > 0 else None
    if function not in ["list", "echo", "hz", "bw"]:
        print("Error! topic function must be one of: list, echo, hz, bw")
        return

    node = Node("rixinfo")
    if not node.ok():
        print("Error! Failed to initialize node.")
        return

    system_info = SystemInfo()
    if not node.get_system_info(system_info):
        print("Error! Failed to get system info.")
        return

    topics_by_hash: dict[str, str] = {}
    index_path = os.path.join(ROOT, ".rix", "rixmsg", "index.txt")
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    hash, topic = line.split()
                    topics_by_hash[hash] = topic

    if function == "list":
        print("Active RIX topics:")
        if len(system_info.topics) == 0:
            print("  No active RIX topics.")
            return
        for topic in system_info.topics:
            topic_hash = hash_to_str(topic.message_hash)
            message_name = topics_by_hash.get(topic_hash, "Unknown")
            print(f"  {topic.name} [{message_name}]")
        return

    if function == "echo":
        arg = args[1] if len(args) > 1 else None
        if not arg:
            print("Error! 'echo' requires a topic name as an argument.")
            return
        topic_name = arg
        topic_info = next((t for t in system_info.topics if t.name == topic_name), None)
        if not topic_info:
            print(f"Topic '{topic_name}' not found.")
            return
        topic_hash = hash_to_str(topic_info.message_hash)
        message_name = topics_by_hash.get(topic_hash)
        if not message_name:
            print(f"Message type for topic '{topic_name}' not found in index.")
            return
        try:
            package, name = message_name.split("/")
        except ValueError:
            print("Message name must be in the form <package>/<name>")
            return
        module_path = f"rix.msg.{package}.{name}"
        try:
            module = importlib.import_module(module_path)
            message_class = getattr(module, name)
        except (ModuleNotFoundError, AttributeError):
            print(f"Could not import '{name}' from {module_path}.")
            return

        def callback(msg) -> None:
            print(msg)

        sub = node.create_subscriber(message_class, topic_name, callback)
        if not sub.ok():
            print("Error! Failed to create subscriber.")
            return

        node.spin()
        return

    if function == "hz":
        arg = args[1] if len(args) > 1 else None
        if not arg:
            print("Error! 'hz' requires a topic name as an argument.")
            return
        topic_name = arg
        topic_info = next((t for t in system_info.topics if t.name == topic_name), None)
        if not topic_info:
            print(f"Topic '{topic_name}' not found.")
            return

        # Create subscriber to measure rate
        message_hash = topic_info.message_hash
        topic_hash = hash_to_str(message_hash)
        message_name = topics_by_hash.get(topic_hash)
        if not message_name:
            print(f"Message type for topic '{topic_name}' not found in index.")
            return
        try:
            package, name = message_name.split("/")
        except ValueError:
            print("Message name must be in the form <package>/<name>")
            return
        module_path = f"rix.msg.{package}.{name}"
        try:
            module = importlib.import_module(module_path)
            message_class = getattr(module, name)
        except (ModuleNotFoundError, AttributeError):
            print(f"Could not import '{name}' from {module_path}.")
            return

        count = 0
        current_time = time.time()

        def callback(msg) -> None:
            nonlocal count, current_time
            count += 1
            elapsed_time = time.time() - current_time
            if elapsed_time > 0:
                print(f"Current rate: {count / elapsed_time:.3f} Hz   ", end="\r")

        sub = node.create_subscriber(message_class, topic_name, callback)
        if not sub.ok():
            print("Error! Failed to create subscriber.")
            return
        print(f"Measuring message rate on topic '{topic_name}'. Press Ctrl+C to stop.")
        node.spin()
        return

    if function == "bw":
        arg = args[1] if len(args) > 1 else None
        if not arg:
            print("Error! 'bw' requires a topic name as an argument.")
            return
        topic_name = arg
        topic_info = next((t for t in system_info.topics if t.name == topic_name), None)
        if not topic_info:
            print(f"Topic '{topic_name}' not found.")
            return

        # Create subscriber to measure bandwidth
        message_hash = topic_info.message_hash
        topic_hash = hash_to_str(message_hash)
        message_name = topics_by_hash.get(topic_hash)
        if not message_name:
            print(f"Message type for topic '{topic_name}' not found in index.")
            return
        try:
            package, name = message_name.split("/")
        except ValueError:
            print("Message name must be in the form <package>/<name>")
            return
        module_path = f"rix.msg.{package}.{name}"
        try:
            module = importlib.import_module(module_path)
            message_class = getattr(module, name)
        except (ModuleNotFoundError, AttributeError):
            print(f"Could not import '{name}' from {module_path}.")
            return

        total_bytes = 0
        current_time = time.time()

        def callback(msg) -> None:
            nonlocal total_bytes, current_time
            total_bytes += msg.size()
            elapsed_time = time.time() - current_time
            if elapsed_time > 0:
                print(
                    f"Current bandwidth: {total_bytes / elapsed_time:.3f} B/s   ",
                    end="\r",
                )

        sub = node.create_subscriber(message_class, topic_name, callback)
        if not sub.ok():
            print("Error! Failed to create subscriber.")
            return
        print(f"Measuring bandwidth on topic '{topic_name}'. Press Ctrl+C to stop.")
        node.spin()
        return


def service(args: list[str]) -> None:
    function = args[0] if len(args) > 0 else None
    if function != "list":
        print("Error! service function must be: list")
        return

    node = Node("rixinfo")
    if not node.ok():
        print("Error! Failed to initialize node.")
        return

    system_info = SystemInfo()
    if not node.get_system_info(system_info):
        print("Error! Failed to get system info.")
        return

    if len(system_info.services) == 0:
        print("No active RIX services.")
        return

    print("Active RIX services:")
    for service in system_info.services:
        print(f"  {service.name}")
    return


def graph(args: list[str]) -> None:
    """Display a runtime graph of the current RIX environment."""
    node = Node("rixinfo")
    if not node.ok():
        print("Error! Failed to initialize node.")
        return

    system_info = SystemInfo()
    if not node.get_system_info(system_info):
        print("Error! Failed to get system info.")
        return

    # Create a directed graph
    G = nx.DiGraph()

    # Create mappings for unique identification
    node_id_to_name = {}

    # Add nodes to the graph using their unique IDs
    node_ids = []
    for n in system_info.nodes:
        node_id = f"node:{n.id}"
        G.add_node(node_id, node_type="node", display_name=n.name)
        node_ids.append(node_id)
        node_id_to_name[n.id] = node_id

    # Add topics as nodes and connections
    topic_names = []
    for topic in system_info.topics:
        topic_node_name = f"topic:{topic.name}"
        G.add_node(topic_node_name, node_type="topic", display_name=topic.name)
        topic_names.append(topic_node_name)

    # Add services as nodes
    service_names = []
    for service in system_info.services:
        service_node_name = f"service:{service.name}"
        G.add_node(service_node_name, node_type="service", display_name=service.name)
        service_names.append(service_node_name)

        # Connect service to its hosting node using node ID
        hosting_node_id = node_id_to_name.get(service.node_id)
        if hosting_node_id:
            G.add_edge(hosting_node_id, service_node_name)

    # Connect publishers to topics using node IDs
    for pub in system_info.publishers:
        pub_node_id = node_id_to_name.get(pub.node_id)
        topic_node_name = f"topic:{pub.topic_info.name}"
        if pub_node_id and topic_node_name in topic_names:
            G.add_edge(pub_node_id, topic_node_name)

    # Connect topics to subscribers using node IDs
    for sub in system_info.subscribers:
        sub_node_id = node_id_to_name.get(sub.node_id)
        topic_node_name = f"topic:{sub.topic_info.name}"
        if sub_node_id and topic_node_name in topic_names:
            G.add_edge(topic_node_name, sub_node_id)

    # Create the visualization
    plt.figure(figsize=(10, 10))
    pos = nx.spring_layout(G)

    # Draw different types of nodes with different colors and shapes
    node_colors = []
    node_sizes = []

    for n in G.nodes():
        node_type = G.nodes[n].get("node_type", "unknown")
        if node_type == "node":
            node_colors.append("lightblue")
            node_sizes.append(1200)
        elif node_type == "topic":
            node_colors.append("lightgreen")
            node_sizes.append(1000)
        elif node_type == "service":
            node_colors.append("lightcoral")
            node_sizes.append(800)
        else:
            node_colors.append("gray")
            node_sizes.append(600)

    # Draw the graph with improved edge styling
    nx.draw_networkx_nodes(
        G,
        pos,
        node_color=node_colors,
        node_size=node_sizes,
        alpha=0.9,
        linewidths=2,
        edgecolors="black",
    )
    nx.draw_networkx_edges(
        G,
        pos,
        edge_color="black",
        arrows=True,
        arrowsize=25,
        alpha=0.7,
        arrowstyle="->",
        width=2,
        connectionstyle="arc3,rad=0.1",
    )

    # Add labels using display names
    labels = {}
    for n in G.nodes():
        display_name = G.nodes[n].get("display_name", n)
        labels[n] = display_name

    nx.draw_networkx_labels(G, pos, labels, font_size=8, font_weight="bold")

    # Add legend
    legend_elements = [
        mlines.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="lightblue",
            markersize=10,
            label="Nodes",
        ),
        mlines.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="lightgreen",
            markersize=8,
            label="Topics",
        ),
        mlines.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="lightcoral",
            markersize=6,
            label="Services",
        ),
    ]
    plt.legend(handles=legend_elements, loc="upper right")

    plt.title("RIX Runtime Graph", size=16, weight="bold")
    plt.axis("off")
    plt.tight_layout()

    print("Displaying RIX runtime graph. Close the window to exit.")
    plt.show()


def main(args: argparse.Namespace) -> None:
    function = args.function

    if function == "node":
        node(args.args)
        return

    if function == "topic":
        topic(args.args)
        return

    if function == "service":
        service(args.args)
        return

    if function == "graph":
        graph(args.args)
        return

    print(f"Unknown function '{function}'. Use -h for help.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="rixinfo CLI", usage=USAGE)
    parser.add_argument("-v", "--version", action="version", version="rixinfo 1.0")
    parser.add_argument(
        "function", type=str, help="Function to call (show, packages, package, create)"
    )
    parser.add_argument("args", type=str, nargs="*", help="Arguments for the function")
    args = parser.parse_args()
    main(args)
