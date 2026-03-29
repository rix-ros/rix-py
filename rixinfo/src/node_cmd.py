from rix.core.socket import Socket
from rix.core.common import OPCODE
from rix.sys_msgs import Status, Operation
from rix.std_msgs import Void

from common import init_node, fetch_system_info


def node_list(args: list[str]) -> None:
    node = init_node()
    if not node:
        return

    system_info = fetch_system_info(node)
    if not system_info:
        return

    if not system_info.nodes:
        print("No active RIX nodes.")
        return

    print("Active RIX nodes:")
    for n in system_info.nodes:
        print(f"  {n.name}")


def node_info(args: list[str]) -> None:
    if not args:
        print("Error: 'info' requires a node name as an argument.")
        return

    node_name = args[0]

    node = init_node()
    if not node:
        return

    system_info = fetch_system_info(node)
    if not system_info:
        return

    node_info = next((n for n in system_info.nodes if n.name == node_name), None)
    if not node_info:
        print(f"Error: Node '{node_name}' not found.")
        return

    pub_topics: set[str] = set()
    sub_topics: set[str] = set()
    services: set[str] = set()
    actions: set[str] = set()
    for pub in system_info.publishers:
        if pub.node_id == node_info.id:
            pub_topics.add(pub.topic_info.name)
    for sub in system_info.subscribers:
        if sub.node_id == node_info.id:
            sub_topics.add(sub.topic_info.name)
    for srv in system_info.services:
        if srv.node_id == node_info.id:
            services.add(srv.name)
    for act in system_info.actions:
        if act.node_id == node_info.id:
            actions.add(act.name)

    print(f"Node: {node_info.name}")
    if pub_topics:
        print("  Published Topics:")
        for t in sorted(pub_topics):
            print(f"    {t}")
    if sub_topics:
        print("  Subscribed Topics:")
        for t in sorted(sub_topics):
            print(f"    {t}")
    if services:
        print("  Services:")
        for s in sorted(services):
            print(f"    {s}")
    if actions:
        print("  Actions:")
        for a in sorted(actions):
            print(f"    {a}")


def node_ping(args: list[str]) -> None:
    if not args:
        print("Error: 'ping' requires a node name as an argument.")
        return

    node_name = args[0]

    node = init_node()
    if not node:
        return

    system_info = fetch_system_info(node)
    if not system_info:
        return

    node_info = next((n for n in system_info.nodes if n.name == node_name), None)
    if not node_info:
        print(f"Error: Node '{node_name}' not found.")
        return

    endpoint = (node_info.endpoint.address, node_info.endpoint.port)

    client = Socket()
    if not client.connect(endpoint):
        print(f"Error: Failed to connect to node '{node_name}' at {endpoint}.")
        return

    msg = Void()
    if not client.send_message(OPCODE.PING, msg):
        print(f"Error: Failed to send ping to node '{node_name}'.")
        return

    status = Status()
    op = Operation()
    if not client.recv_message_with_opcode(op, status):
        print(f"Error: Failed to receive ping response from node '{node_name}'.")
        return

    if op.opcode != OPCODE.STATUS_RESPONSE:
        print(f"Error: Unexpected response opcode {op.opcode} from node '{node_name}'.")
        return

    print(f"Node '{node_name}' is alive. Status: {status.error}")


SUBCOMMANDS = {
    "list": node_list,
    "info": node_info,
    "ping": node_ping,
}


def node(args: list[str]) -> None:
    function = args[0] if args else None
    if function not in SUBCOMMANDS:
        print("Error: node function must be one of: list, info, ping")
        return
    SUBCOMMANDS[function](args[1:])
