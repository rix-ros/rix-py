from rixcore.node import Node
from rixmsg.standard.Header import Header
from rixmsg.mediator.SystemInfo import SystemInfo


def main():
    node = Node("param_server_test")
    if not node.ok():
        print("Failed to create node.")
        return

    header = Header()
    header.frame_id = "Hello, world!"
    header.seq = 1234

    if not node.set_parameter("test_param", header):
        print("Failed to set parameter.")
        return

    other_header = Header()
    if not node.get_parameter("test_param", other_header):
        print("Failed to get parameter.")
        return

    print("Frame ID: " + other_header.frame_id)
    print("Seq: " + str(other_header.seq))

    system_info = SystemInfo()
    if not node.get_system_info(system_info):
        print("Failed to get system info.")
        return

    print(
        f"Nodes: {len(system_info.nodes)}, Publishers: {len(system_info.publishers)}, Subscribers: {len(system_info.subscribers)}, Services: {len(system_info.services)}, Actions: {len(system_info.actions)}"
    )

    node.shutdown()


if __name__ == "__main__":
    main()
