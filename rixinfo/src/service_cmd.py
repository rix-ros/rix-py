from common import init_node, fetch_system_info


def service_list(args: list[str]) -> None:
    node = init_node()
    if not node:
        return

    system_info = fetch_system_info(node)
    if not system_info:
        return

    if not system_info.services:
        print("No active RIX services.")
        return

    print("Active RIX services:")
    for srv in system_info.services:
        print(f"  {srv.name}")


SUBCOMMANDS = {
    "list": service_list,
}


def service(args: list[str]) -> None:
    function = args[0] if args else None
    if function not in SUBCOMMANDS:
        print("Error: service function must be: list")
        return
    SUBCOMMANDS[function](args[1:])
