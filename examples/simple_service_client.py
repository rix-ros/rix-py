from rix.core import Node, TimerCallback
from rix.msg.standard import String, UInt32


def main():
    node = Node("simple_service_client")
    if not node.ok():
        print("Failed to initialize node")
        return

    service_client = node.create_service_client(UInt32, String, "/alphabet")
    if not service_client.ok():
        print("Failed to create service client")
        return

    i: int = 0

    def timer_callback(event: TimerCallback.Event) -> None:
        nonlocal i
        req = UInt32()
        req.data = i
        res = String()
        service_client.call(req, res)
        print(f"Request: {req.data}, Response: {res.data}")
        i += 1

    node.create_timer(1, timer_callback)
    node.spin()


if __name__ == "__main__":
    main()
