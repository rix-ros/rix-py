# rixtopic

`rixtopic` is a command-line utility for interacting with RIX-PY topics in a running RIX system. It allows you to list active topics, echo messages, measure message rates, and monitor bandwidth for any topic.

## Features

- **List Topics:** See all active RIX topics and their message types.
- **Echo Messages:** Print messages published on a topic in real time.
- **Measure Rate:** Display the frequency (Hz) of messages on a topic.
- **Monitor Bandwidth:** Show the bandwidth (bytes/sec) used by a topic.

## Usage

```sh
rixtopic [-h] function [arg]
```

### Functions

- `list`  
  List all active RIX topics.

- `echo <topic>`  
  Print messages published on `<topic>`.

- `hz <topic>`  
  Print the message rate (Hz) of `<topic>`.

- `bw <topic>`  
  Print the bandwidth (bytes/sec) of `<topic>`.

## Requirements

- `rix-py` and its dependencies must be installed.
- `rixhub` must be running.
- The message type index file (`~/.rix/rixmsg/index.txt`) should exist and be up-to-date.

## Troubleshooting

- If you see "Message type for topic ... not found in index", update your message index.
- If you see "Could not import ...", ensure your message packages are installed and available in `~/.rix/python/rix`.

## License

See [LICENSE.md](LICENSE.md) for details.