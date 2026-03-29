#!/usr/bin/env python3.12

import argparse

from node_cmd import node
from topic_cmd import topic
from service_cmd import service
from graph_cmd import graph

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

COMMANDS = {
    "node": node,
    "topic": topic,
    "service": service,
    "graph": graph,
}


def main(args: argparse.Namespace) -> None:
    handler = COMMANDS.get(args.function)
    if handler:
        handler(args.args)
    else:
        print(f"Unknown function '{args.function}'. Use -h for help.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="rixinfo CLI", usage=USAGE)
    parser.add_argument("-v", "--version", action="version", version="rixinfo 1.0")
    parser.add_argument("function", type=str, help="Command to run (node, topic, service, graph)")
    parser.add_argument("args", type=str, nargs="*", help="Arguments for the command")
    args = parser.parse_args()
    main(args)
