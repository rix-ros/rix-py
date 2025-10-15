# `rixinfo`: RIX System Introspection CLI

`rixinfo` is a command-line utility for inspecting and interacting with a running RIX-PY system. It replaces the previous `rixtopic` tool and provides introspection for nodes, topics, and services.

## Features

- **Node Introspection:**
  - List all active RIX nodes
  - Show detailed info for a specific node (published/subscribed topics, services)
- **Topic Introspection:**
  - List all active RIX topics and their message types
  - Echo messages published on a topic in real time
  - Display the message rate (Hz) of a topic
  - Show the bandwidth (bytes/sec) used by a topic
- **Service Introspection:**
  - List all active RIX services

## Usage

```sh
rixinfo [-h] function [arg]
```

### Functions

- `node`
  - `list` — List all active RIX nodes
  - `info <node>` — Show info for a specific node
- `topic`
  - `list` — List all active RIX topics
  - `echo <topic>` — Print messages published on `<topic>`
  - `hz <topic>` — Print the message rate (Hz) of `<topic>`
  - `bw <topic>` — Print the bandwidth (bytes/sec) of `<topic>`
- `service`
  - `list` — List all active RIX services

## Requirements

- `rix-py` and its dependencies must be installed
- `rixhub` must be running
- The message type index file (`~/.rix/rixmsg/index.txt`) should exist and be up-to-date

## Troubleshooting

- If you see "Message type for topic ... not found in index", update your message index
- If you see "Could not import ...", ensure your message packages are installed and available in `~/.rix/python/rix`

## License

See [LICENSE.md](../LICENSE.md) for details.