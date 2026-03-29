import time

from common import init_node, fetch_system_info, load_topic_index, hash_to_str, resolve_message_class, message_to_yaml


def topic_list(args: list[str]) -> None:
    node = init_node()
    if not node:
        return

    system_info = fetch_system_info(node)
    if not system_info:
        return

    topics_by_hash = load_topic_index()

    if not system_info.topics:
        print("No active RIX topics.")
        return

    print("Active RIX topics:")
    for t in system_info.topics:
        topic_hash = hash_to_str(t.message_hash)
        message_name = topics_by_hash.get(topic_hash, "Unknown")
        print(f"  {t.name} [{message_name}]")


def _resolve_topic(system_info, topic_name: str, topics_by_hash: dict):
    """Find a topic in system_info and resolve its message class. Returns (topic_info, message_class) or (None, None)."""
    topic_info = next((t for t in system_info.topics if t.name == topic_name), None)
    if not topic_info:
        print(f"Error: Topic '{topic_name}' not found.")
        return None, None

    topic_hash = hash_to_str(topic_info.message_hash)
    message_name = topics_by_hash.get(topic_hash)
    if not message_name:
        print(f"Error: Message type for topic '{topic_name}' not found in index.")
        return None, None

    message_class = resolve_message_class(message_name)
    if not message_class:
        return None, None

    return topic_info, message_class


def topic_echo(args: list[str]) -> None:
    if not args:
        print("Error: 'echo' requires a topic name as an argument.")
        return

    topic_name = args[0]

    node = init_node()
    if not node:
        return

    system_info = fetch_system_info(node)
    if not system_info:
        return

    topics_by_hash = load_topic_index()
    _, message_class = _resolve_topic(system_info, topic_name, topics_by_hash)
    if not message_class:
        return

    def callback(msg) -> None:
        print(message_to_yaml(msg))
        print()

    sub = node.create_subscriber(message_class, topic_name, callback)
    if not sub.ok():
        print("Error: Failed to create subscriber.")
        return

    node.spin()


def topic_hz(args: list[str]) -> None:
    if not args:
        print("Error: 'hz' requires a topic name as an argument.")
        return

    topic_name = args[0]

    node = init_node()
    if not node:
        return

    system_info = fetch_system_info(node)
    if not system_info:
        return

    topics_by_hash = load_topic_index()
    _, message_class = _resolve_topic(system_info, topic_name, topics_by_hash)
    if not message_class:
        return

    count = 0
    start_time = 0

    def callback(msg) -> None:
        nonlocal count, start_time
        if start_time == 0:
            start_time = time.time()
            return
        count += 1
        elapsed = time.time() - start_time
        if elapsed > 0:
            print(f"\rRate: {count / elapsed:.3f} Hz", end="", flush=True)

    sub = node.create_subscriber(message_class, topic_name, callback)
    if not sub.ok():
        print("Error: Failed to create subscriber.")
        return

    print(f"Measuring rate on '{topic_name}'. Press Ctrl+C to stop.")
    node.spin()


def topic_bw(args: list[str]) -> None:
    if not args:
        print("Error: 'bw' requires a topic name as an argument.")
        return

    topic_name = args[0]

    node = init_node()
    if not node:
        return

    system_info = fetch_system_info(node)
    if not system_info:
        return

    topics_by_hash = load_topic_index()
    _, message_class = _resolve_topic(system_info, topic_name, topics_by_hash)
    if not message_class:
        return

    total_bytes = 0
    start_time = 0

    def callback(msg) -> None:
        nonlocal total_bytes, start_time
        if start_time == 0:
            start_time = time.time()
            return
        total_bytes += msg.size()
        elapsed = time.time() - start_time
        if elapsed > 0:
            bps = total_bytes / elapsed
            if bps >= 1_000_000:
                print(f"\rBandwidth: {bps / 1_000_000:.3f} MB/s", end="", flush=True)
            elif bps >= 1_000:
                print(f"\rBandwidth: {bps / 1_000:.3f} KB/s", end="", flush=True)
            else:
                print(f"\rBandwidth: {bps:.3f} B/s", end="", flush=True)

    sub = node.create_subscriber(message_class, topic_name, callback)
    if not sub.ok():
        print("Error: Failed to create subscriber.")
        return

    print(f"Measuring bandwidth on '{topic_name}'. Press Ctrl+C to stop.")
    node.spin()


SUBCOMMANDS = {
    "list": topic_list,
    "echo": topic_echo,
    "hz": topic_hz,
    "bw": topic_bw,
}


def topic(args: list[str]) -> None:
    function = args[0] if args else None
    if function not in SUBCOMMANDS:
        print("Error: topic function must be one of: list, echo, hz, bw")
        return
    SUBCOMMANDS[function](args[1:])
